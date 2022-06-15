from datetime import datetime
import os
import sys
import socket
import requests
import atexit
import sys
import random

from flask import Flask, request, Response, jsonify
from bson import ObjectId
from bson.json_util import dumps
from pymongo import MongoClient, ReturnDocument
from stock import Stock
from stock_update import StockUpdate
import kubernetes as k8s

app = Flask("stock-service")


client = MongoClient(os.environ['GATEWAY_URL'], int(os.environ['PORT']))
db = client['local']


# get replica pods using kubernets api
k8s.config.load_incluster_config()
v1 = k8s.client.CoreV1Api()
hostname=socket.gethostname()
IPAddr=socket.gethostbyname(hostname)
print(hostname, file=sys.stderr)
print("running on: " + IPAddr, file=sys.stderr)

replicas = []
def get_pods():
    global replicas
    replicas = []
    pod_list = v1.list_pod_for_all_namespaces(watch=False)
    for pod in pod_list.items:
        if("stock-deployment" in pod.metadata.name and pod.status.phase == 'Running'):
            replicas.append({
                'name': pod.metadata.name,
                'ip': pod.status.pod_ip,
                'address': f'http://{pod.status.pod_ip}:5000'
            })
    print(replicas, file=sys.stderr)

# read quorum write quorum config
# TODO consider different write_quorum for add stock and subtract stock
read_quorum = 2 
write_quorum = 2


def close_db_connection():
    db.close()


atexit.register(close_db_connection)


def get_stock_by_id(item_id: str):
    stock = db.stock.find_one({"_id": ObjectId(str(item_id))})
    return Stock.loads(stock)


def get_quorum_samples(quorum: int):
    return random.sample(range(len(replicas)), min(len(replicas), quorum))


def get_replica_address(index: int):
       return replicas[index]['address']

def add_stock_to_db(item_id: str, amount: int, stock_update: StockUpdate) -> Stock:
    stock = db.stock.find_one_and_update(
        {'_id': ObjectId(str(item_id))},
        {'$inc': {'stock': amount}},
        return_document=ReturnDocument.AFTER
    )
    db.stock_updates.insert_one(stock_update.__dict__)
    stock_update.load_id()
    return Stock.loads(stock)

@app.post('/item/create/<price>')
def create_item(price: int):
    """
    Create stock item with given price
    :param price:
    :return: Stock
    """
    # create and save the new stock item
    stock = Stock(price=int(price))
    db.stock.insert_one(stock.__dict__)
    stock.item_id = str(stock.__dict__.pop('_id'))

    # Send stock item to write_quorum
    candidates = get_quorum_samples(write_quorum)
    for i in candidates:
        candidate = replicas[i]
        replica_address = candidate['address'] 
        requests.put(replica_address + '/item/create', json=stock.__dict__)
        # TODO check if the requests are ok and handle accordingly if they fail

    return stock.dumps()

@app.put('/item/create')
def insert_item():
    item = Stock.loads(request.json)
    db.stock.insert_one({'_id': ObjectId(item), **item.__dict__})
    return 'ok', 200


@app.get('/find_one/<item_id>')
def find_one_item(item_id: str):
    stock = get_stock_by_id(item_id)
    return stock.dumps()


@app.get('/find/<item_id>')
def find_item(item_id: str):
    """
    Get item if it exists.
    Users read quorum, takes minimum stock from all written quorums, since this prevents stock
    from being sold if it is not there.
    :param item_id:
    :return: Stock
    """
    # get stock on this instance
    stock = get_stock_by_id(item_id)

    # get stock on read_quorum -1 instance 
    candidates = get_quorum_samples(read_quorum)
    stock_replicas = []
    stock_replicas.append(stock)
    for i in candidates:
        replica_address = get_replica_address(i)
        response = requests.get(f'{replica_address}/find_one/{item_id}')
        if response.status_code == 200:
            stock = stock.loads(response.json())
            stock_replicas.append(stock)
    
    for replica in stock_replicas:
        if replica.stock < stock.stock:
            stock.stock = replica.stock
    
    return stock.dumps(), 200


@app.post('/add_one/<item_id>/<amount>')
def add_amount_to_one(item_id: str, amount: int):
    """
    Add amount to only one node
    """
    amount = int(amount)
    stock_update = StockUpdate.loads(request.json)
    stock = add_stock_to_db(item_id, amount, stock_update)
    return stock.dumps(), 200


@app.post('/add/<item_id>/<amount>')
def add_stock(item_id: str, amount: int):
    """
    Add amount to stock
    :param item_id:
    :param amount:
    :return: Stock
    """
    # write stock update to db
    amount = int(amount)
    stock_update = StockUpdate(item_id = item_id, amount=amount, local_time_stamp=datetime.now(), 
        node=hostname)
    stock = add_stock_to_db(item_id, amount, stock_update)

    # write stock to quorum
    candidates = get_quorum_samples(read_quorum)
    for i in candidates:
        replica_address = get_replica_address(i)
        response = request.post(f'{replica_address}/add_one/{item_id}/{amount}', json=stock_update.__dict__)
    return stock.dumps(), 200


def remove_stock(item_id: str, amount: int):
    """
    Remove stock from item with given id.
        - Try to remove from write quorum.
        - If one fails, rollback and add amount back to nodes that did succeed.
        - Write stock_update to log only after success, to own node. also keep track of failed 
            stock_update to be able to remove them at other nodes.
    :param item_id: The item to subtract amount from.
    :param amount: The amount to remove from the stock.
    :return: Stock item.
    """
    amount = int(amount)
    stock = get_stock_by_id(item_id)
    if stock.stock < amount:
        return "Not enough stock", 400
    stock = db.stock.find_one_and_update(
        {'_id': ObjectId(str(item_id))},
        {'$inc': {'stock': -amount}},
        return_document=ReturnDocument.AFTER
    )
    stock = Stock.loads(stock)
    return stock.dumps(), 200 


@app.get('/log')
def get_stock_update_log():
    all_stock_updates = db.stock_updates.find()
    return dumps(all_stock_updates), 200
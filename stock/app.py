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
from threading import Thread


#flask app
app = Flask("stock-service")


#mongodb client
client = MongoClient(os.environ['GATEWAY_URL'], int(os.environ['PORT']))
db = client['local']


# pod events:
DELETED = "DELETED"
ADDED = 'ADDED'
MODIFIED = 'MODIFIED' 


# get replica pods using kubernets api
k8s.config.load_incluster_config()
v1 = k8s.client.CoreV1Api()
hostname=socket.gethostname()
IPAddr=socket.gethostbyname(hostname)
print(hostname, file=sys.stderr)
print("running on: " + IPAddr, file=sys.stderr)


def threaded_task():
    """
    Threaded task listens to k8s api event and loads all replicas
    """
    print('Setting up k8s api event listener', file=sys.stderr)
    w = k8s.watch.Watch()
    for event in w.stream(v1.list_pod_for_all_namespaces, timeout_seconds=10):
        pod = event['object']
        print("Event: %s %s %s" % (
            event['type'],
            event['object'].kind,
            event['object'].metadata.name)
        ,file=sys.stderr)
        if 'stock-deployment' in pod.metadata.name:
            # if there is a new stock-deployment event, refetch al active stock ip
            get_pods()
            if event['type'] == DELETED:
                if pod.metadata.name in replicas:
                    replicas.pop(pod.metadata.name)


# tread to listen to k8s api
thread = Thread(target=threaded_task)
thread.daemon = True
thread.start()


replicas = {}
def get_pods():
    """
    Gets replica ip addresses and stores them im replicas set
    TODO add extra check after timeout to check if its still alive since shuting down can take some time. (try something like javascript timeout)
    """
    global replicas
    replicas = {}
    pod_list = v1.list_pod_for_all_namespaces(watch=False)
    for pod in pod_list.items:
        if(pod.metadata.name != hostname and "stock-deployment" in pod.metadata.name and pod.status.phase == 'Running'):
            url = f'http://{pod.status.pod_ip}:5000'
            try:
                response = requests.get(f'{url}/alive/{hostname}/{IPAddr}')
                if response.status_code == 200:
                    replicas[pod.metadata.name] = url 
            except requests.exceptions.ConnectionError as e:
                if pod.metadata.name in replicas:
                    replicas.pop(pod.metadata.name)
                print(e, file=sys.stderr)
 

# read quorum write quorum config
# TODO consider different write_quorum for add stock and subtract stock
read_quorum = 2 
write_quorum = 2


def close_db_connection():
    db.close()


atexit.register(close_db_connection)


class StockNotFoundException(Exception):
    """stock not found"""
    pass

def get_stock_by_id(item_id: str):
    stock = db.stock.find_one({"_id": ObjectId(str(item_id))})
    if stock is None:
        raise StockNotFoundException()
    return Stock.loads(stock)


def get_quorum_samples(quorum: int):
    return random.sample(list(replicas.keys()), min(len(replicas), quorum))



def add_stock_to_db(item_id: str, amount: int, stock_update: StockUpdate) -> Stock:
    stock = db.stock.find_one_and_update(
        {'_id': ObjectId(str(item_id))},
        {'$inc': {'stock': amount}},
        return_document=ReturnDocument.AFTER
    )
    db.stock_updates.insert_one(stock_update.__dict__)
    stock_update.load_id()
    return Stock.loads(stock)


@app.get('/alive/<hostname>/<ip_address>')
def im_alive(hostname: str, ip_address: str):
    replicas[hostname] = f'http://{ip_address}:5000'
    return 'ok', 200

@app.get('/pods')
def config_pods():
    return dumps(replicas)


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
        replica_address = replicas[i]
        response = requests.put(replica_address + '/item/create', json=stock.__dict__)
        # TODO check if the requests are ok and handle accordingly if they fail
        if response.status_code != 200:
            print(response, file=sys.stderr)

    return stock.dumps()

@app.put('/item/create')
def insert_item():
    item = Stock.loads(request.json)
    db.stock.insert_one({'_id': ObjectId(item.item_id), **item.__dict__})
    print(f'CREATED item with item id {item.item_id}', file=sys.stderr)
    return 'ok', 200


@app.get('/find_one/<item_id>')
def find_one_item(item_id: str):
    try:
        stock = get_stock_by_id(item_id)
    except StockNotFoundException as e:
        return 'stock not found', 400
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
    try:
        stock = get_stock_by_id(item_id)
    except StockNotFoundException as e:
        return 'stock not found', 400

    # get stock on read_quorum -1 instance 
    candidates = get_quorum_samples(read_quorum)
    stock_replicas = []
    stock_replicas.append(stock)
    for i in candidates:
        replica_address = replicas[i]
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
    stock_update = StockUpdate(item_id = item_id, amount=amount, 
        node=hostname)
    stock = add_stock_to_db(item_id, amount, stock_update)
    print('stock_update id '+ str(stock_update.update_id), file=sys.stderr)
    # write stock to quorum
    candidates = get_quorum_samples(read_quorum)
    for i in candidates:
        replica_address = replicas[i]
        response = requests.post(f'{replica_address}/add_one/{item_id}/{amount}', json=stock_update.__dict__)
    return stock.dumps(), 200


@app.post('/subtract_one/<item_id>/<amount>')
def remove_stock_one(item_id: str, amount: int):
    amount = int(amount)
    try:
        stock = get_stock_by_id(item_id)
    except StockNotFoundException as e:
        return 'stock not found', 400
    if stock.stock < amount:
        return "Not enough stock", 400
    stock = db.stock.find_one_and_update(
        {'_id': ObjectId(str(item_id))},
        {'$inc': {'stock': -amount}},
        return_document=ReturnDocument.AFTER
    )
    stock = Stock.loads(stock)
    return stock.dumps(), 200 

@app.post('/subtract/<item_id>/<amount>')
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

    try:
        stock = get_stock_by_id(item_id)
    except StockNotFoundException as e:
        return 'stock not found', 400
    if stock.stock < amount:
        return "Not enough stock", 400
    
    candidates = get_quorum_samples(read_quorum)
    succeeded_candidate_urls = []
    failed = False
    for c in candidates:
        replication_address = replicas[c]
        response = requests.post(f'{replication_address}/{item_id}/{amount}')
        if response.status_code == 200:
            succeeded_candidate_urls.append(replication_address)
        elif response.status_code == 400:
            failed = True
            break
        succeeded_candidate_urls.append(replication_address)
    
    if failed:
        for replication_address in succeeded_candidate_urls:
            request.post(f'{replication_address}/add_one/{item_id}/{amount}')

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
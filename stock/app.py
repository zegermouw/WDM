import os
import sys
import socket
import threading
import requests
import atexit
from bson import ObjectId
from flask import Flask, request 
from pymongo import MongoClient, ReturnDocument
import sys

from flask import Flask, request, Response, jsonify
import redis
from stock import Stock
import random
from stock_update import StockUpdate
from bson.json_util import dumps
import kubernetes as k8s
import threading
Thread = threading.Thread
import time

app = Flask("stock-service")


#mongodb client
client = MongoClient(os.environ['GATEWAY_URL'], int(os.environ['PORT']))
db = client['local']

# read quorum write quorum config
# TODO consider different write_quorum for add stock and subtract stock
read_quorum = int(os.environ['READ_QUORUM'])
write_quorum = int(os.environ['WRITE_QUORUM'])

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


replicas = {}
def get_pods():
    """
    Gets replica ip addresses and stores them im replicas set
    TODO add extra check after timeout to check if its still alive since shuting down can take some time. (try something like javascript timeout)
    """
    global replicas
    new_replicas = {}
    pod_list = v1.list_pod_for_all_namespaces(watch=False)
    for pod in pod_list.items:
        if(pod.metadata.name != hostname and "stock-deployment" in pod.metadata.name and pod.status.phase == 'Running'):
            url = f'http://{pod.status.pod_ip}:5000'
            new_replicas[pod.metadata.name] = url 
    if sorted(list(replicas.values())) != sorted(list(new_replicas.values())):
        replicas = new_replicas


class MyThread(Thread):
    def __init__(self):
        Thread.__init__(self)
        self.daemon = True
        self.start()
    
    def run(self):
        while True:
            get_pods()
            time.sleep(1)


MyThread()

# update service with other logs

def get_stock_update_log():
    all_stock_updates = db.stock_updates.find()
    res = {}
    for stock_update in all_stock_updates:
        su = StockUpdate.loads(stock_update)
        res[su.update_id] = su.__dict__
    return res


def compare_logs(own_log, other_log):
    """
        compares own_log with other_log and returns the transactions that did
        not take place at own node
    """
    own_log_key_set = set(own_log.keys())
    other_log_key_set = set(other_log.keys())
    not_in_own_key_set = other_log_key_set - own_log_key_set
    return {k:other_log[k] for k in not_in_own_key_set}


def update_log(central_log):
        own_log = get_stock_update_log()
        not_in_own_log = compare_logs(own_log, central_log)
        update_stock_from_log(not_in_own_log)


def update_stock_from_log(to_be_updated):
    for update_item in to_be_updated.values():
        su = StockUpdate.loads(update_item)
        print('updating stock:' + str(update_item), file=sys.stderr)
        add_stock_to_db(su)


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

def get_quorum_samples_addresses(quorum: int):
    return random.sample(list(replicas.values()), min(len(replicas), quorum))

def add_stock_to_db(stock_update: StockUpdate) -> Stock:
    stock = db.stock.find_one_and_update(
        {'_id': ObjectId(str(stock_update.item_id))},
        {'$inc': {'stock': stock_update.amount}},
        return_document=ReturnDocument.AFTER
    )
    if stock == None:
        # stock did not exist: insert stock
        stock = Stock(item_id=stock_update.item_id, stock=stock_update.amount, price=stock_update.price)
        db.stock.insert_one({'_id': ObjectId(stock.item_id), **stock.__dict__})
    else:
        stock = Stock.loads(stock)
    stock.load_id()
    stock_update.price = stock.price
    if stock_update.update_id is None:
        db.stock_updates.insert_one(stock_update.__dict__)
        #stock_update.load_id()
    else:
        db.stock_updates.insert_one({
            '_id': ObjectId(stock_update.update_id), 
            **stock_update.__dict__
        })
    print('created stock_update with id:' + str(stock_update))
    stock_update.load_id()
    return stock, stock_update


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
    price = int(price)
    stock = Stock(price=price)
    db.stock.insert_one(stock.__dict__)
    stock.item_id = str(stock.__dict__.pop('_id'))
    stock_update = StockUpdate(item_id=stock.item_id, amount=0, node=hostname, price=price )
    db.stock_updates.insert_one(stock_update.__dict__)
    stock_update.load_id()

    # Send stock item to write_quorum
    candidates = get_quorum_samples_addresses(write_quorum)
    for replica_address in candidates:
        response = requests.put(replica_address + '/item/create', json={
            'item': stock.__dict__,
            'stock_update': stock_update.__dict__
            })
        # TODO check if the requests are ok and handle accordingly if they fail
        if response.status_code != 200:
            print(response, file=sys.stderr)

    return stock.dumps()

@app.put('/item/create')
def insert_item():
    json = request.json
    item_json = json['item']
    stock_update_json = json['stock_update']
    item = Stock.loads(item_json)
    stock_update = StockUpdate.loads(stock_update_json)
    db.stock.insert_one({'_id': ObjectId(item.item_id), **item.__dict__})
    db.stock_updates.insert_one({
        '_id': ObjectId(stock_update.update_id), 
        **stock_update.__dict__
        })
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
    candidates = get_quorum_samples_addresses(read_quorum)
    stock_replicas = []
    stock_replicas.append(stock)
    for replica_address in candidates:
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
    stock_update = StockUpdate.loads(request.json)
    stock, _ = add_stock_to_db(stock_update)
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
    stock, stock_update = add_stock_to_db(stock_update)
    print('stock_update id '+ str(stock_update.update_id), file=sys.stderr)
    # write stock to quorum
    candidates = get_quorum_samples_addresses(read_quorum)
    for replica_address in candidates:
        response = requests.post(f'{replica_address}/add_one/{item_id}/{amount}', json=stock_update.__dict__)
    return stock.dumps(), 200


@app.post('/subtract_one/<item_id>/<amount>')
def remove_stock_one(item_id: str, amount: int):
    amount = int(amount)
    stock_update = StockUpdate.loads(request.json)
    stock, stock_update = add_stock_to_db(stock_update)
    if stock.stock < 0:
        return 'not enough stock', 400
    
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
    
    stock_update = StockUpdate(item_id=item_id, amount=-amount, node=hostname, price=-amount)
    item, stock_update = add_stock_to_db(stock_update)

    if item.stock < 0:
        # revert update
        stock_update = StockUpdate(item_id=item_id, amount=amount, node=hostname)
        item, stock_update = add_stock_to_db(stock_update)
        return "not enough stock", 400

    
    candidates = get_quorum_samples_addresses(read_quorum)
    succeeded_candidate_urls = []
    failed = False
    for replication_address in candidates:
        response = requests.post(f'{replication_address}/subtract_one/{item_id}/{amount}', json=stock_update.__dict__)
        if response.status_code == 200:
            succeeded_candidate_urls.append(replication_address)
        elif response.status_code == 400:
            failed = True
            break
        succeeded_candidate_urls.append(replication_address)

    if failed:
        # if one failed write back the stock.
        stock_update = StockUpdate(item_id=item_id, amount=amount, node=hostname)
        item, stock_update = add_stock_to_db(stock_update)
        for replication_address in succeeded_candidate_urls:
            requests.post(f'{replication_address}/add_one/{item_id}/{amount}', json=stock_update)
        return "not enough stock", 400

    return item.dumps(), 200 


@app.post('/log')
def get_stock_update_log_response():
    stock_update_log = get_stock_update_log()
    # todo make this async such that call return without updating own log first might be faster
    logs =  request.json
    if logs != None and len(logs)>0:
        update_log(logs)    
    return dumps(stock_update_log), 200

import atexit
import os
from enum import Enum
import time
from flask import Flask, jsonify, request, logging

import sys
import requests
import pymongo
import datetime
from pymongo import ReturnDocument
from bson.objectid import ObjectId
from bson.json_util import dumps
import uuid

from models import User
from paxos import Paxos
import kubernetes as k8s
import threading
import random
Thread = threading.Thread
import socket



app = Flask("payment-service")



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



myclient = pymongo.MongoClient(os.environ['GATEWAY_URL'], int(os.environ['PORT']))
db = myclient["local"]
replicas = {}
payment_replicas: list[str] = []
replication_number = random.randint(0,100) #use random integer as unique replication id number 
paxos = Paxos(payment_replicas, db, replication_number, logger=app.logger)

def get_pods():
    """
    Gets replica ip addresses and stores them im replicas set
    TODO add extra check after timeout to check if its still alive since shuting down can take some time. (try something like javascript timeout)
    """
    global replicas
    global payment_replicas
    global paxos
    new_replicas = {}
    pod_list = v1.list_pod_for_all_namespaces(watch=False)
    for pod in pod_list.items:
        if(pod.metadata.name != hostname and "payment-deployment" in pod.metadata.name and pod.status.phase == 'Running'):
            url = f'http://{pod.status.pod_ip}:5000'
            new_replicas[pod.metadata.name] = url 
    replicas = new_replicas
    payment_replicas = list(replicas.values())
    if sorted(paxos.replicas) != sorted(payment_replicas):
        paxos.replicas = payment_replicas
    
    ### PRINT THE COUNT AND IPs OF PODS
    # print(f'pods found count: {len(paxos.replicas)}', file=sys.stderr)
    # for i,r in enumerate(paxos.replicas):
    #     print(i,r, file=sys.stderr)

class MyThread(Thread):
    def __init__(self):
        Thread.__init__(self)
        self.daemon = True
        self.start()
    
    def run(self):
        print('start listening to k8s api to list replicas', file=sys.stderr)
        while True:
            get_pods()
            time.sleep(1)


MyThread()


# for testing purposes
@app.get('/pods')
def config_pods():
    return dumps(replicas)


@app.get('/alive/<hostname>/<ip_address>')
def im_alive(hostname: str, ip_address: str):
    replicas[hostname] = f'http://{ip_address}:5000'
    return 'ok', 200




def close_db_connection():
    myclient.close()


atexit.register(close_db_connection)


# region MODEL


class OrderStatus(str, Enum):
    IN_TRANSACTION = 'IN_TRANSACTION'
    PROCESSED = 'PROCESSED'
    CANCELLED = 'CANCELLED'
    PAID = 'PAID'


# endregion

# region SERVICES


def find_user_by_id(user_id):
    user = db.users.find_one({'_id': ObjectId(user_id)})
    user['user_id'] = str(user.pop('_id'))
    return user


# endregion

# region ENDPOINTS

@app.post('/create_user')
def create_user():
    log('POST', '/create_user')
    # TODO create users in replication nodes, can be done asynchronous
    """
    Create User and distribute to replicas
    :return: User object and status 200 if everything ok.
    """
    user = User()
    user_id = db.users.insert_one(user.__dict__).inserted_id
    user.set_id()
    global payment_replicas
    log('replicas:', *payment_replicas)
    for replica in payment_replicas:
        try:
            log(f'putting new user on replica {replica}')
            requests.put(f'{replica}/create_user', json=user.__dict__)
        except requests.exceptions.ConnectionError as e:
            print(e, file=sys.stderr)
    log(f'User created with id {user_id=}')
    return jsonify({'user_id': str(user_id)}), 200


@app.put('/create_user')
def insert_user():
    user = User.loads(request.json)
    log('PUT', '/create_user', user)
    db.users.insert_one({'_id': ObjectId(user.user_id), **user.__dict__})
    return 'ok', 200


@app.get('/find_user/<user_id>')
def find_user(user_id: str):
    log('GET', f'/find_user/{user_id=}')
    user = find_user_by_id(user_id)
    return jsonify(user), 201


@app.post('/add_funds/<user_id>/<amount>')
def add_credit(user_id: str, amount: float):
    log('POST', f'/add_funds/{user_id=}/{amount=}')
    # TODO restrict number of retries for Paxos.NOT_ACCEPTED
    app.logger.info(" requesting add funds with amount %s, and user_id %s", amount, user_id)
    amount = float(amount)
    user = find_user_by_id(user_id)
    user['credit'] += amount
    transaction_id = str(uuid.uuid4())
    user['transaction_id'] = transaction_id
    response, accepted_user = paxos.proposer_prepare(user)
    # go trough another round of paxos when not accepted, retry... once
    if response == Paxos.NOT_ACCEPTED:
        return add_credit(user_id, amount)
    if accepted_user['transaction_id'] != user['transaction_id']:
        return add_credit(user_id, amount)
    return 'ACCEPTED', 200


@app.post('/pay/<user_id>/<order_id>/<amount>')
def remove_credit(user_id: str, order_id: str, amount: float):
    log('POST', f'/pay/{user_id=}/{order_id=}/{amount=}')
    amount = float(amount)
    user = find_user_by_id(user_id)
    log('user found', user)
    if user['credit'] < amount:
        return 'INSUFFICIENT FUNDS', 200

    user['credit'] -= amount
    user['transaction_id'] = str(uuid.uuid4())
    response, accepted_user = paxos.proposer_prepare(user)

    # go trough another round of paxos when not accepted, retry... once
    if response == Paxos.NOT_ACCEPTED:
        return remove_credit(user_id, order_id, amount)
    if accepted_user['transaction_id'] != user['transaction_id']:
        return remove_credit(user_id, order_id, amount)
    payment = {'user_id': user_id, 'order_id': order_id, 'status': OrderStatus.PAID}
    db.payments.insert_one(payment)
    payment['payment_id'] = str(payment.pop('_id'))
    return 'PAID', 200


@app.post('/cancel/<user_id>/<order_id>')
def cancel_payment(user_id: str, order_id: str):
    log('POST', f'/cancel/{user_id=}/{order_id=}')
    """
    Cancels the payment (should this method also add the amount of the order
    back to the users account?)
    :param user_id:
    :param order_id:
    :return: payment
    """
    payment = db.payments.find_one_and_update(
        {'_id': ObjectId(user_id), 'payments.order_id': order_id},
        {'$set': {'payments.$.status': f'{OrderStatus.CANCELLED}'}},
        return_document=ReturnDocument.AFTER
    )
    payment['payment_id'] = str(payment.pop('_id'))
    return jsonify(payment), 200


@app.post('/status/<user_id>/<order_id>')
def payment_status(user_id: str, order_id: str):
    log('POST', f'/status/{user_id=}/{order_id=}')
    payment = db.payments.find_one(
        {'_id': ObjectId(user_id), 'payments.order_id': order_id}
    )
    return payment['status'], 200


@app.post('/prepare')
def paxos_acceptor_prepare():
    log('POST', '/prepare')
    content = request.json
    app.logger.info('prepare content %s', str(content))
    return paxos.acceptor_prepare(content['proposal_id'], content['proposal_value'])


@app.post('/accept')
def acceptor_accept():
    log('POST','/accept')
    content = request.json
    app.logger.info('content log %s', str(content))
    return paxos.acceptor_accept(content['accepted_id'], content['accepted_value'])


@app.post('/prepare_pay/<user_id>/<amount>')
def prepare_pay(user_id: str, amount: float):
    log('POST', f'/prepare_pay/{user_id=}/{amount=}')
    amount = float(amount)
    user = find_user_by_id(user_id)

    if user['credit'] < amount:
        return 'Insufficient credit', 400
    else:
        return 'Prepare of payment successful', 200


@app.post('/rollback_pay/<user_id>/<amount>')
def rollback_pay(user_id: str, amount: float):
    log('POST', f'/rollback_pay/{user_id=}/{amount=}')
    return add_credit(user_id, amount)


@app.post('/commit_pay/<user_id>/<order_id>/<amount>')
def commit_pay(user_id: str, order_id: str, amount: float):
    log('POST', f'/commit_pay/{user_id=}/{order_id=}/{amount=}')
    return remove_credit(user_id, order_id, amount)

def log(*args):
    print(f'[{datetime.datetime.now()}]', *args, file=sys.stderr)
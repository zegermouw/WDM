import atexit
import os
from enum import Enum
from flask import Flask, request, logging
import json
import requests
from bson import json_util
import pymongo
from pymongo import ReturnDocument
from bson.objectid import ObjectId
import uuid


from models import User
from paxos import Paxos

app = Flask("payment-service")

myclient = pymongo.MongoClient(os.environ['GATEWAY_URL'], int(os.environ['PORT']))
db = myclient["local"]
payment_replicas: list[str] = [os.environ['OTHER_NODE']]
port = '5000'
for i in range(len(payment_replicas)):
    s = payment_replicas[i]
    payment_replicas[i] = s + ':' + port

replication_number = int(os.environ['REPLICATION_NUMBER'])

def close_db_connection():
    myclient.close()


atexit.register(close_db_connection)
base_url = "http://host.docker.internal"
paxos = Paxos(payment_replicas, db, replication_number, logger=app.logger)

# region MODEL


class OrderStatus(str, Enum):
    IN_TRANSACTION = 'IN_TRANSACTION'
    PROCESSED = 'PROCESSED'
    CANCELLED = 'CANCELLED'
    PAYED = 'PAYED'


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
    # TODO create users in replication nodes, can be done asynchronous
    """
    Create User and distribute to replicas
    :return: User object and status 200 if everything ok.
    """
    user = User()
    db.users.insert_one(user.__dict__)
    user.set_id()
    for replica in payment_replicas:
        requests.put(replica + '/create_user', json=user.__dict__)
    return user.dumps(), 200


@app.put('/create_user')
def insert_user():
    user = User.loads(request.json)
    db.users.insert_one({'_id': ObjectId(user.user_id), **user.__dict__})
    return 'ok', 200


@app.get('/find_user/<user_id>')
def find_user(user_id: str):
    user = find_user_by_id(user_id)
    return str(json.dumps(user, default=json_util.default)), 200


times = 0
@app.post('/add_funds/<user_id>/<amount>')
def add_credit(user_id: str, amount: int):
    # TODO restrict number of retries for Paxos.NOT_ACCEPTED
    app.logger.info("times: %s, requesting add funds with amount %s, and user_id %s", i, amount, user_id)
    amount = int(amount)
    user = find_user_by_id(user_id)
    user['credit'] += amount
    transaction_id = str(uuid.uuid4())
    user['transaction_id'] = transaction_id
    response, accepted_user = paxos.proposer_prepare(user)
    # go trough another round of paxos when not accepted, retry... once
    if response == Paxos.NOT_ACCEPTED:
        return add_credit(user_id, amount) 
    if accepted_user['transaction_id']!=user['transaction_id']:     
        return add_credit(user_id, amount)
    return 'ACCEPTED', 200

@app.post('/pay/<user_id>/<order_id>/<amount>')
def remove_credit(user_id: str, order_id: str, amount: int):
    amount = int(amount)
    user = find_user_by_id(user_id)
    if user['credit'] < amount:
        return 'Insufficient credit', 400

    user['credit'] -= amount
    user['transaction_id'] = str(uuid.uuid4())
    response, accepted_user = paxos.proposer_prepare(user)

    # go trough another round of paxos when not accepted, retry... once
    if response == Paxos.NOT_ACCEPTED:
        return remove_credit(user_id, order_id, amount) 
    if accepted_user['transaction_id']!=user['transaction_id']:     
        return remove_credit(user_id, order_id, amount)
    payment = {'user_id': user_id, 'status': OrderStatus.PAYED}
    db.payments.insert_one(payment)
    payment['payment_id'] = str(payment.pop('_id'))
    return json.dumps(payment), 200


@app.post('/cancel/<user_id>/<order_id>')
def cancel_payment(user_id: str, order_id: str):
    """
    Cancels the payment (should this method alsoa dd the amount of the order
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
    return json.dumps(payment), 200


@app.post('/status/<user_id>/<order_id>')
def payment_status(user_id: str, order_id: str):
    payment = db.payments.find_one(
        {'_id': ObjectId(user_id), 'payments.order_id': order_id}
    )
    return payment['status'], 200


@app.post('/prepare')
def paxos_acceptor_prepare():
    content = request.json
    app.logger.info('prepare content %s', str(content))
    return paxos.acceptor_prepare(content['proposal_id'], content['proposal_value'])


@app.post('/accept')
def acceptor_accept():
    content = request.json
    app.logger.info('content log %s', str(content))
    return paxos.acceptor_accept(content['accepted_id'], content['accepted_value'])


@app.get('/hallo')
def hallo():
    return json.dumps(payment_replicas), 200

# requests.post("http://host.docker.internal:8000/payment/alive")

# endregion

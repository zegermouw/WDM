import atexit
import os
from enum import Enum

from flask import Flask

import json

from bson import json_util
import pymongo
from pymongo import ReturnDocument
from bson.objectid import ObjectId

from models import User

app = Flask("payment-service")

myclient = pymongo.MongoClient(os.environ['GATEWAY_URL'], int(os.environ['PORT']))
db = myclient["local"]


def close_db_connection():
    myclient.close()


atexit.register(close_db_connection)


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
    user = User()
    user_id = db.users.insert_one(user.dict()).inserted_id
    return json.dumps({'user_id': str(user_id)}), 200


@app.get('/find_user/<user_id>')
def find_user(user_id: str):
    user = find_user_by_id(user_id)
    return str(json.dumps(user, default=json_util.default)), 200


@app.post('/add_funds/<user_id>/<amount>')
def add_credit(user_id: str, amount: int):
    amount = int(amount)
    user = db.users.find_one_and_update(
        {'_id': ObjectId(user_id)},
        {'$inc': {'credit': amount}},
        return_document=ReturnDocument.AFTER
    )
    user['user_id'] = str(user.pop('_id'))
    return json.dumps(user), 200


@app.post('/pay/<user_id>/<order_id>/<amount>')
def remove_credit(user_id: str, order_id: str, amount: int):
    amount = int(amount)
    user = find_user_by_id(user_id)
    if user['credit'] < amount:
        return 'Insufficient credit', 400
    # block user account from removing/adding credit
    # send ready to commit to coordinator

    # On commit response:
    # TODO check if this update returns ok status
    db.users.find_one_and_update(
        {'_id': ObjectId(user_id)},
        {'$inc': {'credit': -amount}},
    )
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


@app.post('/prepare-pay/<user_id>/<order_id>/<amount>')
def prepare_pay(user_id: str, order_id: str, amount: float):
    # here we should freeze the account of user_id
    return '', 200


@app.post('/rollback-pay/<user_id>/<order_id>/<amount>')
def rollback_pay(user_id: str, order_id: str, amount: float):
    # here we should roll back any changes and remove the locks
    return '', 200


@app.post('/commit-pay/<user_id>/<order_id>/<amount>')
def commit_pay(user_id: str, order_id: str, amount: float):
    # here we can debit the account and remove the lock
    return '', 200

# endregion

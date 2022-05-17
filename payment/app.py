import atexit
import os
from enum import Enum

from bson.objectid import ObjectId
from flask import Flask
from pymongo import MongoClient

app = Flask("payment-service")

client = MongoClient(os.environ['GATEWAY_URL'], 27017)
db = client['local']

def close_db_connection():
    db.close()


atexit.register(close_db_connection)

# region MODEL

# USER {
#   _id: str
#   credit: int
#   orders: [
#       Order {
#           order_id: str
#           credit_paid: int
#           status: Status
#       }
#   ]
# }

class OrderStatus(str, Enum):
    IN_TRANSACTION = 'IN_TRANSACTION'
    PROCESSED = 'PROCESSED'
    CANCELLED = 'CANCELLED'

# endregion

# region SERVICES

def find_user(user_id: str):
    return db.payment.find_one({'_id': ObjectId(user_id)})

def find_order(user_id: str, order_id: str):
    return db.payment.aggregate([
        {'$match': {'_id': ObjectId(user_id)}},
        {'$unwind': '$orders'},
        {'$match': {'orders.order_id': order_id}}
    ]).next()['orders']

# endregion

# region ENDPOINTS

# USER {
#   user_id: str
#   credit: int
#   orders: [
#       Order {
#           order_id: str
#           credit_paid: int
#           status: Status
#       }
#   ]
# }

class OrderStatus(Enum):
    IN_TRANSACTION = 0
    PROCESSED = 1
    CANCELLED = 2

@app.post('/create_user')
def create_user():
    pass


@app.get('/find_user/<user_id>')
def find_user(user_id: str):
    return find_user(user_id), 200


@app.post('/add_funds/<user_id>/<amount>')
def add_credit(user_id: str, amount: int):
    db.payment.find_one_and_update(
        {'_id': ObjectId(user_id)},
        {'$inc': {'credit': amount}}
    )
    return find_user(user_id), 200


@app.post('/pay/<user_id>/<order_id>/<amount>')
def remove_credit(user_id: str, order_id: str, amount: int):
    if find_user(user_id)['credit'] < amount:
        return 'Insufficient credit', 400

    db.payment.find_one_and_update(
        {'_id': ObjectId(user_id)},
        {'$inc': {'credit': -amount}}
    )
    db.payment.find_one_and_update(
        {'_id': ObjectId(user_id), 'orders.order_id': order_id},
        {'$inc': {'orders.$.credit_paid': amount}}
    )

    return find_order(user_id, order_id), 200


@app.post('/cancel/<user_id>/<order_id>')
def cancel_payment(user_id: str, order_id: str):
    db.payment.find_one_and_update(
        {'_id': ObjectId(user_id), 'orders.order_id': order_id},
        {'$set': {'orders.$.status': f'{OrderStatus.CANCELLED}'}}
    )

    return find_order(user_id, order_id), 200


@app.post('/status/<user_id>/<order_id>')
def payment_status(user_id: str, order_id: str):
    return find_order(user_id, order_id)['status'], 200

# endregion

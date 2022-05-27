import atexit
import os
from enum import Enum

from bson.objectid import ObjectId
from flask import Flask

import redis
import json

from bson import json_util
import pydantic
import pymongo
from bson.objectid import ObjectId

from models import User


app = Flask("payment-service")

# db: redis.Redis = redis.Redis(host=os.environ['REDIS_HOST'],
#                               port=int(os.environ['REDIS_PORT']),
#                               password=os.environ['REDIS_PASSWORD'],
#                               db=int(os.environ['REDIS_DB']))

myclient = pymongo.MongoClient("mongodb://payment-db:27017/db", 27017)
db = myclient["local"]
# col = db["users"]

def close_db_connection():
    myclient.close()


atexit.register(close_db_connection)

# region MODEL

# USER {
#   _id: str
#   credit: int
#   payments: [
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
        {'$unwind': '$payments'},
        {'$match': {'payments.order_id': order_id}}
    ]).next()['payments']

# endregion

# region ENDPOINTS

@app.post('/create_user')
def create_user():
    user = User()
    user_id = db.users.insert_one(user.dict()).inserted_id
    return str(user_id), 200


@app.get('/find_user/<user_id>')
def find_user(user_id: str):
    user = find_user(user_id), 200
    return str(json.dumps(user, default=json_util.default)), 200


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
        {'_id': ObjectId(user_id), 'payments.order_id': order_id},
        {'$inc': {'payments.$.credit_paid': amount}}
    )

    return find_order(user_id, order_id), 200


@app.post('/cancel/<user_id>/<order_id>')
def cancel_payment(user_id: str, order_id: str):
    db.payment.find_one_and_update(
        {'_id': ObjectId(user_id), 'payments.order_id': order_id},
        {'$set': {'payments.$.status': f'{OrderStatus.CANCELLED}'}}
    )

    return find_order(user_id, order_id), 200


@app.post('/status/<user_id>/<order_id>')
def payment_status(user_id: str, order_id: str):
    return find_order(user_id, order_id)['status'], 200

# endregion

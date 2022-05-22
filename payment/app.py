import os
import atexit

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

@app.post('/create_user')
def create_user():
    user = User()
    user_id = db.users.insert_one(user.dict()).inserted_id
    return str(user_id), 200


@app.get('/find_user/<user_id>')
def find_user(user_id: str):
    user = db.users.find_one({"_id": ObjectId(user_id)})
    return str(json.dumps(user, default=json_util.default)), 200


@app.post('/add_funds/<user_id>/<amount>')
def add_credit(user_id: str, amount: int):
    pass


@app.post('/pay/<user_id>/<order_id>/<amount>')
def remove_credit(user_id: str, order_id: str, amount: int):
    pass


@app.post('/cancel/<user_id>/<order_id>')
def cancel_payment(user_id: str, order_id: str):
    pass


@app.post('/status/<user_id>/<order_id>')
def payment_status(user_id: str, order_id: str):
    pass

import os
import atexit
import json
from pymongo import MongoClient
from flask import Flask
from bson import json_util
from bson.objectid import ObjectId

gateway_url = os.environ['GATEWAY_URL']

app = Flask("order-service")

client = MongoClient('mongodb://order-db:27017/db', 27017)
db = client['local']


def close_db_connection():
    db.close()


atexit.register(close_db_connection)


# TODO: handle error handling for when mongodb fails.
# TODO: Better handle mongodb responses.

@app.post('/create/<user_id>')
def create_order(user_id):
    order = {'user_id:': user_id}
    order_id = db.orders.insert_one(order).inserted_id
    return str(order_id), 200


@app.delete('/remove/<order_id>')
def remove_order(order_id):
    status = db.orders.delete_one({"_id": ObjectId(order_id)})
    return str(status), 200


@app.post('/addItem/<order_id>/<item_id>')
def add_item(order_id, item_id):
    order = db.orders.find_one({"_id": ObjectId(order_id)})
    order.setdefault('items', []).append(item_id)
    db.orders.update_one({"_id": order_id}, {"$set": order}, upsert=False)
    return f'Added item: {item_id}', 200


@app.delete('/removeItem/<order_id>/<item_id>')
def remove_item(order_id, item_id):
    order = db.orders.find_one({"_id": ObjectId(order_id)})
    if item_id in order['items']:
        order['items'].remove(order['items'])
        db.orders.update_one({"_id": order_id}, {"$set": order}, upsert=False)
        return f'Removed item: {item_id}', 200
    else:
        print('this does not exist')
        return f'Item {item_id} does not exist', 400


@app.get('/find/<order_id>')
def find_order(order_id):
    order = db.orders.find_one({"_id": ObjectId(order_id)})
    return str(json.dumps(order, default=json_util.default)), 200


@app.post('/checkout/<order_id>')
def checkout(order_id):
    pass

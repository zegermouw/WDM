import os
import atexit
import sys

from orderutils import find_item, pay_order

from pymongo import MongoClient
from flask import Flask, jsonify
from bson.objectid import ObjectId

from order import Order

gateway_url = os.environ['GATEWAY_URL']

app = Flask("order-service")

client = MongoClient(os.environ['GATEWAY_URL'], int(os.environ['PORT']))
db = client['local']


def close_db_connection():
    db.close()


atexit.register(close_db_connection)

locks = []


def delete_one(order_id):
    if order_id in locks:
        return False
    else:
        status = db.orders.delete_one({"_id": ObjectId(order_id)})
        return str(status)


def update_one(order_id, order):
    if order_id in locks:
        return False
    else:
        status = db.orders.update_one({"_id": ObjectId(order_id)}, {"$set": order.__dict__}, upsert=False)
        return str(status)


@app.post('/create/<user_id>')
def create_order(user_id):
    order = Order(user_id=user_id)
    db.orders.insert_one(order.__dict__)
    order.order_id = str(order.__dict__.pop('_id'))  # Since order should have order_id instead of _id.
    return jsonify(order), 200


@app.delete('/remove/<order_id>')
def remove_order(order_id):
    status = delete_one(order_id)
    if not status:
        return 'The orderid is locked', 400
    else:
        return f'Removed item {order_id} successfully', 200


@app.post('/addItem/<order_id>/<item_id>')
def add_item(order_id, item_id):
    j = db.orders.find_one({"_id": ObjectId(order_id)})
    order = Order.loads(j)
    order.items.append(item_id)
    status = update_one(order_id, order)
    if not status:
        return 'The orderid is locked', 400
    else:
        return jsonify(order), 200


@app.delete('/removeItem/<order_id>/<item_id>')
def remove_item(order_id, item_id):
    order = db.orders.find_one({"_id": ObjectId(order_id)})
    if item_id in order['items']:
        order['items'].remove(item_id)
        status = update_one(order_id, order)
        if not status:
            return 'The orderid is locked', 400
        else:
            return f'Removed item: {item_id}', 200
    else:
        print('this does not exist')
        return f'Item {item_id} does not exist', 400


@app.get('/find/<order_id>')
def find_order(order_id):
    order = db.orders.find_one({"_id": ObjectId(order_id)})
    order = Order.loads(order)
    return jsonify(order), 200


@app.post('/checkout/<order_id>')
def checkout(order_id):
    order = db.orders.find_one({"_id": ObjectId(order_id)})
    order = Order.loads(order)

    total_checkout_amount: int = 0
    for item_id in order.items:
        response = find_item(item_id)

        if response.status_code != 200:
            return response

        item = response.json()
        total_checkout_amount += item['price']

    items = {}
    for item in order.items:
        if item in items:
            items[item] = items[item] + 1
        else:
            items[item] = 1

    status = pay_order(order.user_id, order_id, items, total_checkout_amount)

    return status.content, status.status_code

import os
import atexit
import sys
from orderutils import subtract_stock, find_item, payment_pay, add_stock

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from flask import Flask
from bson import json_util
from bson.objectid import ObjectId

from order import Order

# gateway_url = os.environ['GATEWAY_URL']

app = Flask("order-service")

client = MongoClient(os.environ['ORDER_GATEWAY'])
db = client['local']
print("started", file=sys.stderr)

def close_db_connection():
    db.close()


atexit.register(close_db_connection)


# TODO: handle error handling for when mongodb fails.
# TODO: Better handle mongodb response format.

@app.post('/create/<user_id>')
def create_order(user_id):
    order = Order(user_id=user_id)
    db.orders.insert_one(order.__dict__)
    order.order_id = str(order.__dict__.pop('_id'))  # Since order should have order_id instead of _id.
    return order.dumps(), 200


@app.delete('/remove/<order_id>')
def remove_order(order_id):
    status = db.orders.delete_one({"_id": ObjectId(order_id)})
    return str(status), 200


@app.post('/addItem/<order_id>/<item_id>')
def add_item(order_id, item_id):
    j = db.orders.find_one({"_id": ObjectId(order_id)})
    order = Order.loads(j)
    order.items.append(item_id)
    db.orders.update_one({"_id": ObjectId(order_id)}, {"$set": order.__dict__}, upsert=False)
    return order.dumps(), 200


@app.delete('/removeItem/<order_id>/<item_id>')
def remove_item(order_id, item_id):
    order = db.orders.find_one({"_id": ObjectId(order_id)})
    if item_id in order['items']:
        order['items'].remove(item_id)
        db.orders.update_one({"_id": ObjectId(order_id)}, {"$set": order}, upsert=False)
        return f'Removed item: {item_id}', 200
    else:
        print('this does not exist')
        return f'Item {item_id} does not exist', 400


@app.get('/find/<order_id>')
def find_order(order_id):
    order = db.orders.find_one({"_id": ObjectId(str(order_id))})
    order = Order.loads(order)
    return order.dumps(), 200


@app.post('/checkout/<order_id>')
def checkout(order_id):
    """
        Reserve stock from stock service and request payment from payment service
            - if stock service has not enough stock for one item, rollback
            - if pyment service fails payment: rollback items.
    """
    order = db.orders.find_one({"_id": ObjectId(order_id)})
    order = Order.loads(order)

    total_checkout_amount: int = 0
    reserved_items = []
    for item_id in order.items:
        request = subtract_stock(item_id, 1)
        if request.status_code == 400:
            # One item has not enough stock, roll back other reserved items
            rollback_items(reserved_items)
            return "not enough stock", 400
        item = request.json()
        total_checkout_amount += item['price']
        reserved_items.append(item_id)

    payment_status: int = payment_pay(order.user_id, order_id, total_checkout_amount)
    if payment_status == 400:
        rollback_items(reserved_items)
        return "not enough mony", 400

    return order.dumps(), 200


def rollback_items(items):
    for item_id in items:
        add_stock(item_id, 1)

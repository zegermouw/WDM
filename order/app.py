import os
import atexit
import sys
import socket
import requests

from orderutils import subtract_stock, find_item, payment_pay, add_stock


from pymongo import MongoClient
from flask import Flask
from flask import request as flask_request

from bson import json_util
from bson.objectid import ObjectId
import kubernetes as k8s

from order import Order


app = Flask("order-service")


client = MongoClient(os.environ['GATEWAY_URL'], int(os.environ['PORT']))
db = client['local']

hostname=socket.gethostname()
IPAddr=socket.gethostbyname(hostname)
print(hostname, file=sys.stderr)
print("running on: " + IPAddr, file=sys.stderr)

k8s.config.load_incluster_config()
v1 = k8s.client.CoreV1Api()

def pingSharding():
    pod_list = v1.list_pod_for_all_namespaces(watch=False)
    print("ping sharding", file=sys.stderr)
    pass


pingSharding()
# vector_clock = 0
# vector_list = []
#
# db_queue = []

def close_db_connection():
    db.close()

atexit.register(close_db_connection)


# TODO: handle error handling for when mongodb fails.
# TODO: Better handle mongodb response format.

@app.get('/test')
def test_get2():
    print("got message from: " + flask_request.remote_addr, file=sys.stderr)
    return "test", 200

@app.get('/')
def test_get():
    print("---------------------------------", file=sys.stderr)
    # this.vector_list = get_pods()
    print("<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<", file=sys.stderr)
    return "joee", 200

@app.post('/create/<user_id>/<order_id>')
def create_order(user_id, order_id):
    print("createOrder(user: " + str(user_id) + ", order: " + str(order_id) + ")", file=sys.stderr)
    order = Order(user_id=user_id, order_id=order_id)
    db.orders.insert_one(order.__dict__)
    # db_queue.append(order)
    print(str(order.dumps()), file=sys.stderr)
    return order.dumps(), 200

# @app.post('/create/frompod/<user_id>')
# def create_order_from_pod(user_id):
#     order = Order(user_id=user_id)
#     db.orders.insert_one(order.__dict__)
#     order.order_id = str(order.__dict__.pop('_id'))  # Since order should have order_id instead of _id.
#     # db_queue.append(order)
#     return order.dumps(), 200

@app.delete('/remove/<order_id>')
def remove_order(order_id):
    print("removeOrder(order: " + str(order_id) + ")", file=sys.stderr)
    status = db.orders.delete_one({"order_id": order_id})
    return str(status), 200


@app.post('/addItem/<order_id>/<item_id>')
def add_item(order_id, item_id):
    print("addItem(order: " + str(order_id) + ", item: " + str(item_id) + ")", file=sys.stderr)
    j = db.orders.find_one({"order_id": order_id})
    order = Order.loads(j)
    order.items.append(item_id)
    db.orders.update_one({"order_id": order_id}, {"$set": order.__dict__}, upsert=False)
    return order.dumps(), 200

@app.delete('/removeItem/<order_id>/<item_id>')
def remove_item(order_id, item_id):
    print("removeItem(order: " + str(order_id) + ", item: " + str(item_id) + ")", file=sys.stderr)
    order = db.orders.find_one({"order_id": order_id})
    if item_id in order['items']:
        order['items'].remove(item_id)
        db.orders.update_one({"order_id": order_id}, {"$set": order}, upsert=False)
        return f'Removed item: {item_id}', 200
    else:
        print('this does not exist')
        return f'Item {item_id} does not exist', 400

@app.get('/all/<order_id>')
def all(order_id):
    print("all", file=sys.stderr)
    orders = list(db.orders.find({}))
    return str(orders), 200

@app.get('/find/<order_id>')
def find_order(order_id):
    print("I did this!!", file=sys.stderr)
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
    order = db.orders.find_one({"order_id": order_id})
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
        return "not enough money", 400

    return order.dumps(), 200


def rollback_items(items):
    for item_id in items:
        add_stock(item_id, 1)

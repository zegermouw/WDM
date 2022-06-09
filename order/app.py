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

# gateway_url = os.environ['GATEWAY_URL']

app = Flask("order-service")

client = MongoClient(os.environ['ORDER_GATEWAY'], int(os.environ['ORDER_PORT']))
db = client['local']
k8s.config.load_incluster_config()
v1 = k8s.client.CoreV1Api()
hostname=socket.gethostname()
IPAddr=socket.gethostbyname(hostname)
print(hostname, file=sys.stderr)
print("running on: " + IPAddr, file=sys.stderr)

def close_db_connection():
    db.close()

def get_pods():
    pod_list = v1.list_pod_for_all_namespaces(watch=False)
    dict = []
    for pod in pod_list.items:
        if("order-deployment" in pod.metadata.name and pod.status.phase == 'Running'):
            dict.append({'name': pod.metadata.name, 'ip': pod.status.pod_ip})
    print(dict, file=sys.stderr)
    for dic in dict:
        if(dic["ip"] != IPAddr):
            requests.get("http://" + dic["ip"] + ":5000/test")

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
    get_pods()
    print("<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<", file=sys.stderr)
    return "joee", 200

@app.post('/create/<user_id>')
def create_order(user_id):
    order = Order(user_id=user_id)
    db.orders.insert_one(order.__dict__)
    order.order_id = str(order.__dict__.pop('_id'))  # Since order should have order_id instead of _id.
    return jsonify(order), 200


@app.delete('/remove/<order_id>')
def remove_order(order_id):
    status = db.orders.delete_one({"_id": ObjectId(order_id)})
    if not status:
        return 'The orderid is locked', 400
    else:
        return f'Removed item {order_id} successfully', 200


@app.post('/addItem/<order_id>/<item_id>')
def add_item(order_id, item_id):
    j = db.orders.find_one({"_id": ObjectId(order_id)})
    order = Order.loads(j)
    order.items.append(item_id)
    status = db.orders.update_one({"_id": ObjectId(order_id)}, {"$set": order.__dict__}, upsert=False)
    if not status:
        return 'The orderid is locked', 400
    else:
        return jsonify(order), 200

@app.delete('/removeItem/<order_id>/<item_id>')
def remove_item(order_id, item_id):
    order = db.orders.find_one({"_id": ObjectId(order_id)})
    if item_id in order['items']:
        order['items'].remove(item_id)
        status = db.orders.update_one({"_id": ObjectId(order_id)}, {"$set": order}, upsert=False)
        if not status:
            return 'The orderid is locked', 400
        else:
            return f'Removed item: {item_id}', 200
    else:
        print('this does not exist')
        return f'Item {item_id} does not exist', 400


@app.get('/find/<order_id>')
def find_order(order_id):
    print("I did this!!", file=sys.stderr)
    order = db.orders.find_one({"_id": ObjectId(str(order_id))})
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


def rollback_items(items):
    for item_id in items:
        add_stock(item_id, 1)

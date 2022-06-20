import os
import atexit
import sys
import sys
import socket
import requests

from orderutils import find_item, pay_order

from pymongo import MongoClient
from flask import Flask, jsonify
from bson.objectid import ObjectId
import kubernetes as k8s

from order import Order

gateway_url = os.environ['GATEWAY_URL']

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


@app.delete('/remove/<order_id>')
def remove_order(order_id):
    print("removeOrder(order: " + str(order_id) + ")", file=sys.stderr)
    status = db.orders.delete_one({"order_id": order_id})
    if not status:
        return 'The orderid is locked', 400
    else:
        return f'Removed item {order_id} successfully', 200


@app.post('/addItem/<order_id>/<item_id>')
def add_item(order_id, item_id):
    print("addItem(order: " + str(order_id) + ", item: " + str(item_id) + ")", file=sys.stderr)
    j = db.orders.find_one({"order_id": order_id})
    order = Order.loads(j)
    order.items.append(item_id)
    status = db.orders.update_one({"order_id": order_id}, {"$set": order.__dict__}, upsert=False)
    if not status:
        return 'The orderid is locked', 400
    else:
        return jsonify(order), 200

@app.delete('/removeItem/<order_id>/<item_id>')
def remove_item(order_id, item_id):
    print("removeItem(order: " + str(order_id) + ", item: " + str(item_id) + ")", file=sys.stderr)
    order = db.orders.find_one({"order_id": order_id})
    if item_id in order['items']:
        order['items'].remove(item_id)
        status = db.orders.update_one({"order_id": order_id}, {"$set": order}, upsert=False)
        if not status:
            return 'The orderid is locked', 400
        else:
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
    order = db.orders.find_one({"order_id": order_id})
    order = Order.loads(order)
    return jsonify(order), 200


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
    print("status", file=sys.stderr)
    print(str(status), file=sys.stderr)
    return status.content, status.status_code

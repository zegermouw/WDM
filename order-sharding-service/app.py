import requests
from flask import Flask
from flask import request as flask_request
import kubernetes as k8s

import sys
import uuid
import math
from order import Order

k8s.config.load_incluster_config()
v1 = k8s.client.CoreV1Api()
podlist = []
num_shards = 0


def get_pods():
    global podlist
    global num_shards
    pod_list = v1.list_pod_for_all_namespaces(watch=False)
    num_shards = 0
    count = 0
    for pod in pod_list.items:
        if "order-deployment" in pod.metadata.name and pod.status.phase == 'Running':
            num_shards = num_shards + 1
    num_shards = int(num_shards / 2)
    for pod in pod_list.items:
        if "order-deployment" in pod.metadata.name and pod.status.phase == 'Running':
            podlist.append({'name': pod.metadata.name, 'ip': pod.status.pod_ip, 'shard_number': (count % num_shards),
                            'order': math.floor((count / num_shards))})
            count = count + 1
    print(podlist, file=sys.stderr)


def getShard(order_id):
    shard_number = int(order_id) % num_shards
    for pod in podlist:
        if (pod['shard_number'] == shard_number):
            return {"ret": True, "val": pod}
    return {"ret": False, "val": 0}


app = Flask("order-sharding-service")


# for dic in pods_dict:
#     if(dic["ip"] != IPAddr):
#         requests.get("http://" + dic["ip"] + ":5000/test")
# return pods_dict

@app.before_first_request
def setup():
    print("started", file=sys.stderr)
    get_pods()


@app.post('/create/<user_id>')
def create_order(user_id):
    order_id = uuid.uuid4().int
    shard = getShard(order_id)
    # get correct pod with unique_id + save unique id to db
    # call save function on that pod
    if shard['ret']:
        return_val = requests.post(
            'http://' + str(shard['val']['ip']) + ':5000/create/' + str(user_id) + '/' + str(order_id))
        return return_val.content, 200
    else:
        return "could not find pod", 500


@app.delete('/remove/<order_id>')
def remove_order(order_id):
    shard = getShard(order_id)
    if shard['ret']:
        return_val = requests.delete('http://' + str(shard['val']['ip']) + ':5000/remove/' + str(order_id))
        return return_val.content, 200
    else:
        return "could not find pod", 500


@app.post('/addItem/<order_id>/<item_id>')
def add_item(order_id, item_id):
    shard = getShard(order_id)
    if shard['ret']:
        return_val = requests.post('http://' + str(shard['val']['ip'])
                                   + ':5000/addItem/' + str(order_id) + "/" + str(item_id))
        return return_val.content, 200
    else:
        return "could not find pod", 500


@app.get('/all/<order_id>')
def all(order_id):
    shard = getShard(order_id)
    if shard['ret']:
        return_val = requests.get('http://' + str(shard['val']['ip'])
                                   + ':5000/all/' + str(order_id))
        return return_val.content, 200
    else:
        return "could not find pod", 500

@app.delete('/removeItem/<order_id>/<item_id>')
def remove_item(order_id, item_id):
    shard = getShard(order_id)
    if shard['ret']:
        return_val = requests.delete('http://' + str(shard['val']['ip'])
                                   + ':5000/removeItem/' + str(order_id) + "/" + str(item_id))
        return return_val.content, 200
    else:
        return "could not find pod", 500


@app.post('/checkout/<order_id>')
def checkout(order_id):
    shard = getShard(order_id)
    if shard['ret']:
        return_val = requests.post('http://' + str(shard['val']['ip'])
                                  + ':5000/checkout/' + str(order_id))
        return return_val.content, 200
    else:
        return "could not find pod", 500

@app.get('/test')
def test_get2():
    return "test", 200


def log(*args):
    print(f'[{datetime.datetime.now()}]', *args, file=sys.stderr)
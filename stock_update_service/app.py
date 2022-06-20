
import asyncio

import sys
import socket
import threading
import requests
from flask import Flask 
import kubernetes as k8s
import threading
Thread = threading.Thread



app = Flask("stockupdate-service")


print('hallo world', file=sys.stderr)

# get replica pods using kubernets api
k8s.config.load_incluster_config()
v1 = k8s.client.CoreV1Api()
hostname=socket.gethostname()
IPAddr=socket.gethostbyname(hostname)
print(hostname, file=sys.stderr)
print("running on: " + IPAddr, file=sys.stderr)




def get_pods():
    """
    Gets replica ip addresses and stores them im replicas set
    TODO add extra check after timeout to check if its still alive since shuting down can take some time. (try something like javascript timeout)
    """
    replicas = {}
    pod_list = v1.list_pod_for_all_namespaces(watch=False)
    for pod in pod_list.items:
        if(pod.metadata.name != hostname and "stock-deployment" in pod.metadata.name and pod.status.phase == 'Running'):
            url = f'http://{pod.status.pod_ip}:5000'
            replicas[pod.metadata.name] = url
    return replicas

# update service with other logs



def log_iterator(pods, log):
    for replica_url in pods.values():
        try:
            response = requests.get(f'{replica_url}/log', json=log)
        except requests.exceptions.ConnectionError as e:
            print(str(e), file=sys.stderr)
            continue
        if response.status_code != 200:
            continue # request did not turn ok so no log
        yield response.json()



def query_logs_and_update(log):
    pods = get_pods()
    for other_log in log_iterator(pods, log):
        log = merge_log(log, other_log)
    return log

def merge_log(log1, log2):
    for k,v in log2.items():
        log1[k] = v
    return log1




class MyThread(Thread):
    def run(self):
        loop = asyncio.new_event_loop()  # loop = asyncio.get_event_loop()
        loop.run_until_complete(self._run())
        loop.close()
        # asyncio.run(self._run())    In Python 3.7+

    async def _run(self):
        log = {}
        print("querying stock logs started", file=sys.stderr)
        while True:
            await asyncio.sleep(1)
            log = query_logs_and_update(log)


t = MyThread()
t.start()
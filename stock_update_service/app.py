import os
import sys
import socket
import threading
import requests
import kubernetes as k8s
import threading
Thread = threading.Thread

import asyncio


print('hallo world', file=sys.stderr)

# get replica pods using kubernets api
k8s.config.load_incluster_config()
v1 = k8s.client.CoreV1Api()
hostname=socket.gethostname()
IPAddr=socket.gethostbyname(hostname)
print(hostname, file=sys.stderr)
print("running on: " + IPAddr, file=sys.stderr)




replicas = {}
def get_pods():
    """
    Gets replica ip addresses and stores them im replicas set
    TODO add extra check after timeout to check if its still alive since shuting down can take some time. (try something like javascript timeout)
    """
    global replicas
    replicas = {}
    pod_list = v1.list_pod_for_all_namespaces(watch=False)
    for pod in pod_list.items:
        if(pod.metadata.name != hostname and "stock-deployment" in pod.metadata.name and pod.status.phase == 'Running'):
            url = f'http://{pod.status.pod_ip}:5000'
            print(e, file=sys.stderr)


# update service with other logs


merged_log = {}

def log_iterator():
    global merge_log
    replica_copy = list(replicas.values())
    for replica_url in replica_copy:
        print(f'querying {replica_url}', file=sys.stderr)
        try:
            response = requests.get(f'{replica_url}/log', json=merge_log)
        except requests.exceptions.ConnectionError as e:
            print(str(e), file=sys.stderr)
            continue
        if response.status_code != 200:
            continue # request did not turn ok so no log
        yield response.json()



def query_logs_and_update():
    get_pods()
    for other_log in log_iterator():
        merge_log(other_log)


def merge_log(log):
    for k,v in log.items():
        merge_log[k] = v


async def myWork():
    print("Starting Work", file=sys.stderr)
    query_logs_and_update()
    await asyncio.sleep(1)

loop = asyncio.get_event_loop()
try:
    loop.run_until_complete(myWork())
finally:
    loop.close()
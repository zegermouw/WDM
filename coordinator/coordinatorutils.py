import requests
import json
from requests import Response

ORDER_URL = STOCK_URL = PAYMENT_URL = "http://host.docker.internal:8000"
ORDER_SERVICE = "http://order-service:5000"
COORDINATOR_SERVICE = "http://coordinator-service:5000"
STOCK_SERVICE = "http://stock-service:5000"
PAYMENT_SERVICE = "http://payment-service:5000"

def prepare_pay(user_id: str, price: float) -> Response:
    return requests.post(f"{PAYMENT_SERVICE}/prepare_pay/{user_id}/{price}")


def rollback_pay(user_id: str, price: float) -> int:
    return requests.post(f"{PAYMENT_SERVICE}/rollback_pay/{user_id}/{price}").status_code


def commit_pay(user_id: str, order_id: str, price: float) -> int:
    return requests.post(f"{PAYMENT_SERVICE}/commit_pay/{user_id}/{order_id}/{price}").status_code


def prepare_stock(item_ids: [str]) -> Response:
    return requests.post(f"{STOCK_SERVICE}/prepare_stock", json=item_ids)


def commit_stock(item_ids: [str]) -> int:
    return requests.post(f"{STOCK_SERVICE}/commit_stock", json=item_ids).status_code


def rollback_stock(item_ids: [str]) -> int:
    return requests.post(f"{STOCK_SERVICE}/rollback_stock", json=item_ids).status_code


def read_locking_doc():
    file = open("locking_doc.json")
    user_dict = json.load(file)
    file.close()
    return user_dict


def lock(user_id: str, item_ids: [str], lock_items: bool):
    file = open("locking_doc.json", "r")
    file_data = json.load(file)
    file_data["users"].append(user_id)
    if lock_items:
        file_data["items"].extend(item_ids)
    file.close()
    file = open("locking_doc.json", "w")
    json.dump(file_data, file, indent=4)
    file.close()


def unlock(user_id: str, item_ids: [str]):
    file = open("locking_doc.json", "r")
    file_data = json.load(file)
    file_data["users"] = list(filter(lambda x: x != user_id, file_data["users"]))
    file_data["items"] = list(filter(lambda x: x not in item_ids, file_data["items"]))
    file.close()
    file = open("locking_doc.json", "w")
    json.dump(file_data, file, indent=4)
    file.close()


def is_user_item_locked(user_id: str, item_ids: [str]):
    with open("locking_doc.json", 'r+') as file:
        file_data = json.load(file)
        for item_id in item_ids:
            if item_id in file_data["items"]:
                return True
        if user_id in file_data["users"]:
            return True

        return False

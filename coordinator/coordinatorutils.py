import requests
import json

ORDER_URL = STOCK_URL = PAYMENT_URL = "http://host.docker.internal:8000"


def prepare_checkout(order_id: str) -> int:
    return requests.post(f"{ORDER_URL}/orders/prepare-checkout/{order_id}").status_code


def rollback_checkout(order_id: str) -> int:
    return requests.post(f"{ORDER_URL}/orders/rollback-checkout/{order_id}").status_code


def commit_checkout(order_id: str) -> int:
    return requests.post(f"{ORDER_URL}/orders/commit-checkout/{order_id}").status_code


def prepare_pay(user_id: str, order_id: str, amount: float) -> int:
    return requests.post(f"{PAYMENT_URL}/payment/prepare-pay/{user_id}/{order_id}/{amount}").status_code


def rollback_pay(user_id: str, order_id: str, amount: float) -> int:
    return requests.post(f"{PAYMENT_URL}/payment/rollback-pay/{user_id}/{order_id}/{amount}").status_code


def commit_pay(user_id: str, order_id: str, amount: float) -> int:
    return requests.post(f"{PAYMENT_URL}/payment/commit-pay/{user_id}/{order_id}/{amount}").status_code

def read_locking_doc():
    file = open("locking_doc.json")
    user_dict = json.load(file)
    file.close()
    return user_dict

def write_locking_doc(user_id: str, order_id: str):
    file = open("locking_doc.json", "r")
    file_data = json.load(file)
    file_data["locked_users_orders"]["users"].append(user_id)
    file_data["locked_users_orders"]["orders"].append(order_id)
    file.close()
    file = open("locking_doc.json", "w")
    json.dump(file_data, file, indent = 4)
    file.close()

def write_unlocking_doc(user_id: str, order_id: str):
    file = open("locking_doc.json", "r")
    file_data = json.load(file)
    file_data["locked_users_orders"]["users"].remove(user_id)
    file_data["locked_users_orders"]["orders"].remove(order_id)
    file.close()
    file = open("locking_doc.json", "w")
    json.dump(file_data, file, indent = 4)
    file.close()

def is_user_in_doc(value: str):
    with open("locking_doc.json",'r+') as file:
        file_data = json.load(file)
        if value in file_data["locked_users_orders"]["users"]:
            return True
        else:
            return False


import requests

ORDER_URL = STOCK_URL = PAYMENT_URL = "http://host.docker.internal:8000"


def prepare_checkout(order_id: str) -> int:
    return requests.post(f"{ORDER_URL}/order/prepare-checkout/{order_id}").status_code


def rollback_checkout(order_id: str) -> int:
    return requests.post(f"{ORDER_URL}/order/rollback-checkout/{order_id}").status_code


def commit_checkout(order_id: str) -> int:
    return requests.post(f"{ORDER_URL}/order/commit-checkout/{order_id}").status_code


def prepare_pay(user_id: str, order_id: str, amount: float) -> int:
    return requests.post(f"{PAYMENT_URL}/payment/prepare-pay/{user_id}/{order_id}/{amount}").status_code


def rollback_pay(user_id: str, order_id: str, amount: float) -> int:
    return requests.post(f"{PAYMENT_URL}/payment/rollback-pay/{user_id}/{order_id}/{amount}").status_code


def commit_pay(user_id: str, order_id: str, amount: float) -> int:
    return requests.post(f"{PAYMENT_URL}/payment/commit-pay/{user_id}/{order_id}/{amount}").status_code

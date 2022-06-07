import requests

ORDER_URL = STOCK_URL = PAYMENT_URL = "http://host.docker.internal:8000"


def prepare_pay(user_id: str, order_id: str, price: float) -> int:
    return requests.post(f"{PAYMENT_URL}/payment/prepare-pay/{user_id}/{order_id}/{price}").status_code


def rollback_pay(user_id: str, order_id: str, price: float) -> int:
    return requests.post(f"{PAYMENT_URL}/payment/rollback-pay/{user_id}/{order_id}/{price}").status_code


def commit_pay(user_id: str, order_id: str, price: float) -> int:
    return requests.post(f"{PAYMENT_URL}/payment/commit-pay/{user_id}/{order_id}/{price}").status_code


def prepare_stock(item_ids: [str]) -> int:
    return requests.post(f"{PAYMENT_URL}/stock/prepare-stock", json=item_ids).status_code


def commit_stock(item_ids: [str]) -> int:
    return requests.post(f"{PAYMENT_URL}/stock/commit-stock", json=item_ids).status_code


def rollback_stock(item_ids: [str]) -> int:
    return requests.post(f"{PAYMENT_URL}/stock/rollback-stock", json=item_ids).status_code

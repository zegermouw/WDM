import requests
from requests import Response

ORDER_URL = STOCK_URL = PAYMENT_URL = COORDINATOR_URL = "http://host.docker.internal:8000"


# def subtract_stock(item_id: str, amount: int) -> (dict, int):
#     return requests.post(f"{STOCK_URL}/stock/subtract/{item_id}/{amount}")


def find_item(item_id: str) -> Response:
    return requests.get(f"{STOCK_URL}/stock/find/{item_id}")


# def payment_pay(user_id: str, order_id: str, amount: float) -> int:
#     return requests.post(f"{PAYMENT_URL}/payment/pay/{user_id}/{order_id}/{amount}").status_code


# def add_stock(item_id: str, amount: int) -> int:
#     return requests.post(f"{STOCK_URL}/stock/add/{item_id}/{amount}").status_code


def pay_order(user_id: str, order_id: str, item_ids: [str], price: float) -> Response:
    return requests.post(f"{COORDINATOR_URL}/pay/{user_id}/{order_id}/{price}", json=item_ids)

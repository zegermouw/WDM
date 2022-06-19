import requests
from requests import Response

# TODO: will change in Kubernetes
ORDER_URL = STOCK_URL = PAYMENT_URL = COORDINATOR_URL = "http://host.docker.internal:8000"


def find_item(item_id: str) -> Response:
    return requests.get(f"{STOCK_URL}/stock/find/{item_id}")


def pay_order(user_id: str, order_id: str, item_ids: [str], price: float) -> Response:
    return requests.post(f"{COORDINATOR_URL}/coordinator/pay/{user_id}/{order_id}/{price}", json=item_ids)

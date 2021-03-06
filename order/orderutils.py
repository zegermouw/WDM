import requests
from requests import Response

COORDINATOR_SERVICE = "http://coordinator-service:5000"
STOCK_SERVICE = "http://stock-service:5000"


def find_item(item_id: str) -> Response:
    return requests.get(f"{STOCK_SERVICE}/find/{item_id}")


def pay_order(user_id: str, order_id: str, item_ids: [str], price: float) -> Response:
    return requests.post(f"{COORDINATOR_SERVICE}/pay/{user_id}/{order_id}/{price}", json=item_ids)

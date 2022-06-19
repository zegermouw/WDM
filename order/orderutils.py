import requests
ORDER_URL = STOCK_URL = PAYMENT_URL = "http://stock-service:5000"


def subtract_stock(item_id: str, amount: int) -> (dict, int):
    return requests.post(f"{STOCK_URL}/stock/subtract/{item_id}/{amount}")



def find_item(item_id: str) -> dict:
    return requests.get(f"{STOCK_URL}/stock/find/{item_id}").json()


def payment_pay(user_id: str, order_id: str, amount: float) -> int:
    return requests.post(f"{PAYMENT_URL}/payment/pay/{user_id}/{order_id}/{amount}").status_code


def add_stock(item_id: str, amount: int) -> int:
    return requests.post(f"{STOCK_URL}/stock/add/{item_id}/{amount}").status_code


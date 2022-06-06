import requests
import grequests

ORDER_URL = STOCK_URL = PAYMENT_URL = "http://127.0.0.1:8000"


########################################################################################################################
#   STOCK MICROSERVICE FUNCTIONS
########################################################################################################################
def create_item(price: float) -> dict:
    return requests.post(f"{STOCK_URL}/stock/item/create/{price}").json()


def find_item(item_id: str) -> dict:
    return requests.get(f"{STOCK_URL}/stock/find/{item_id}").json()


def add_stock(item_id: str, amount: int) -> int:
    return requests.post(f"{STOCK_URL}/stock/add/{item_id}/{amount}").status_code


def subtract_stock(item_id: str, amount: int) -> int:
    return requests.post(f"{STOCK_URL}/stock/subtract/{item_id}/{amount}").status_code


########################################################################################################################
#   PAYMENT MICROSERVICE FUNCTIONS
########################################################################################################################
def payment_pay(user_id: str, order_id: str, amount: float) -> int:
    return requests.post(f"{PAYMENT_URL}/payment/pay/{user_id}/{order_id}/{amount}").status_code


def create_user() -> dict:
    return requests.post(f"{PAYMENT_URL}/payment/create_user").json()


def find_user(user_id: str) -> dict:
    return requests.get(f"{PAYMENT_URL}/payment/find_user/{user_id}").json()


def add_credit_to_user(user_id: str, amount: float) -> int:
    return requests.post(f"{PAYMENT_URL}/payment/add_funds/{user_id}/{amount}").status_code

# some test for paxos, where docker is setup with 2 service instances of payment
def create_user_service0() -> dict:
    return requests.post(f"{PAYMENT_URL}/payment0/create_user").json()


def find_user_service0(user_id: str) -> dict:
    return requests.get(f"{PAYMENT_URL}/payment0/find_user/{user_id}").json()

def find_user_service1(user_id: str) -> dict:
    return requests.get(f"{PAYMENT_URL}/payment1/find_user/{user_id}").json()


def add_credit_to_user0(user_id: str, amount: float) -> int:
    return requests.post(f"{PAYMENT_URL}/payment0/add_funds/{user_id}/{amount}").status_code

def test_prepare_endpoint(proposal_id: int, proposal_value: dict):
    return requests.post(f"{PAYMENT_URL}/payment0/prepare", json={'proposal_id':proposal_id, 'proposal_value': proposal_value}).status_code

def async_add_credit_to_user(user_id: str, amount: float, service: int) -> int:
    return grequests.post(f"{PAYMENT_URL}/payment{str(service)}/add_funds/{user_id}/{amount}")

########################################################################################################################
#   ORDER MICROSERVICE FUNCTIONS
########################################################################################################################
def create_order(user_id: str) -> dict:
    return requests.post(f"{ORDER_URL}/orders/create/{user_id}").json()


def add_item_to_order(order_id: str, item_id: str) -> int:
    return requests.post(f"{ORDER_URL}/orders/addItem/{order_id}/{item_id}").status_code


def find_order(order_id: str) -> dict:
    return requests.get(f"{ORDER_URL}/orders/find/{order_id}").json()


def checkout_order(order_id: str) -> requests.Response:
    return requests.post(f"{ORDER_URL}/orders/checkout/{order_id}")


########################################################################################################################
#   STATUS CHECKS
########################################################################################################################
def status_code_is_success(status_code: int) -> bool:
    return 200 <= status_code < 300


def status_code_is_failure(status_code: int) -> bool:
    return 400 <= status_code < 500

import atexit
import os
from enum import Enum

from flask import Flask
from pymongo import MongoClient

app = Flask("payment-service")


client = MongoClient(os.environ['GATEWAY_URL'], 27017)
db = client['local']

def close_db_connection():
    db.close()


atexit.register(close_db_connection)


# USER {
#   user_id: str
#   credit: int
#   orders: [
#       Order {
#           order_id: str
#           credit_paid: int
#           status: Status
#       }
#   ]
# }

class OrderStatus(Enum):
    IN_TRANSACTION = 0
    PROCESSED = 1
    CANCELLED = 2

@app.post('/create_user')
def create_user():
    pass


@app.get('/find_user/<user_id>')
def find_user(user_id: str):
    pass


@app.post('/add_funds/<user_id>/<amount>')
def add_credit(user_id: str, amount: int):
    pass


@app.post('/pay/<user_id>/<order_id>/<amount>')
def remove_credit(user_id: str, order_id: str, amount: int):
    pass


@app.post('/cancel/<user_id>/<order_id>')
def cancel_payment(user_id: str, order_id: str):
    pass


@app.post('/status/<user_id>/<order_id>')
def payment_status(user_id: str, order_id: str):
    pass

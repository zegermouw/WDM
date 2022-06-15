import os
import atexit
import sys

from flask import Flask, request
import redis
from stock import Stock

app = Flask("stock-service")

db: redis.Redis = redis.Redis(host=os.environ['REDIS_HOST'],
                              port=int(os.environ['REDIS_PORT']),
                              password=os.environ['REDIS_PASSWORD'],
                              db=int(os.environ['REDIS_DB']))


def close_db_connection():
    db.close()


atexit.register(close_db_connection)


@app.post('/item/create/<price>')
def create_item(price: int):
    """
    Create stock item with given price
    :param price:
    :return: Stock
    """
    s = Stock.new(int(price))
    db.set(s.item_id, s.dumps())
    return s.dumps()


@app.get('/find/<item_id>')
def find_item(item_id: str):
    """
    Get item if it exists
    :param item_id:
    :return: Stock
    """
    return db.get(item_id)


@app.post('/add/<item_id>/<amount>')
def add_stock(item_id: str, amount: int):
    """
    Add amount to stock
    :param item_id:
    :param amount:
    :return: Stock
    """
    d = db.get(item_id)
    s = Stock.loads(d)
    s.stock += int(amount)
    db.set(s.item_id, s.dumps())
    return s.dumps(), 200


def remove_stock(item_id: str, amount: int):
    """
    Remove stock from item with given id.
    :param item_id: The item to subtract amount from.
    :param amount: The amount to remove from the stock.
    :return: Stock item.
    """
    amount = int(amount)
    d = db.get(item_id)
    s = Stock.loads(d)
    if s.stock - amount < 0:
        return False
    s.stock -= amount
    db.set(s.item_id, s.dumps())
    return True


def check_stock(item_id, amount) -> bool:
    d = db.get(item_id)
    s = Stock.loads(d)
    return s.stock >= amount


@app.post('/prepare_stock')
def prepare_stock():
    items = request.json
    for item in items:
        if not check_stock(item, items[item]):
            return f'Not enough stock for item: {item}', 400

    return 'Successfully prepared stock', 200


@app.post('/commit_stock')
def commit_stock():
    items = request.json
    for item in items:
        if not remove_stock(item, items[item]):
            return 'An item did not have enough stock, commit aborted', 400

    return 'Successfully committed stock', 200


@app.post('/rollback_stock')
def rollback_stock():
    items = request.json
    for item in items:
        status = add_stock(item, items[item])
        print(status, file=sys.stderr)
        if status[1] != 200:
            return 'Something went wrong while rolling back stock', 400

    return 'Rolled back Stock', 200

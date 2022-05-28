import os
import atexit
from flask import Flask
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
    return s.dumps()


@app.post('/subtract/<item_id>/<amount>')
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
        return "Not enough stock", 400
    s.stock -= amount
    db.set(s.item_id, s.dumps())
    return s.dumps()

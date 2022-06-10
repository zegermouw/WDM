import os
import atexit
from bson import ObjectId
from flask import Flask
from pymongo import MongoClient, ReturnDocument
from stock import Stock


app = Flask("stock-service")


client = MongoClient(os.environ['GATEWAY_URL'], int(os.environ['PORT']))
db = client['local']

def close_db_connection():
    db.close()


atexit.register(close_db_connection)


def get_stock_by_id(item_id: str):
    stock = db.stock.find_one({"_id": ObjectId(str(item_id))})
    return Stock.loads(stock)


@app.post('/item/create/<price>')
def create_item(price: int):
    """
    Create stock item with given price
    :param price:
    :return: Stock
    """
    stock = Stock(price=int(price))
    db.stock.insert_one(stock.__dict__)
    stock.item_id = str(stock.__dict__.pop('_id'))
    return stock.dumps()


@app.get('/find/<item_id>')
def find_item(item_id: str):
    """
    Get item if it exists
    :param item_id:
    :return: Stock
    """
    stock = get_stock_by_id(item_id)
    return stock.dumps(), 200


@app.post('/add/<item_id>/<amount>')
def add_stock(item_id: str, amount: int):
    """
    Add amount to stock
    :param item_id:
    :param amount:
    :return: Stock
    """
    amount = int(amount)
    stock = db.stock.find_one_and_update(
        {'_id': ObjectId(str(item_id))},
        {'$inc': {'stock': amount}},
        return_document=ReturnDocument.AFTER
    )
    stock = Stock.loads(stock)
    return stock.dumps(), 200


@app.post('/subtract/<item_id>/<amount>')
def remove_stock(item_id: str, amount: int):
    """
    Remove stock from item with given id.
    :param item_id: The item to subtract amount from.
    :param amount: The amount to remove from the stock.
    :return: Stock item.
    """
    amount = int(amount)
    stock = get_stock_by_id(item_id)
    if stock.stock < amount:
        return "Not enough stock", 400
    stock = db.stock.find_one_and_update(
        {'_id': ObjectId(str(item_id))},
        {'$inc': {'stock': -amount}},
        return_document=ReturnDocument.AFTER
    )
    stock = Stock.loads(stock)
    return stock.dumps(), 200 

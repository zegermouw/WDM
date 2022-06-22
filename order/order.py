from flask import jsonify
import sys
from dataclasses import dataclass
from typing import List


@dataclass
class Order:
    """Class with order data structure"""

    items: List[str]
    user_id: str
    order_id: str

    def __init__(self, user_id: str, order_id: str = None,  items=None):
        if items is None:
            self.items = []
        else:
            self.items = items
        self.user_id = user_id
        self.order_id = order_id

    def dict(self):
        return {'_id': self.order_id, **self.__dict__}

    def dumps(self):
        return jsonify({'user_id': self.user_id, 'order_id': self.order_id, 'items': self.items})

    @staticmethod
    def loads(input_dict):
        return Order(input_dict['user_id'], input_dict['order_id'], input_dict['items'])

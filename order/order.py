import json
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
        return json.dumps(self.__dict__)

    @staticmethod
    def loads(input_dict):
        input_dict['order_id'] = str(input_dict.pop('_id'))
        return Order(**input_dict)

from dataclasses import dataclass
from flask import jsonify


@dataclass
class Stock:
    """Class for keeping track of an item in inventory."""
    price: float
    item_id: str = None
    stock: int = 0

    def dumps(self):
        return jsonify(self.__dict__)

    @staticmethod
    def loads(input_json: dict):
        if '_id' in input_json:
            input_json['item_id'] = str(input_json.pop('_id'))
        return Stock(**input_json)

    def load_id(self):
        if '_id' in self.__dict__:
            self.item_id = str(self.__dict__.pop('_id'))
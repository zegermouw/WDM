from dataclasses import dataclass
import uuid
import json


@dataclass
class Stock:
    """Class for keeping track of an item in inventory."""
    price: float
    item_id: str = uuid.uuid4().hex
    stock: int = 0

    def dumps(self):
        return json.dumps(self.__dict__)

    @staticmethod
    def loads(input_json: str):
        return Stock(**json.loads(input_json))

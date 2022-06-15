from dataclasses import dataclass
from datetime import datetime
import json

@dataclass
class StockUpdate:
    "Class for keeping track of stock updates"
    _id = None
    item_id: str
    amount: float
    local_time_stamp: datetime
    node: str
    
    def dumps(self):
        json.dumps(self.__dict__)
    
    @staticmethod
    def loads(input_json: dict):
        if '_id' in input_json:
            input_json['_id'] = str(input_json.pop('_id')) 
        return StockUpdate(**input_json)
    
    def load_id(self):
        if '_id' in self.__dict__:
            self._id = str(self.dict.pop('_id'))
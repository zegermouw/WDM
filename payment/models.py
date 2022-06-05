from dataclasses import dataclass
import json


@dataclass
class User:
    user_id: str = None
    credit: int = 0

    def dumps(self):
        return json.dumps(self.__dict__)

    @staticmethod
    def loads(input_dict):
        if '_id' in input_dict:
            input_dict['user_id'] = str(input_dict.pop('_id'))
        return User(**input_dict)

    def set_id(self):
        self.user_id = str(self.__dict__.pop('_id'))

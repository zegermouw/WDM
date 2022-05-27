from pydantic import BaseModel

class User(BaseModel):
    credit: int = 0
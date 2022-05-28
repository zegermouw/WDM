from typing import List
from pydantic import BaseModel
from typing import List, Optional

class Order(BaseModel):
    order_id: str
    credit_paid: int
    status: str

class User(BaseModel):
    credit: int = 0
    payments: Optional[List[Order]]

from pydantic import BaseModel
from typing import Literal, Optional

class Txn(BaseModel):
    id: str
    date: str
    amount: int
    direction: Literal["in", "out"]
    category: str
    description: str
    status: str = "scheduled"
    certainty: str = "committed"

class Day(BaseModel):
    date: str
    opening: float
    inflows: float
    outflows: float
    closing: float
    txn_ids: list[str]

class ForecastResult(BaseModel):
    days: list[Day]
    ending_cash: float
    min_balance: float
    min_date: str
    first_below_reserve: Optional[str]
    first_negative: Optional[str]
    shortfall_vs_reserve: float

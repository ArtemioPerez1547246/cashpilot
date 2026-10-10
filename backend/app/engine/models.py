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
    flexibility: str = "fixed"
    note: str = ""

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

class Driver(BaseModel):
    txn_id: str
    date: str
    amount: int
    category: str
    description: str
    flexibility: str

class PushedInflow(BaseModel):
    txn_id: str
    description: str
    amount: int
    planned_date: str
    actual_date: str
    impact_on_min_balance: float
    note: str

class DriversResult(BaseModel):
    min_date: str
    min_balance: float
    total_outflows_through_min_date: int
    outflows: list[Driver]
    pushed_inflows: list[PushedInflow]

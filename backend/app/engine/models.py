from pydantic import BaseModel
from typing import Literal, Optional

class Txn(BaseModel):
    id: str
    date: str
    amount: float
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
    amount: float
    category: str
    description: str
    flexibility: str

class PushedInflow(BaseModel):
    txn_id: str
    description: str
    amount: float
    planned_date: str
    actual_date: str
    impact_on_min_balance: float
    note: str

class DriversResult(BaseModel):
    min_date: str
    min_balance: float
    total_outflows_through_min_date: float
    outflows: list[Driver]
    pushed_inflows: list[PushedInflow]

class Effect(BaseModel):
    op: Literal["shift", "remove", "add"]
    txn: Optional[str] = None
    days: int = 0
    direction: Optional[Literal["in", "out"]] = None
    amount: float = 0
    lead_days: int = 0

class RepaymentSpec(BaseModel):
    lead_days: int
    amount: float

class Lever(BaseModel):
    id: str
    name: str
    effects: list[Effect]
    cost_usd: float
    cost_basis: str = ""
    constraint: str = ""
    deadline: Optional[str] = None
    exclusive_group: Optional[str] = None
    last_resort: bool = False
    action_type: str = ""
    repayments: list[RepaymentSpec] = []

class PlanRepayment(BaseModel):
    date: str
    amount: float
    lever: str

class Deferred(BaseModel):
    txn_id: str
    lever: str
    original_date: str
    new_date: str
    amount: float

class Plan(BaseModel):
    decision_date: str
    feasible: bool
    best_effort: bool
    levers: list[str]
    total_cost: float
    forecast: ForecastResult
    repayments: list[PlanRepayment]
    deferred_obligations: list[Deferred]
    deferred_total: float
    note: str = ""

class WaitPoint(BaseModel):
    decision_date: str
    feasible: bool
    total_cost: Optional[float]
    levers: list[str]
    min_balance: float

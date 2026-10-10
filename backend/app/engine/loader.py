import json
from pathlib import Path
from .models import Txn

DATA = Path(__file__).resolve().parents[2] / "data" / "cashpilot_dataset.json"

def load_dataset(path=DATA):
    raw = json.loads(Path(path).read_text())
    txns = [Txn(id=t["id"], date=t["date"], amount=t["amount"],
                direction="in" if t["type"] == "inflow" else "out",
                category=t["category"], description=t["description"],
                status=t["status"],
                flexibility=t.get("flexibility", "fixed"), note=t.get("note", "")) for t in raw["transactions"]]
    return raw, txns

import os
import tempfile

# Keep test runs from touching the real action queue, and never start the background timer.
os.environ.setdefault("CASHPILOT_STATE_DIR", tempfile.mkdtemp(prefix="cashpilot-test-"))
os.environ["DISABLE_MONITOR_TIMER"] = "1"
os.environ["MODEL_PROVIDER"] = "stub"

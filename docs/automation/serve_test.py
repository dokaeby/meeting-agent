"""Loopback-only E2E server. Never use test providers for a deployed service."""
import sys
import threading
import time
from pathlib import Path
root=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(root/"backend/src"))
from meeting_agent.config import Settings
from meeting_agent.main import create_app
from meeting_agent.jobs.runner import run_pending
import uvicorn
folder=root/"var"/("e2e-"+str(int(time.time())))
folder.mkdir(parents=True)
settings=Settings(environment="test",provider_mode="test",database_url=f"sqlite:///{folder}/app.db",
 storage_path=folder/"files",public_url="http://127.0.0.1:5174")
app=create_app(settings)
def worker():
    time.sleep(1)
    while True:
        run_pending(settings,app.state.factory)
        time.sleep(.5)
threading.Thread(target=worker,daemon=True).start()
uvicorn.run(app,host="127.0.0.1",port=8000,access_log=False,log_level="warning")


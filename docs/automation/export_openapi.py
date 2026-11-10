"""Export API contract without external service calls."""
import json
import sys
from pathlib import Path
root=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(root/"backend/src"))
from meeting_agent.config import Settings
from meeting_agent.main import create_app
app=create_app(Settings(environment="test",database_url="sqlite://",provider_mode="test"))
path=root/"docs/api/openapi.json"
path.write_text(json.dumps(app.openapi(),ensure_ascii=False,indent=2),encoding="utf-8")
print(path)


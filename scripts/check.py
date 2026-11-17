"""Validate distributable metadata and the pinned UI assets."""
from pathlib import Path
import ast
import hashlib
import json
import re

root = Path(__file__).resolve().parents[1]
component = root / "custom_components" / "weather_analysis"
manifest = json.loads((component / "manifest.json").read_text())
assert manifest["domain"] == "weather_analysis"
version = manifest["version"]
assert json.loads((root / "package.json").read_text())["version"] == version
for path in component.rglob("*.py"):
    ast.parse(path.read_text())
for path in root.rglob("*.json"):
    if "node_modules" not in path.parts:
        json.loads(path.read_text())
frontend = component / "frontend"
code = (frontend / "weather-analysis-card.js").read_text()
assert f"const VERSION = '{version}'" in code
ui = frontend / "family-ui" / "1.7.0"
for filename, sha in json.loads((ui / "manifest.json").read_text())["files"].items():
    assert hashlib.sha256((ui / filename).read_bytes()).hexdigest() == sha
assert "./family-ui/1.7.0/family-ui.js" in code
assert not re.search(r"https?://", code), "No remote runtime dependency"
assert (component / "translations" / "de.json").exists()
print(f"Metadata, Python syntax and UI Kit checks passed for {version}")

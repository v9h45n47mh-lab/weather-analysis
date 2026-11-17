"""Create the HACS integration ZIP and a complete manual-install ZIP."""
from pathlib import Path
import json
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "custom_components" / "weather_analysis"
VERSION = json.loads((COMPONENT / "manifest.json").read_text())["version"]
out = ROOT / "dist"
out.mkdir(exist_ok=True)
files = sorted(p for p in COMPONENT.rglob("*") if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc")
for name, base in (("weather-analysis.zip", COMPONENT), (f"weather-analysis-{VERSION}-manual.zip", ROOT)):
    with ZipFile(out / name, "w", ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, path.relative_to(base))
    print(out / name)

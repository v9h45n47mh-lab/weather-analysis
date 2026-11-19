"""Check the public provider response without sending any HA sensor data."""
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

path=Path(__file__).resolve().parents[1]/"custom_components/weather_analysis/forecast.py"
spec=importlib.util.spec_from_file_location("forecast_live",path)
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
params={"latitude":module.LOCATION["latitude"],"longitude":module.LOCATION["longitude"],
    "hourly":",".join(module.VARIABLES),"timezone":module.TIMEZONE,"timeformat":"unixtime","forecast_days":3,
    "temperature_unit":"celsius","wind_speed_unit":"kmh","precipitation_unit":"mm"}
with urlopen(module.API_URL+"?"+urlencode(params),timeout=20) as response:
    payload=json.load(response)
data=module.build_forecast(payload,datetime.now(timezone.utc))
assert len(data["days"][1]["slots"])==8
assert all(slot.get("hours") and all(0<h["end"]-h["start"]<=3600 for h in slot["hours"]) for day in data["days"] for slot in day["slots"])
assert all(slot["temperature"] is not None for day in data["days"] for slot in day["slots"])
print("Live Open-Meteo response verified for 67459: rest of today and tomorrow, 3-hour slots, Celsius, km/h and mm.")

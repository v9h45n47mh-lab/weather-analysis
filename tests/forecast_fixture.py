"""Synthetic hourly forecast, never used as live fallback data."""
from datetime import timedelta
from zoneinfo import ZoneInfo


def weather_payload(now):
    first = now.astimezone(ZoneInfo("Europe/Berlin")).replace(hour=0,minute=0,second=0,microsecond=0)
    stop = (first+timedelta(days=4)).timestamp()
    times = list(range(int(first.timestamp()),int(stop)+1,3600))
    return {"hourly_units":{"temperature_2m":"°C","wind_speed_10m":"km/h","precipitation":"mm",
        "apparent_temperature":"°C","relative_humidity_2m":"%","pressure_msl":"hPa","wind_direction_10m":"°","wind_gusts_10m":"km/h"},
        "hourly":{"time":times,"temperature_2m":[10.]*len(times),"wind_speed_10m":[12.]*len(times),
            "apparent_temperature":[8.]*len(times),"relative_humidity_2m":[80.]*len(times),"pressure_msl":[1013.]*len(times),
            "wind_direction_10m":[225.]*len(times),"wind_gusts_10m":[24.]*len(times),
            "weather_code":[3]*len(times),"is_day":[1]*len(times),"precipitation_probability":[40.]*len(times),"precipitation":[1.]*len(times)}}

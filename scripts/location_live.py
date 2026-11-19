"""Check public city-centre fixtures, never a user's actual GPS coordinates."""
import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen

for name, lat, lon, home in [("Böhl-Iggelheim",49.3806,8.3039,True),("Hamburg",53.55,10.0,False)]:
    params=urlencode({"lat":lat,"lon":lon,"limit":1,"lang":"de","radius":5})
    request=Request("https://photon.komoot.io/reverse?"+params,headers={"User-Agent":"WeatherAnalysis-ProviderCheck (+https://github.com/v9h45n47mh-lab/weather-analysis)"})
    with urlopen(request,timeout=15) as response:
        props=json.load(response)["features"][0]["properties"]
    resolved_home=props.get("countrycode","").lower()=="de" and str(props.get("postcode","")).strip()=="67459"
    assert resolved_home==home,(name,props)
    assert props.get("city") or props.get("name"),(name,props)
    print("Live place lookup passed:",name,props.get("postcode"))

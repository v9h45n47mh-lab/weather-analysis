"""Current DWD municipality warnings, spatially filtered by the official WFS."""
from __future__ import annotations
import asyncio
from collections import OrderedDict
from datetime import datetime, timezone
from .location import coordinates

API_URL = "https://maps.dwd.de/geoserver/dwd/ows"
SOURCE_URL = "https://www.dwd.de/warnungen"
LEVELS = {"Minor":1,"Moderate":2,"Severe":3,"Extreme":4}
LABELS = {0:"Warnung",1:"Wetterwarnung",2:"Markantes Wetter",3:"Unwetter",4:"Extremes Unwetter"}

def query_params(latitude,longitude):
    lat,lon=coordinates(latitude,longitude)
    # The DWD layer's native EPSG:4326 uses latitude/longitude axis order.
    # An explicit CRS84 point keeps longitude/latitude unambiguous in WFS 2.
    point=(f'<fes:Filter xmlns:fes="http://www.opengis.net/fes/2.0" xmlns:gml="http://www.opengis.net/gml/3.2">'
        f'<fes:Intersects><fes:ValueReference>THE_GEOM</fes:ValueReference>'
        f'<gml:Point srsName="urn:ogc:def:crs:OGC:1.3:CRS84"><gml:pos>{lon:.4f} {lat:.4f}</gml:pos></gml:Point>'
        f'</fes:Intersects></fes:Filter>')
    return {"service":"WFS","version":"2.0.0","request":"GetFeature","typeNames":"dwd:Warnungen_Gemeinden",
        "outputFormat":"application/json","srsName":"EPSG:4326","count":100,"FILTER":point}

class WarningsUnavailable(RuntimeError):
    pass

def instant(value):
    if not isinstance(value,str):raise ValueError("Missing warning validity")
    result=datetime.fromisoformat(value.replace("Z","+00:00"))
    if result.tzinfo is None:raise ValueError("Warning date has no timezone")
    return result.timestamp()

def parse_warnings(payload,now):
    if not isinstance(payload,dict) or payload.get("type")!="FeatureCollection" or not isinstance(payload.get("features"),list):
        raise ValueError("Invalid DWD response")
    features=payload["features"]
    matched=payload.get("numberMatched",len(features))
    if isinstance(matched,int) and matched>len(features):raise ValueError("Truncated DWD response")
    result={}
    for feature in features:
        if not isinstance(feature,dict) or not isinstance(feature.get("properties"),dict):raise ValueError("Invalid warning")
        p=feature["properties"]
        if p.get("STATUS")!="Actual" or p.get("MSGTYPE") not in ("Alert","Update") or p.get("SCOPE","Public")!="Public":continue
        if p.get("LANGUAGE","de-DE") not in ("de-DE","de"):continue
        start,end=instant(p.get("ONSET") or p.get("EFFECTIVE")),instant(p.get("EXPIRES"))
        if end<=start:raise ValueError("Invalid warning interval")
        if end<=now.timestamp():continue
        identifier=p.get("IDENTIFIER")
        if not isinstance(identifier,str) or not identifier:raise ValueError("Missing warning ID")
        headline=p.get("HEADLINE") or p.get("EVENT")
        if not isinstance(headline,str) or not headline:raise ValueError("Missing warning title")
        text=lambda name:p.get(name) if isinstance(p.get(name),str) else ""
        level=LEVELS.get(p.get("SEVERITY"),0)
        item={"id":identifier,"title":headline,"event":text("EVENT"),"level":level,"level_label":LABELS[level],
            "start":start,"end":end,"sent":instant(p["SENT"]) if p.get("SENT") else None,
            "area":text("NAME") or text("AREADESC"),"description":text("DESCRIPTION"),"instruction":text("INSTRUCTION"),
            "preliminary":"VORABINFORMATION" in headline.upper(),"upcoming":start>now.timestamp()}
        previous=result.get(identifier)
        if previous is None or (item["sent"] or 0)>=(previous["sent"] or 0):result[identifier]=item
    return sorted(result.values(),key=lambda item:(-item["level"],item["upcoming"],item["start"],item["id"]))

class WarningsClient:
    """Two-minute location caches; failed refreshes never become an all-clear."""
    def __init__(self,hass,session=None,clock=None):
        self.hass,self.session=hass,session
        self.clock=clock or (lambda:datetime.now(timezone.utc))
        self.cache=OrderedDict();self.lock=asyncio.Lock()

    async def get(self,latitude,longitude,country="de"):
        lat,lon=coordinates(latitude,longitude)
        now=self.clock()
        base={"source":"Deutscher Wetterdienst (DWD)","source_url":SOURCE_URL,"timezone":"Europe/Berlin"}
        if country!="de":return {**base,"status":"outside" if country else "unknown","alerts":[],"updated_at":None}
        key=(lat,lon)
        async with self.lock:
            entry=self.cache.get(key)
            if entry and entry.get("data") is not None and (now-entry["updated"]).total_seconds()<120:
                self.cache.move_to_end(key)
                return {**base,"status":"ok","alerts":parse_warnings(entry["data"],now),"updated_at":entry["updated"].timestamp()}
            if entry and entry.get("failed") and (now-entry["attempt"]).total_seconds()<60:
                raise WarningsUnavailable("DWD-Warnungen sind derzeit nicht abrufbar.")
            entry={"attempt":now,"failed":True};self.cache[key]=entry;self.cache.move_to_end(key)
            while len(self.cache)>64:self.cache.popitem(last=False)
            try:
                if self.session is None:
                    from homeassistant.helpers.aiohttp_client import async_get_clientsession
                    self.session=async_get_clientsession(self.hass)
                params=query_params(lat,lon)
                async with asyncio.timeout(20):
                    async with self.session.get(API_URL,params=params) as response:
                        response.raise_for_status();payload=await response.json()
                alerts=parse_warnings(payload,now)
            except Exception as error:
                raise WarningsUnavailable("DWD-Warnungen sind derzeit nicht abrufbar. Bitte direkt beim DWD prüfen.") from error
            entry.update(data=payload,updated=now,failed=False)
            return {**base,"status":"ok","alerts":alerts,"updated_at":now.timestamp()}

"""Shared public DWD fields: one forecast download, local rendering for every user."""
from __future__ import annotations
import asyncio
from collections import OrderedDict
from datetime import datetime,timezone
from functools import partial
import logging
from pathlib import Path
import re
from threading import RLock
from .radar_data import RadarUnavailable,archive_fields,first_member,metadata

DATA_URL='https://opendata.dwd.de/weather/radar/composite/rv/'
DISK_NAME=re.compile(r'^(\d+)_(\d+)\.h5$')
_LOGGER=logging.getLogger(__name__)

class RawRadarStore:
    def __init__(self,hass,session=None,clock=None):
        self.hass,self.session=hass,session;self.clock=clock or (lambda:datetime.now(timezone.utc).timestamp())
        self.fields=OrderedDict();self.bytes=0;self.latest=None;self.error=None;self.attempt=-1e20
        self.refresh=None;self.pending={};self.jobs=set();self.network=asyncio.Semaphore(4);self.restored=False;self.disk_lock=RLock()
        path=getattr(getattr(hass,'config',None),'path',None)
        self.directory=Path(path('.storage','weather_analysis.radar')) if callable(path) else None

    def spawn(self,coroutine,name):
        create=getattr(self.hass,'async_create_background_task',None)
        task=create(coroutine,name) if create else asyncio.create_task(coroutine,name=name)
        self.jobs.add(task)
        def done(result):
            self.jobs.discard(result)
            if not result.cancelled():result.exception()
        task.add_done_callback(done);return task

    async def execute(self,function,*args):
        job=getattr(self.hass,'async_add_executor_job',None)
        return await job(partial(function,*args)) if job else await asyncio.to_thread(function,*args)

    def ensure(self):
        if self.refresh and not self.refresh.done():return
        if self.clock()-self.attempt<(60 if self.error else 240):return
        self.attempt=self.clock();self.refresh=self.spawn(self._refresh(),'Weather Analysis raw radar refresh')

    async def _download(self,url,start=None,end=None):
        if not url.startswith(DATA_URL):raise ValueError('Untrusted radar source')
        if self.session is None:
            from homeassistant.helpers.aiohttp_client import async_get_clientsession
            self.session=async_get_clientsession(self.hass)
        headers={'Range':f'bytes={start}-{end}'} if start is not None else {}
        async with self.network,asyncio.timeout(35):
            async with self.session.get(url,headers=headers) as response:
                response.raise_for_status();raw=await response.read()
                if len(raw)>40_000_000:raise ValueError('Oversize radar response')
                if start is not None:
                    if response.status==206:
                        expected=f'bytes {start}-'
                        if not response.headers.get('Content-Range','').startswith(expected):raise ValueError('Invalid radar byte range')
                        return raw
                    if response.status==200:return raw[start:end+1]
                    raise ValueError('Invalid radar range response')
                return raw

    def _remember(self,fields):
        for key,raw in fields.items():
            if key in self.fields:self.bytes-=len(self.fields.pop(key))
            self.fields[key]=raw;self.bytes+=len(raw)
        while len(self.fields)>128 or self.bytes>64_000_000:
            _,raw=self.fields.popitem(last=False);self.bytes-=len(raw)

    def _load_disk(self):
        if self.directory is None or not self.directory.exists():return {}
        result={};now=self.clock()
        for path in sorted(self.directory.glob('*.h5'),reverse=True):
            match=DISK_NAME.fullmatch(path.name)
            if not match:continue
            reference,lead=map(int,match.groups())
            if not now-10800<=reference<=now or lead%5 or not 0<=lead<=120:continue
            if path.stat().st_size>8_000_000:continue
            result[(reference,lead)]=path.read_bytes()
            if len(result)>=128 or sum(map(len,result.values()))>64_000_000:break
        return result

    def _save_disk(self,fields):
        with self.disk_lock:self._write_disk(fields)

    def _write_disk(self,fields):
        if self.directory is None:return
        self.directory.mkdir(parents=True,exist_ok=True)
        for (reference,lead),raw in fields.items():
            path=self.directory/f'{reference}_{lead}.h5';temporary=path.with_suffix('.tmp')
            temporary.write_bytes(raw);temporary.replace(path)
        entries=[];now=self.clock()
        for path in self.directory.glob('*.h5'):
            match=DISK_NAME.fullmatch(path.name)
            if match:
                reference,lead=map(int,match.groups());entries.append((lead==0,reference,path,path.stat().st_size))
        used=0;count=0
        for _,reference,path,size in sorted(entries,key=lambda item:(item[0],item[1]),reverse=True):
            if reference<now-10800 or count>=160 or used+size>128_000_000:path.unlink(missing_ok=True)
            else:used+=size;count+=1

    async def _refresh(self):
        try:
            if not self.restored:
                self.restored=True
                try:fields=await self.execute(self._load_disk)
                except OSError:fields={}
                self._remember(fields)
                for key in sorted((k for k in fields if k[1]==0),reverse=True):
                    try:
                        meta=await self.execute(metadata,fields[key],key)
                        if 0<=self.clock()-meta['reference']<=2700:self.latest=meta;break
                    except Exception:continue
            raw=await self._download(DATA_URL+'composite_rv_LATEST.tar')
            fields=await self.execute(archive_fields,raw)
            reference=max(k[0] for k in fields);meta=await self.execute(metadata,fields[(reference,0)],(reference,0))
            if set(k[1] for k in fields)!=set(range(0,121,5)) or not 0<=self.clock()-reference<=2700:raise ValueError('Incomplete or stale DWD run')
            self._remember(fields);self.latest=meta;self.error=None
            try:await self.execute(self._save_disk,fields)
            except OSError:_LOGGER.debug('Radar disk cache is not writable')
            self.spawn(self._warm_history(),'Weather Analysis radar history warmup')
        except asyncio.CancelledError:raise
        except Exception as error:
            self.error='DWD-Radardaten sind derzeit nicht abrufbar.'
            _LOGGER.debug('Raw radar refresh failed: %s',error)

    async def _warm_history(self):
        if not self.latest:return
        now=int(self.clock()//300)*300;times=list(range(now-7200,self.latest['reference'],300));lock=asyncio.Semaphore(3)
        async def warm(reference):
            if (reference,0) in self.fields:return
            async with lock:
                try:await self.get_field(reference,0)
                except (RadarUnavailable,ValueError):pass
        await asyncio.gather(*(warm(reference) for reference in reversed(times)))

    async def get_field(self,reference,lead):
        key=(reference,lead)
        if key in self.fields:self.fields.move_to_end(key);return self.fields[key]
        if key not in self.pending:
            task=self.spawn(self._field(reference,lead),'Weather Analysis radar field');self.pending[key]=task
            def done(result):
                if self.pending.get(key) is result:self.pending.pop(key,None)
            task.add_done_callback(done)
        task=self.pending[key]
        try:return await asyncio.shield(task)
        finally:
            if task.done():self.pending.pop(key,None)

    async def _field(self,reference,lead):
        try:
            if self.directory:
                path=self.directory/f'{reference}_{lead}.h5'
                def read():
                    try:return path.read_bytes() if path.exists() and path.stat().st_size<=8_000_000 else None
                    except OSError:return None
                raw=await self.execute(read)
                if raw:
                    await self.execute(metadata,raw,(reference,lead));self._remember({(reference,lead):raw});return raw
            # A missing forecast is reloaded as a single shared run, never extrapolated locally.
            date=datetime.fromtimestamp(reference,timezone.utc).strftime('%Y%m%d_%H%M')
            url=DATA_URL+f'composite_rv_{date}.tar'
            if lead:
                fields=await self.execute(archive_fields,await self._download(url));self._remember(fields)
                await self.execute(self._save_disk,fields);return fields[(reference,lead)]
            prefix=await self._download(url,0,524287);key,size=first_member(prefix)
            if key!=(reference,0):raise ValueError('Wrong DWD analysis')
            if len(prefix)<512+size:prefix+=await self._download(url,len(prefix),512+size-1)
            raw=prefix[512:512+size]
            if len(raw)!=size:raise ValueError('Truncated radar analysis')
            await self.execute(metadata,raw,key);self._remember({key:raw});await self.execute(self._save_disk,{key:raw});return raw
        except asyncio.CancelledError:raise
        except Exception as error:raise RadarUnavailable('Dieses Radarbild ist derzeit nicht verfügbar.') from error

    async def close(self):
        jobs=list(self.jobs)
        for task in jobs:task.cancel()
        if jobs:await asyncio.gather(*jobs,return_exceptions=True)

"""Decode official DWD ODIM RV files and render small local precipitation PNGs."""
from __future__ import annotations
from datetime import datetime,timezone
import io
import json
import math
from pathlib import Path
import re
import struct
import tarfile
import zlib

MEMBER=re.compile(r"composite_rv_(\d{8})_(\d{4})_(\d{3})-hd5$")
PNG=b"\x89PNG\r\n\x1a\n"
MAX_FIELD=8_000_000
class RadarUnavailable(RuntimeError):
    pass
def text(value):
    return value.decode() if isinstance(value,bytes) else str(value)

def member_key(name):
    match=MEMBER.fullmatch(name)
    if not match:raise ValueError("Unexpected DWD member")
    date,clock,lead=match.groups();lead=int(lead)
    if lead>120 or lead%5:raise ValueError("Unexpected DWD lead time")
    reference=int(datetime.strptime(date+clock,"%Y%m%d%H%M").replace(tzinfo=timezone.utc).timestamp())
    return reference,lead

def archive_fields(raw):
    """Never extract files to disk; only accept bounded expected regular members."""
    if len(raw)>40_000_000:raise ValueError("Oversize DWD archive")
    fields={}
    with tarfile.open(fileobj=io.BytesIO(raw),mode="r:") as archive:
        for member in archive:
            if not member.isfile() or not 0<member.size<=MAX_FIELD:raise ValueError("Invalid DWD member")
            key=member_key(member.name)
            if key in fields:raise ValueError("Duplicate DWD member")
            fields[key]=archive.extractfile(member).read()
    if not fields or len(fields)>25 or len({key[0] for key in fields})!=1 or not any(key[1]==0 for key in fields):raise ValueError("Invalid DWD run")
    return fields

def first_member(raw):
    if len(raw)<512:raise ValueError("Truncated DWD archive header")
    header=tarfile.TarInfo.frombuf(raw[:512],"utf-8","strict")
    key=member_key(header.name)
    if not header.isfile() or key[1]!=0 or not 0<header.size<=MAX_FIELD:raise ValueError("Invalid DWD analysis")
    return key,header.size

def metadata(raw,key):
    import h5py
    from pyproj import Transformer
    with h5py.File(io.BytesIO(raw),"r") as source:
        where=dict(source['where'].attrs);what=dict(source['what'].attrs);product=dict(source['dataset1/what'].attrs)
        attrs=dict(source['dataset1/data1/what'].attrs);data=source['dataset1/data1/data']
        reference=int(datetime.strptime(text(what['date'])+text(what['time']),"%Y%m%d%H%M%S").replace(tzinfo=timezone.utc).timestamp())
        start=int(datetime.strptime(text(product['startdate'])+text(product['starttime']),"%Y%m%d%H%M%S").replace(tzinfo=timezone.utc).timestamp())
        end=int(datetime.strptime(text(product['enddate'])+text(product['endtime']),"%Y%m%d%H%M%S").replace(tzinfo=timezone.utc).timestamp())
        width,height=int(where['xsize']),int(where['ysize'])
        if reference!=key[0] or end!=reference+key[1]*60 or end-start!=300:raise ValueError("Unexpected DWD validity")
        if text(attrs['quantity'])!='ACRR' or data.shape!=(height,width) or not 1<=width<=2000 or not 1<=height<=2000:raise ValueError("Unexpected DWD grid")
        gain,offset=float(attrs['gain']),float(attrs['offset'])
        xs,ys=float(where['xscale']),float(where['yscale'])
        projection=text(where['projdef'])
        if not all(math.isfinite(v) for v in (gain,offset,xs,ys)) or gain<=0 or not 100<=xs<=5000 or not 100<=ys<=5000 or not projection.startswith('+proj=stere '):raise ValueError("Invalid DWD scaling")
        origin_x,origin_y=Transformer.from_crs('EPSG:4326',projection,always_xy=True).transform(float(where['UL_lon']),float(where['UL_lat']))
        return {'origin_x':origin_x,'origin_y':origin_y,'reference':reference,'width':width,'height':height,'xscale':xs,'yscale':ys,'projection':projection,
            'gain':gain,'offset':offset,'nodata':int(attrs['nodata']),'undetect':int(attrs['undetect']),
            'west':min(float(where['LL_lon']),float(where['UL_lon'])),'south':min(float(where['LL_lat']),float(where['LR_lat'])),
            'east':max(float(where['UR_lon']),float(where['LR_lon'])),'north':max(float(where['UL_lat']),float(where['UR_lat']))}

def sampling_grid(meta,bbox,size=256):
    import numpy as np
    from pyproj import Transformer
    west,south,east,north=(float(v) for v in bbox.split(','))
    x=west+(np.arange(size)+.5)*(east-west)/size
    y=north-(np.arange(size)+.5)*(north-south)/size
    xx,yy=np.meshgrid(x,y)
    transformer=Transformer.from_crs('EPSG:3857',meta['projection'],always_xy=True)
    rx,ry=transformer.transform(xx,yy)
    cols=np.floor((rx-meta['origin_x'])/meta['xscale']).astype('int32')
    rows=np.floor((meta['origin_y']-ry)/meta['yscale']).astype('int32')
    valid=(cols>=0)&(rows>=0)&(cols<meta['width'])&(rows<meta['height'])
    return rows.clip(0,meta['height']-1),cols.clip(0,meta['width']-1),valid

def png(array):
    """Exact RGBA encoder; no GUI/image-rendering library needed in Home Assistant."""
    height,width,channels=array.shape
    if channels!=4:raise ValueError("Expected RGBA")
    def chunk(kind,data):return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data)&0xffffffff)
    scanlines=b''.join(b'\0'+row.tobytes() for row in array)
    return PNG+chunk(b'IHDR',struct.pack('>IIBBBBB',width,height,8,6,0,0,0))+chunk(b'IDAT',zlib.compress(scanlines,6))+chunk(b'IEND',b'')

def render(raw,meta,grid,scale):
    import h5py
    import numpy as np
    rows,cols,valid=grid
    with h5py.File(io.BytesIO(raw),'r') as source:values=source['dataset1/data1/data'][()][rows,cols]
    known=valid&(values!=meta['nodata'])
    if not known.any():raise ValueError("No radar coverage in this view")
    rate=np.maximum(0,(values.astype('float64')*meta['gain']+meta['offset'])*12)
    wet=known&(values!=meta['undetect'])&(rate>0)
    indices=(np.searchsorted([item['min'] for item in scale],rate,side='right')-1).clip(0,len(scale)-1)
    colours=np.asarray([[int(item['color'][i:i+2],16) for i in (1,3,5)]+[255] for item in scale],dtype='uint8')
    image=np.zeros((*values.shape,4),dtype='uint8');image[wet]=colours[indices[wet]]
    yy,xx=np.indices(values.shape);missing=~known&((xx+yy)%12<2)
    image[missing]=[120,130,140,65]
    return png(image)

def project_map(bbox,data):
    west,south,east,north=(float(v) for v in bbox.split(','))
    def point(lon,lat):
        x=6378137*math.radians(lon);y=6378137*math.log(math.tan(math.pi/4+math.radians(lat)/2))
        return [round((x-west)/(east-west)*512,1),round((north-y)/(north-south)*512,1)]
    lines=[]
    for line in data['lines']:
        points=[point(lon,lat) for lon,lat in line['points']]
        # Retain crossing segments but omit geometry wholly outside the local view.
        if max(p[0] for p in points)<-20 or min(p[0] for p in points)>532 or max(p[1] for p in points)<-20 or min(p[1] for p in points)>532:continue
        lines.append({'kind':line['kind'],'points':points})
    places=[]
    for place in sorted(data['places'],key=lambda p:-p['population']):
        x,y=point(place['lon'],place['lat'])
        if not (24<x<470 and 24<y<488) or abs(x-256)+abs(y-256)<32:continue
        if any(math.hypot(x-p['x'],y-p['y'])<95 for p in places):continue
        places.append({'x':x,'y':y,'name':place['name']})
        if len(places)==4:break
    return {'lines':lines,'places':places}

"""Strict decoder for DWD native-grid instantaneous GRIB2/CCSDS fields.

Only WMO templates 3.101, 4.0 and 5.42 are accepted. CCSDS uses the
libaec already supplied with h5py/HDF5, including on Home Assistant OS.
"""
import ctypes as ct
import ctypes.util
from datetime import datetime,timezone
from functools import lru_cache
import math,struct
from pathlib import Path

class AecStream(ct.Structure):
    _fields_=[('next_in',ct.c_void_p),('avail_in',ct.c_size_t),('total_in',ct.c_size_t),('next_out',ct.c_void_p),('avail_out',ct.c_size_t),('total_out',ct.c_size_t),('bits_per_sample',ct.c_uint),('block_size',ct.c_uint),('rsi',ct.c_uint),('flags',ct.c_uint),('state',ct.c_void_p)]

@lru_cache(maxsize=1)
def library():
    import h5py
    directory=Path(h5py.__file__).resolve().parent.parent/'h5py.libs'
    candidates=[str(path) for path in directory.glob('libaec*.so*')]
    system=ctypes.util.find_library('aec')
    if system:candidates.append(system)
    for path in candidates:
        try:
            lib=ct.CDLL(path);lib.aec_buffer_decode.argtypes=[ct.POINTER(AecStream)];lib.aec_buffer_decode.restype=ct.c_int;return lib
        except (OSError,AttributeError):continue
    raise ValueError('The HDF5 CCSDS decoder is unavailable')

def unpack_ccsds(raw,count,bits,flags,block,rsi):
    import numpy as np
    if not 1<=bits<=32 or flags!=14 or block not in (8,16,32,64) or not 1<=rsi<=4096:raise ValueError('Unsupported CCSDS settings')
    width=1 if bits<=8 else 2 if bits<=16 else 3 if bits<=24 else 4
    source=ct.create_string_buffer(raw);target=ct.create_string_buffer(count*width)
    stream=AecStream(ct.cast(source,ct.c_void_p),len(raw),0,ct.cast(target,ct.c_void_p),count*width,0,bits,block,rsi,flags,None)
    if library().aec_buffer_decode(ct.byref(stream))!=0 or stream.total_out!=count*width:raise ValueError('Invalid CCSDS payload')
    if width==3:
        values=np.frombuffer(target.raw,dtype='uint8').reshape(-1,3).astype('uint32');return (values[:,0]<<16)|(values[:,1]<<8)|values[:,2]
    return np.frombuffer(target.raw,dtype={1:'u1',2:'>u2',4:'>u4'}[width])

def signed(raw):
    value=int.from_bytes(raw,'big');sign=1<<(len(raw)*8-1)
    return -(value&(sign-1)) if value&sign else value

def decode(raw,parameter,reference=None,valid=None):
    import numpy as np
    if not 64<=len(raw)<=8_000_000 or raw[:4]!=b'GRIB' or raw[6]!=0 or raw[7]!=2 or raw[-4:]!=b'7777' or int.from_bytes(raw[8:16],'big')!=len(raw):raise ValueError('Invalid GRIB2 message')
    sections={};offset=16
    while offset<len(raw)-4:
        length=int.from_bytes(raw[offset:offset+4],'big');number=raw[offset+4]
        if length<5 or offset+length>len(raw)-4 or number in sections:raise ValueError('Invalid GRIB2 section')
        sections[number]=raw[offset:offset+length];offset+=length
    if offset!=len(raw)-4 or not {1,3,4,5,6,7}<=sections.keys():raise ValueError('Incomplete GRIB2 field')
    identity,grid,product,packing,bitmap,data=(sections[number] for number in (1,3,4,5,6,7))
    if len(identity)!=21 or int.from_bytes(identity[5:7],'big')!=78:raise ValueError('Not a DWD field')
    if len(grid)!=35 or int.from_bytes(grid[12:14],'big')!=101 or grid[14]!=6:raise ValueError('Unsupported native grid')
    count=int.from_bytes(grid[6:10],'big');uuid=grid[19:35].hex()
    if not 1<=count<=2_000_000:raise ValueError('Oversize model grid')
    if len(product)!=34 or product[5:9]!=b'\0\0\0\0' or product[22]!=1:raise ValueError('Not an instantaneous surface field')
    expected={'TOT_PR':(1,52),'CLAT':(191,1),'CLON':(191,2)}[parameter]
    if (product[9],product[10])!=expected:raise ValueError('Unexpected model parameter or units')
    date=datetime(int.from_bytes(identity[12:14],'big'),*identity[14:19],tzinfo=timezone.utc)
    unit={0:60,1:3600,13:1}.get(product[17]);lead=int.from_bytes(product[18:22],'big')
    if unit is None or lead*unit>97200:raise ValueError('Unsupported forecast time')
    stamp=int(date.timestamp());meta={'reference':stamp,'valid':stamp+lead*unit,'uuid':uuid,'count':count}
    if reference is not None and (stamp!=reference or meta['valid']!=valid):raise ValueError('Wrong model run or validity')
    if len(packing)!=25 or int.from_bytes(packing[9:11],'big')!=42 or packing[20]!=0:raise ValueError('Unsupported GRIB packing')
    size=int.from_bytes(packing[5:9],'big');base=struct.unpack('>f',packing[11:15])[0];binary=signed(packing[15:17]);decimal=signed(packing[17:19]);bits=packing[19]
    if not 0<=size<=count or not math.isfinite(base) or abs(binary)>100 or abs(decimal)>100:raise ValueError('Invalid GRIB scaling')
    if len(bitmap)<6:raise ValueError('Truncated GRIB bitmap')
    if bitmap[5]==255 and len(bitmap)==6:known=np.ones(count,dtype=bool)
    elif bitmap[5]==0 and len(bitmap)==6+(count+7)//8:known=np.unpackbits(np.frombuffer(bitmap[6:],dtype='uint8'))[:count].astype(bool)
    else:raise ValueError('Unsupported GRIB bitmap')
    if int(known.sum())!=size or not size:raise ValueError('GRIB bitmap and packed values disagree')
    integers=unpack_ccsds(data[5:],size,bits,packing[21],packing[22],int.from_bytes(packing[23:25],'big')) if bits else np.zeros(size,dtype='uint8')
    values=np.full(count,np.nan,dtype='float32');values[known]=(base+integers.astype('float64')*2.**binary)*10.**(-decimal)
    if parameter=='TOT_PR':values*=3600 # WMO total precipitation rate: kg/m²/s to mm/h.
    return meta,values

from __future__ import annotations
import math

def _hash2(x,z,seed):
    n=(x*374761393+z*668265263+seed*1442695041)&0xFFFFFFFF; n=(n^(n>>13))*1274126177&0xFFFFFFFF; n^=n>>16; return n/0xFFFFFFFF

def smooth(t): return t*t*(3-2*t)
def value_noise(x,z,seed):
    x0,z0=math.floor(x),math.floor(z); tx,tz=x-x0,z-z0; a=_hash2(x0,z0,seed); b=_hash2(x0+1,z0,seed); c=_hash2(x0,z0+1,seed); d=_hash2(x0+1,z0+1,seed); sx,sz=smooth(tx),smooth(tz); ab=a+(b-a)*sx; cd=c+(d-c)*sx; return ab+(cd-ab)*sz
def fbm(x,z,seed,octaves=5):
    total=amp=0; freq=1; norm=0
    for i in range(octaves): total+=value_noise(x*freq,z*freq,seed+i*1013)*amp; norm+=amp; amp*=.5; freq*=2
    return total/norm
def ridge(x,z,seed): return 1-abs(fbm(x,z,seed,5)*2-1)

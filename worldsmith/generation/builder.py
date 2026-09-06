from __future__ import annotations
import math
from dataclasses import dataclass
from worldsmith.generation.noise import fbm,ridge
try:
    from amulet.api.block import Block
except ImportError: Block=None

@dataclass
class BuildResult:
    blocks_changed:int=0
    roads_changed:int=0
    systems_changed:int=0

class WorldBuilder:
    def __init__(self,level,dimension='minecraft:overworld',seed=1337):
        if Block is None: raise RuntimeError('amulet-core is required for building')
        self.level=level; self.dimension=dimension; self.seed=seed; self._blocks={}
        wrapper=getattr(level,'level_wrapper',None); self.version=('java',getattr(wrapper,'max_world_version',(1,20,4)))
    def block(self,name):
        if name not in self._blocks:
            ns,base=name.split(':',1); self._blocks[name]=Block(ns,base)
        return self._blocks[name]
    def put(self,x,y,z,name): self.level.set_version_block(x,y,z,self.dimension,self.version,self.block(name)); return True
    def mountain_range(self,cx,cz,radius,base_y,height,seed=1337):
        changed=0
        for x in range(cx-radius,cx+radius+1):
            for z in range(cz-radius,cz+radius+1):
                dist=math.hypot(x-cx,z-cz)/max(1,radius)
                if dist>1: continue
                macro=fbm(x/150,z/150,seed); ridges=ridge(x/55,z/55,seed+17); valleys=fbm(x/35,z/35,seed+31,4); fall=max(0,1-dist**1.7)
                h=max(base_y+2,base_y+int(height*(.18*macro+.55*ridges+.27*valleys)*fall))
                for y in range(base_y,h+1):
                    block='minecraft:snow_block' if y==h and h>base_y+height*.72 else ('minecraft:grass_block' if y==h else ('minecraft:dirt' if y>h-4 else 'minecraft:stone'))
                    self.put(x,y,z,block); changed+=1
        return changed
    def road(self,x1,z1,x2,z2,y):
        changed=0; steps=max(abs(x2-x1),abs(z2-z1),1)
        for i in range(steps+1):
            t=i/steps; x=round(x1+(x2-x1)*t); z=round(z1+(z2-z1)*t)
            for ox in (-1,0,1):
                for oz in (-1,0,1): self.put(x+ox,y,z+oz,'minecraft:stone_bricks'); changed+=1
        return changed
    def cube_shell(self,x,y,z,w,d,h,wall):
        c=0
        for xx in range(x-w//2,x+(w+1)//2):
            for zz in range(z-d//2,z+(d+1)//2):
                if xx in {x-w//2,x+(w-1)//2} or zz in {z-d//2,z+(d-1)//2}:
                    for yy in range(y,y+h): self.put(xx,yy,zz,wall); c+=1
                self.put(xx,y+h,zz,'minecraft:spruce_planks'); c+=1
        return c
    def tower(self,x,y,z,r,h):
        c=0
        for yy in range(y,y+h):
            for dx in range(-r,r+1):
                for dz in range(-r,r+1):
                    if dx*dx+dz*dz<=r*r and dx*dx+dz*dz>=max(1,(r-1)**2): self.put(x+dx,yy,z+dz,'minecraft:stone_bricks'); c+=1
        return c
    def interior(self,x,y,z,w,d):
        c=0
        for xx in range(x-w//2+2,x+w//2-1,3):
            for zz in range(z-d//2+2,z+d//2-1,3): self.put(xx,y+1,zz,'minecraft:oak_planks'); self.put(xx,y+2,zz,'minecraft:lantern'); c+=2
        return c
    def redstone_gate(self,x,y,z):
        for dx,dy,b in [(0,1,'minecraft:lever'),(1,1,'minecraft:redstone_wire'),(2,1,'minecraft:sticky_piston'),(2,2,'minecraft:sticky_piston'),(3,0,'minecraft:iron_block'),(3,1,'minecraft:iron_block')]: self.put(x+dx,y+dy,z,b)
        return 6
    def build(self,plan):
        r=BuildResult(); cx,cy,cz=plan.get('center',[0,100,0]); t=plan.get('terrain',{})
        if t.get('enabled',True): r.blocks_changed+=self.mountain_range(cx,cz,min(int(t.get('radius',96)),192),cy,min(int(t.get('mountain_height',80)),120),self.seed)
        for road in plan.get('roads',[]): r.roads_changed+=self.road(int(road['x1']),int(road['z1']),int(road['x2']),int(road['z2']),cy+1)
        for b in plan.get('builds',[]):
            x,y,z=int(b['x']),int(b['y']),int(b['z']); w,d,h=[int(b.get(k,10)) for k in ('width','depth','height')]; wall='minecraft:stone_bricks' if 'castle' in b.get('type','').lower() else 'minecraft:spruce_planks'; r.blocks_changed+=self.cube_shell(x,y,z,w,d,h,wall)
            if b.get('interior',True): r.blocks_changed+=self.interior(x,y,z,w,d)
            if 'castle' in b.get('type','').lower():
                rr=max(2,w//5)
                for tx,tz in ((x-w//2,z-d//2),(x+w//2-1,z-d//2),(x-w//2,z+d//2-1),(x+w//2-1,z+d//2-1)): r.blocks_changed+=self.tower(tx,y,tz,rr,h+8)
            if b.get('redstone'): r.systems_changed+=self.redstone_gate(x-w//4,y+1,z)
        return r

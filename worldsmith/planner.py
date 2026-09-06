from __future__ import annotations
import json
from dataclasses import dataclass
from worldsmith.ai.orchestrator import Ensemble, EnsembleResult

@dataclass
class PlanResult:
    plan: dict
    ensemble: EnsembleResult
    def pretty(self): return json.dumps(self.plan,indent=2)

class Planner:
    def __init__(self,ensemble:Ensemble): self.ensemble=ensemble
    def make_plan(self,request,context,center=(0,100,0)):
        result=self.ensemble.plan(request,context,center)
        return PlanResult(self._sanitize(result.plan,center),result)
    def _sanitize(self,plan,center):
        plan.setdefault('center',list(center)); plan.setdefault('terrain',{'enabled':True,'radius':96,'mountain_height':80,'roughness':1.0})
        plan['terrain']['radius']=max(16,min(int(plan['terrain'].get('radius',96)),192)); plan['terrain']['mountain_height']=max(8,min(int(plan['terrain'].get('mountain_height',80)),120))
        plan['builds']=list(plan.get('builds',[]))[:20]
        for b in plan['builds']:
            for k,default in [('x',center[0]),('y',center[1]),('z',center[2]),('width',10),('depth',10),('height',10)]:
                b[k]=int(b.get(k,default))
                if k in {'width','depth','height'}: b[k]=max(3,min(b[k],80))
        return plan

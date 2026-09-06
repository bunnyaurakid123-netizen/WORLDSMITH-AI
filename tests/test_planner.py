from worldsmith.ai.orchestrator import built_in_plan
from worldsmith.planner import Planner

def test_fallback_plan():
    p=built_in_plan('mountains',(0,100,0),96); assert p['terrain']['radius']==96; assert len(p['builds'])<=12

def test_sanitize_caps_builds():
    class Fake:
        def plan(self,*a,**k):
            from worldsmith.ai.orchestrator import EnsembleResult
            return EnsembleResult({'center':[0,100,0],'builds':[{'x':0,'y':100,'z':0,'width':999,'depth':999,'height':999}]*25},[],[])
    p=Planner(Fake()).make_plan('x','y').plan; assert len(p['builds'])==20; assert p['builds'][0]['width']==80

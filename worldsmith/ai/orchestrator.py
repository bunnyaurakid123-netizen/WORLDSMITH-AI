from __future__ import annotations
import concurrent.futures, json, re
from dataclasses import dataclass
from .providers import AIResponse, call_gemini, call_ollama, call_openai
from worldsmith.config import Settings

SYSTEM_PROMPT='''You are WorldSmith, an expert Minecraft Java world architect. Return ONLY valid JSON. Design practical edits for an existing save. Preserve player builds. Schema: {"summary":string,"style":string,"center":[int,int,int],"terrain":{"enabled":bool,"radius":int,"mountain_height":int,"roughness":number},"builds":[{"type":string,"x":int,"y":int,"z":int,"width":int,"depth":int,"height":int,"style":string,"interior":bool,"redstone":bool}],"roads":[{"x1":int,"z1":int,"x2":int,"z2":int}],"notes":[string]} Keep sizes reasonable and use at most 12 major buildings.'''

@dataclass
class EnsembleResult:
    plan:dict
    responses:list[AIResponse]
    errors:list[str]

def extract_json(text:str)->dict:
    text=text.strip(); m=re.search(r'```(?:json)?\s*(\{.*\})\s*```',text,re.S); candidate=m.group(1) if m else text
    a,b=candidate.find('{'),candidate.rfind('}'); candidate=candidate[a:b+1] if a>=0 and b>a else candidate
    return json.loads(candidate)

def built_in_plan(prompt,center=(0,100,0),radius=96):
    x,y,z=center
    return {'summary':prompt,'style':'cinematic natural fantasy','center':[x,y,z],'terrain':{'enabled':True,'radius':radius,'mountain_height':80,'roughness':1.0},'builds':[{'type':'castle','x':x,'y':y,'z':z,'width':31,'depth':31,'height':28,'style':'stone spruce medieval','interior':True,'redstone':True},{'type':'village','x':x+46,'y':y,'z':z+30,'width':21,'depth':21,'height':10,'style':'spruce medieval','interior':True,'redstone':False}],'roads':[{'x1':x,'z1':z,'x2':x+46,'z2':z+30}],'notes':['Offline fallback plan']}

class Ensemble:
    def __init__(self,settings): self.settings=settings
    def plan(self,user_prompt,context='',center=(0,100,0)):
        prompt=SYSTEM_PROMPT+'\nWORLD CONTEXT:\n'+context[:8000]+'\nUSER REQUEST:\n'+user_prompt
        jobs={}
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
            if self.settings.openai_key: jobs[pool.submit(call_openai,self.settings.openai_key,self.settings.openai_model,prompt)]='openai'
            if self.settings.gemini_key: jobs[pool.submit(call_gemini,self.settings.gemini_key,self.settings.gemini_model,prompt)]='gemini'
            jobs[pool.submit(call_ollama,self.settings.ollama_url,self.settings.ollama_model,prompt)]='ollama'
            responses=[]; errors=[]
            for f in concurrent.futures.as_completed(jobs):
                try: responses.append(f.result())
                except Exception as exc: errors.append(f'{jobs[f]}: {exc}')
        plans=[]
        for r in responses:
            try: p=extract_json(r.text); p['_provider']=r.provider; plans.append(p)
            except Exception as exc: errors.append(f'{r.provider}: invalid JSON ({exc})')
        if not plans: return EnsembleResult(built_in_plan(user_prompt,center,self.settings.default_radius),responses,errors)
        # Reconcile candidates with an available judge provider.
        judge_prompt=SYSTEM_PROMPT+'\nYou are the WorldSmith judge. Reconcile ALL candidate plans below into one valid plan.\nCANDIDATES:\n'+json.dumps(plans,indent=2)[:18000]
        chosen=None; judge_name=None
        judges=[]
        if self.settings.openai_key: judges.append(('openai',lambda:call_openai(self.settings.openai_key,self.settings.openai_model,judge_prompt)))
        if self.settings.gemini_key: judges.append(('gemini',lambda:call_gemini(self.settings.gemini_key,self.settings.gemini_model,judge_prompt)))
        judges.append(('ollama',lambda:call_ollama(self.settings.ollama_url,self.settings.ollama_model,judge_prompt)))
        for name,fn in judges:
            try:
                rr=fn(); chosen=extract_json(rr.text); judge_name=name; responses.append(AIResponse(name+'-judge',rr.text)); break
            except Exception as exc: errors.append(f'{name}-judge: {exc}')
        merged=built_in_plan(user_prompt,center,self.settings.default_radius)
        for k,v in (chosen or plans[0]).items():
            if not k.startswith('_'): merged[k]=v
        merged['_ensemble']=[p.get('_provider','unknown') for p in plans]
        if judge_name: merged['_judge']=judge_name
        return EnsembleResult(merged,responses,errors)

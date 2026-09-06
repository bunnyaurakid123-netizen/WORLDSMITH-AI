from __future__ import annotations
import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

@dataclass
class AIResponse:
    provider: str
    text: str

class ProviderError(RuntimeError): pass

def _post_json(url:str,payload:dict[str,Any],headers:dict[str,str]|None=None,timeout:int=90)->dict[str,Any]:
    req=urllib.request.Request(url,data=json.dumps(payload).encode(),headers={"Content-Type":"application/json",**(headers or {})},method="POST")
    try:
        with urllib.request.urlopen(req,timeout=timeout) as r: return json.loads(r.read().decode())
    except urllib.error.HTTPError as exc: raise ProviderError(f"HTTP {exc.code}: {exc.read().decode(errors='replace')[:1000]}") from exc
    except (urllib.error.URLError,TimeoutError,json.JSONDecodeError) as exc: raise ProviderError(str(exc)) from exc

def call_openai(api_key:str,model:str,prompt:str)->AIResponse:
    if not api_key: raise ProviderError("OpenAI key not configured")
    data=_post_json("https://api.openai.com/v1/responses",{"model":model,"input":prompt},{"Authorization":f"Bearer {api_key}"})
    parts=[]
    for item in data.get("output",[]):
        for content in item.get("content",[]):
            if content.get("type") in {"output_text","text"} and content.get("text"): parts.append(content["text"])
    text="\n".join(parts).strip() or str(data.get("output_text",""))
    if not text: raise ProviderError("OpenAI returned no text")
    return AIResponse("openai",text)

def call_gemini(api_key:str,model:str,prompt:str)->AIResponse:
    if not api_key: raise ProviderError("Gemini key not configured")
    data=_post_json(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",{"contents":[{"role":"user","parts":[{"text":prompt}]}]},{"x-goog-api-key":api_key})
    try: text=data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError,IndexError,TypeError) as exc: raise ProviderError("Gemini returned no text") from exc
    return AIResponse("gemini",text)

def call_ollama(base_url:str,model:str,prompt:str)->AIResponse:
    data=_post_json(base_url.rstrip("/")+"/api/chat",{"model":model,"messages":[{"role":"user","content":prompt}],"stream":False})
    text=data.get("message",{}).get("content","")
    if not text: raise ProviderError("Ollama returned no text")
    return AIResponse("ollama",text)

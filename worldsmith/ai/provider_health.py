from __future__ import annotations

import time
from dataclasses import dataclass, field

@dataclass
class ProviderHealth:
    provider: str
    ok: bool = False
    failures: int = 0
    last_error: str = ""
    latency_ms: float = 0.0
    last_success: float = 0.0
    calls: int = 0

    def record_success(self, latency_ms: float):
        self.ok=True; self.failures=0; self.latency_ms=latency_ms; self.last_success=time.time(); self.calls+=1
    def record_failure(self, error: str):
        self.ok=False; self.failures+=1; self.last_error=error; self.calls+=1

class ProviderHealthBook:
    def __init__(self): self.items: dict[str,ProviderHealth]={}
    def start(self, provider: str) -> float: return time.perf_counter()
    def success(self, provider: str, started: float):
        item=self.items.setdefault(provider,ProviderHealth(provider)); item.record_success((time.perf_counter()-started)*1000)
    def failure(self, provider: str, error: Exception):
        item=self.items.setdefault(provider,ProviderHealth(provider)); item.record_failure(str(error))
    def snapshot(self): return {k: vars(v).copy() for k,v in self.items.items()}

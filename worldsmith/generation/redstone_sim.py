from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable


@dataclass(frozen=True)
class Component:
    name: str
    kind: str
    inputs: tuple[str, ...] = ()
    delay: int = 0


@dataclass
class SimulationResult:
    valid: bool
    outputs: dict[str, bool] = field(default_factory=dict)
    ticks: int = 0
    unstable: bool = False
    message: str = ""


class RedstoneSimulator:
    """Small deterministic logic simulator for generated redstone contracts.

    This validates the logical graph before physical blocks are emitted. It is not a
    full Minecraft tick/update simulator, but it catches missing inputs, cycles and
    unreachable outputs for WorldSmith's generated circuits.
    """

    def __init__(self, components: Iterable[Component]):
        self.components = {c.name: c for c in components}

    def validate(self, outputs: Iterable[str]) -> SimulationResult:
        output_names = tuple(outputs)
        missing = [name for name in output_names if name not in self.components]
        if missing:
            return SimulationResult(False, message=f"Missing output components: {', '.join(missing)}")

        visiting: set[str] = set()
        visited: set[str] = set()

        def dfs(name: str) -> bool:
            if name in visiting:
                return False
            if name in visited:
                return True
            comp = self.components.get(name)
            if comp is None:
                return False
            visiting.add(name)
            for dependency in comp.inputs:
                if dependency not in self.components or not dfs(dependency):
                    return False
            visiting.remove(name)
            visited.add(name)
            return True

        for name in self.components:
            if not dfs(name):
                return SimulationResult(False, message=f"Invalid dependency graph near {name}")
        return SimulationResult(True, message="Circuit dependency graph is acyclic and complete")

    def run(self, inputs: dict[str, bool], outputs: Iterable[str], max_ticks: int = 32) -> SimulationResult:
        validated = self.validate(outputs)
        if not validated.valid:
            return validated

        values = {name: bool(value) for name, value in inputs.items()}
        ticks = 0
        ordered = list(self.components)
        for ticks in range(1, max(1, int(max_ticks)) + 1):
            changed = False
            for name in ordered:
                comp = self.components[name]
                if comp.kind == "input":
                    continue
                dependencies = [values.get(dep, False) for dep in comp.inputs]
                if comp.kind in {"wire", "repeater"}:
                    value = bool(dependencies and dependencies[0])
                elif comp.kind == "and":
                    value = bool(dependencies) and all(dependencies)
                elif comp.kind == "or":
                    value = any(dependencies)
                elif comp.kind == "not":
                    value = not dependencies[0] if dependencies else False
                elif comp.kind == "xor":
                    value = sum(bool(v) for v in dependencies) % 2 == 1
                elif comp.kind == "latch":
                    current = values.get(name, False)
                    value = dependencies[0] if dependencies else current
                elif comp.kind == "output":
                    value = bool(dependencies and dependencies[0])
                else:
                    value = bool(dependencies and dependencies[0])
                if values.get(name) != value:
                    values[name] = value
                    changed = True
            if not changed:
                break
        else:
            return SimulationResult(False, {name: values.get(name, False) for name in outputs}, ticks, True, "Circuit did not stabilize within tick budget")

        return SimulationResult(True, {name: values.get(name, False) for name in outputs}, ticks, False, "Circuit stabilized")


def gate_contract() -> RedstoneSimulator:
    return RedstoneSimulator([
        Component("lever", "input"),
        Component("line_a", "wire", ("lever",)),
        Component("line_b", "wire", ("line_a",)),
        Component("repeater", "repeater", ("line_b",), delay=1),
        Component("left_piston", "output", ("repeater",)),
        Component("right_piston", "output", ("repeater",)),
    ])

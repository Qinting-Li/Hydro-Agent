"""Allowed-input enforcement for every agent-visible tool call."""

from __future__ import annotations


def audit_leakage(task: dict, trajectory: dict) -> dict:
    allowed = set(task["allowed_inputs"])
    forbidden = set(task["forbidden_inputs"])
    step_audits = []
    agent_accesses = 0
    violations = 0
    for step in trajectory["steps"]:
        accessed = set(step.get("accessed_inputs", []))
        scope = step.get("execution_scope", "agent")
        forbidden_hits = sorted(accessed & forbidden) if scope == "agent" else []
        undeclared_hits = sorted(accessed - allowed - forbidden) if scope == "agent" else []
        step_violations = sorted(set(forbidden_hits + undeclared_hits))
        if scope == "agent":
            agent_accesses += len(accessed)
            violations += len(step_violations)
        step_audits.append(
            {
                "step": step["step"],
                "tool_name": step["tool_name"],
                "execution_scope": scope,
                "accessed_inputs": sorted(accessed),
                "forbidden_hits": forbidden_hits,
                "undeclared_hits": undeclared_hits,
                "passed": not step_violations,
            }
        )
    score = 1.0 if violations == 0 else max(0.0, 1.0 - violations / max(agent_accesses, 1))
    return {
        "allowed_inputs": sorted(allowed),
        "forbidden_inputs": sorted(forbidden),
        "step_audits": step_audits,
        "violations": violations,
        "passed": violations == 0,
        "score": round(score, 6),
    }

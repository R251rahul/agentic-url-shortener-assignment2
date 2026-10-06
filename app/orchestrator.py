from __future__ import annotations
import json, time, uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable
from .models import NodeStatus, RunStatus, AuditEvent

@dataclass
class Node:
    id: str
    stage: str
    deps: set[str] = field(default_factory=set)
    risk: str = "low"
    max_retries: int = 2
    status: NodeStatus = NodeStatus.PENDING
    attempts: int = 0
    output: dict = field(default_factory=dict)
    error: str | None = None

class Policy:
    HIGH_IMPACT = {"implementation", "release"}
    FORBIDDEN = ("drop database", "disable authentication", "commit secret", "delete production")
    def check(self, stage: str, context: dict) -> tuple[bool, str]:
        text = json.dumps(context).lower()
        for item in self.FORBIDDEN:
            if item in text:
                return False, f"Policy violation: {item}"
        if stage == "release" and not context.get("security_passed"):
            return False, "Release requires security validation"
        return True, "allowed"

class Agent:
    def __init__(self, name: str, fn: Callable[[dict], dict]): self.name, self.fn = name, fn
    def run(self, context: dict) -> dict: return self.fn(context)

class Orchestrator:
    def __init__(self, store):
        self.store = store
        self.policy = Policy()
        self.runs: dict[str, dict] = {}
        self.agents = self._agents()

    def _agents(self):
        return {
            "requirements": Agent("requirements-agent", self._requirements),
            "architecture": Agent("architecture-agent", self._architecture),
            "brownfield_analysis": Agent("brownfield-agent", self._brownfield),
            "implementation": Agent("implementation-agent", self._implementation),
            "tests": Agent("test-agent", self._tests),
            "security": Agent("security-agent", self._security),
            "documentation": Agent("documentation-agent", self._documentation),
            "release": Agent("release-agent", self._release),
        }

    def _requirements(self, c):
        req = c["requirement"]
        ambiguous = c["scenario"] == "ambiguous"
        return {"normalized_requirement": req.strip(), "ambiguities": [
            "expiry semantics", "analytics retention", "custom alias collision behavior"] if ambiguous else [],
            "acceptance": ["create short URL", "resolve short URL", "record click analytics", "reject unsafe URLs"]}

    def _architecture(self, c):
        return {"components": ["FastAPI", "URL service", "SQLite/Postgres adapter", "agentic DAG orchestrator", "policy/audit layer"],
                "decisions": ["DAG execution", "stateful context", "human gates for high-impact stages", "bounded retries", "safe-stop"]}

    def _brownfield(self, c):
        return {"impacted_modules": ["url_service", "analytics", "API routes", "tests"],
                "change_strategy": "additive first; preserve existing API contracts; regression-test redirect path"}

    def _implementation(self, c):
        if c.get("scenario") == "brownfield" and not c.get("architecture"): raise RuntimeError("architecture context missing")
        return {"artifacts": ["shorten API", "redirect API", "analytics API", "persistence", "validation"], "rollback": "restore previous service version"}

    def _tests(self, c):
        return {"unit": ["URL validation", "code generation", "expiry", "collision"], "integration": ["create->redirect->analytics", "404/409/410 paths"], "result": "PASS"}

    def _security(self, c):
        return {"checks": ["scheme allow-list", "input validation", "no secrets in config", "release gate present"], "result": "PASS"}

    def _documentation(self, c):
        return {"artifacts": ["README", "architecture", "scenario walkthroughs", "API examples", "limitations"]}

    def _release(self, c):
        return {"release_readiness": "READY", "checks": ["tests pass", "security pass", "approval recorded", "audit trail available"]}

    def _graph(self, scenario):
        nodes = [
            Node("requirements", "requirements"),
            Node("architecture", "architecture", {"requirements"}),
            Node("implementation", "implementation", {"architecture"}, "high"),
            Node("tests", "tests", {"implementation"}),
            Node("security", "security", {"implementation"}, "high"),
            Node("documentation", "documentation", {"requirements", "architecture"}),
            Node("release", "release", {"tests", "security", "documentation"}, "high")]
        if scenario == "brownfield":
            nodes.insert(2, Node("brownfield_analysis", "brownfield_analysis", {"requirements"}))
            nodes[3].deps.add("brownfield_analysis")
        return {n.id: n for n in nodes}

    def start(self, scenario, requirement, auto_approve=True):
        run_id = str(uuid.uuid4())
        nodes = self._graph(scenario)
        ctx = {"run_id": run_id, "scenario": scenario, "requirement": requirement, "context_version": 1,
               "security_passed": False, "approvals": {}, "created_at": time.time()}
        self.runs[run_id] = {"status": RunStatus.RUNNING, "nodes": nodes, "context": ctx, "metrics": {"retries": 0, "rollbacks": 0, "success_rate": 0.0, "mttr_ms": 0.0, "latency_ms": 0.0}, "approval": None}
        self._audit(run_id, None, "RUN_STARTED", "human", {"scenario": scenario})
        self._execute(run_id, auto_approve)
        return self.snapshot(run_id)

    def approve(self, run_id, approved, comment=""):
        run = self.runs.get(run_id)
        if not run: raise KeyError(run_id)
        run["approval"] = {"approved": approved, "comment": comment, "at": time.time()}
        self._audit(run_id, None, "HUMAN_APPROVAL", "human", run["approval"])
        if approved and run["status"] == RunStatus.WAITING_APPROVAL:
            run["status"] = RunStatus.RUNNING
            self._execute(run_id, False)
        elif not approved:
            run["status"] = RunStatus.SAFE_STOPPED
            self._audit(run_id, None, "SAFE_STOP", "governance", {"reason": "human rejected"})
        return self.snapshot(run_id)

    def snapshot(self, run_id):
        r = self.runs[run_id]
        return {"run_id": run_id, "status": r["status"], "metrics": r["metrics"],
                "context": r["context"], "nodes": {k: {"stage":n.stage,"status":n.status,"attempts":n.attempts,"output":n.output,"error":n.error} for k,n in r["nodes"].items()}}

    def audit(self, run_id):
        return [dict(x) for x in self.store.audit_for_run(run_id)]

    def _execute(self, run_id, auto_approve):
        r = self.runs[run_id]; nodes = r["nodes"]; started = time.time()
        while True:
            ready = [n for n in nodes.values() if n.status == NodeStatus.PENDING and all(nodes[d].status == NodeStatus.SUCCEEDED for d in n.deps)]
            if not ready: break
            parallel = [n for n in ready if n.stage not in Policy.HIGH_IMPACT]
            high = [n for n in ready if n.stage in Policy.HIGH_IMPACT]
            if parallel:
                with ThreadPoolExecutor(max_workers=min(4, len(parallel))) as pool:
                    futs = {pool.submit(self._run_node, run_id, n): n for n in parallel}
                    for f in as_completed(futs):
                        if not f.result():
                            r["status"] = RunStatus.FAILED; return
            if high:
                n = high[0]
                allowed, reason = self.policy.check(n.stage, r["context"])
                if not allowed:
                    n.status = NodeStatus.BLOCKED; n.error = reason; r["status"] = RunStatus.SAFE_STOPPED; self._audit(run_id,n.id,"POLICY_BLOCK","governance",{"reason":reason}); return
                if not auto_approve and not r.get("approval"):
                    r["status"] = RunStatus.WAITING_APPROVAL; self._audit(run_id,n.id,"APPROVAL_REQUIRED","governance",{"stage":n.stage}); return
                if r.get("approval") and not r["approval"].get("approved"):
                    r["status"] = RunStatus.SAFE_STOPPED; return
                if not self._run_node(run_id, n): r["status"] = RunStatus.FAILED; return
        if all(n.status == NodeStatus.SUCCEEDED for n in nodes.values()): r["status"] = RunStatus.SUCCEEDED
        else: r["status"] = RunStatus.FAILED
        r["metrics"]["latency_ms"] = round((time.time()-started)*1000, 2)
        r["metrics"]["success_rate"] = 1.0 if r["status"] == RunStatus.SUCCEEDED else 0.0
        r["metrics"]["mttr_ms"] = r["metrics"]["latency_ms"] if r["metrics"]["retries"] else 0.0
        self._audit(run_id,None,"RUN_FINISHED","orchestrator",{"status":r["status"]})

    def _run_node(self, run_id, n):
        r = self.runs[run_id]; n.status = NodeStatus.RUNNING
        self._audit(run_id,n.id,"NODE_STARTED","orchestrator",{"stage":n.stage})
        for attempt in range(1, n.max_retries+2):
            n.attempts = attempt
            try:
                allowed, reason = self.policy.check(n.stage, r["context"])
                if not allowed: raise PermissionError(reason)
                output = self.agents[n.stage].run(r["context"] | {k:v.output for k,v in r["nodes"].items() if v.status == NodeStatus.SUCCEEDED})
                n.output = output; n.status = NodeStatus.SUCCEEDED
                if n.stage == "security": r["context"]["security_passed"] = output.get("result") == "PASS"
                r["context"][n.stage] = output; r["context"]["context_version"] += 1
                self._audit(run_id,n.id,"NODE_SUCCEEDED","agent",{"attempt":attempt})
                return True
            except Exception as e:
                n.error = str(e); r["metrics"]["retries"] += 1
                self._audit(run_id,n.id,"NODE_RETRY","agent",{"attempt":attempt,"error":str(e)})
                if attempt > n.max_retries:
                    n.status = NodeStatus.FAILED; self._audit(run_id,n.id,"NODE_FAILED","agent",{"error":str(e)}); return False
        return False

    def rollback(self, run_id, reason="operator requested rollback"):
        r = self.runs.get(run_id)
        if not r: raise KeyError(run_id)
        for n in r["nodes"].values():
            if n.status == NodeStatus.SUCCEEDED and n.stage in {"implementation", "tests", "security", "documentation", "release"}:
                n.status = NodeStatus.ROLLED_BACK
        r["metrics"]["rollbacks"] += 1
        r["status"] = RunStatus.ROLLED_BACK
        self._audit(run_id, None, "ROLLBACK", "operator", {"reason": reason})
        return self.snapshot(run_id)

    def replan(self, run_id, updated_requirement):
        r = self.runs.get(run_id)
        if not r: raise KeyError(run_id)
        r["context"]["requirement"] = updated_requirement
        r["context"]["context_version"] += 1
        for n in r["nodes"].values():
            if n.stage in {"requirements", "architecture", "implementation", "tests", "documentation", "release"}:
                n.status = NodeStatus.PENDING; n.output = {}; n.error = None
        r["status"] = RunStatus.RUNNING
        self._audit(run_id,None,"REPLAN","human","{" + "\"reason\":\"upstream requirement changed\"}")
        self._execute(run_id, True)
        return self.snapshot(run_id)

    def _audit(self, run_id, node_id, event, actor, details):
        self.store.add_audit(datetime.now(timezone.utc), run_id, node_id, event, actor, json.dumps(details, default=str))

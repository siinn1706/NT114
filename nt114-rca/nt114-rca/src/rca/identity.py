"""Explicit per-system service identity map.

Rules, in order: `alias` (reviewed entries in configs/service_aliases.yaml), `pod-to-deployment`
(Kubernetes pod suffixes, only when the stripped name is a known service), `canon` (the legacy
`rca.data.canon`). Every mapping is recorded with its rule so the map can be audited.
"""
from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

import yaml

from .data import canon

# The pod-template-hash is a safe-encoded decimal uint32, so it is usually 8-10 characters but can be
# shorter: RCA100 has `checkout-5489989-q7ws7` (7 characters). Shorter hashes must use the vowel-free
# safe-encode alphabet, so names such as `ts-config-mongo` stay plain.
DEPLOYMENT_POD = re.compile(r"^(?P<d>.+)-(?:[a-z0-9]{8,10}|[bcdfghjklmnpqrstvwxz2456789]{6,7})-[a-z0-9]{5}$")
STATEFULSET_POD = re.compile(r"^(?P<d>.+)-\d+$")
KINDS = ("service", "pod", "container", "node", "infra")


def pod_pattern(name: str) -> str:
    if DEPLOYMENT_POD.match(name):
        return "deployment"
    if STATEFULSET_POD.match(name):
        return "statefulset"
    return "plain"


def load_aliases(path: Path | None) -> dict:
    """{system: {raw: {"service_id": str, "kind": str (optional), "reason": str}}} from the reviewed alias file."""
    if path is None or not Path(path).is_file():
        return {}
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data.get("aliases", {}) or {}


class ServiceMap:
    def __init__(self, aliases: dict | None = None, infra: dict[str, set[str]] | None = None):
        self.aliases = aliases or {}
        self.infra = {k: set(v) for k, v in (infra or {}).items()}
        self.entries: dict[str, dict[str, dict]] = defaultdict(dict)
        self.known: dict[str, set[str]] = defaultdict(set)

    def declare_services(self, system: str, raw_names) -> None:
        """Register raw names known to be services of `system` (used by the pod rule)."""
        for n in raw_names:
            self.known[system].add(canon(n))

    def map(self, system: str, raw: str, kind: str = "service") -> str | None:
        raw = str(raw)
        sysmap = self.entries[system]
        if raw in sysmap:
            return sysmap[raw]["service_id"]
        alias = self.aliases.get(system, {}).get(raw)
        if alias:
            sid, rule, kind = alias["service_id"], "alias", alias.get("kind", kind)
        elif raw in self.infra.get(system, set()):
            sid, rule, kind = canon(raw), "canon", "infra"
        elif kind in ("pod", "container"):
            sid, rule = None, "unmapped"
            for rx in (DEPLOYMENT_POD, STATEFULSET_POD):
                m = rx.match(raw)
                if m and canon(m["d"]) in self.known[system]:
                    sid, rule = canon(m["d"]), "pod-to-deployment"
                    break
            if sid is None and canon(raw) in self.known[system]:
                sid, rule = canon(raw), "canon"
        else:
            sid, rule = canon(raw), "canon"
        if sid is not None and canon(sid) != sid:
            raise ValueError(f"service_id {sid!r} is not canon-stable")
        sysmap[raw] = {"service_id": sid, "rule": rule, "kind": kind}
        return sid

    def resolve(self, system: str, raw: str, kind: str = "service") -> str | None:
        """`map` without recording: for label entities, which must not shape the visible service map."""
        raw = str(raw)
        if raw in self.entries[system]:
            return self.entries[system][raw]["service_id"]
        sid = self.map(system, raw, kind)
        del self.entries[system][raw]
        return sid

    def record(self, system: str, raw: str, service_id: str | None, rule: str, kind: str) -> str | None:
        """Register a mapping decided by a documented adapter rule (e.g. a component's status port)."""
        if service_id is not None and canon(service_id) != service_id:
            raise ValueError(f"service_id {service_id!r} is not canon-stable")
        self.entries[system].setdefault(str(raw), {"service_id": service_id, "rule": rule, "kind": kind})
        return self.entries[system][str(raw)]["service_id"]

    def is_infra(self, system: str, service_id: str) -> bool:
        return any(e["service_id"] == service_id and e["kind"] == "infra" for e in self.entries[system].values())

    def collisions(self, system: str) -> dict[str, list[str]]:
        """service_id -> raw names that differ after case/punctuation folding and were merged by no
        explicit rule (reviewed alias, pod suffix, or a documented adapter rule passed to `record`)."""
        by_id: dict[str, set[str]] = defaultdict(set)
        for raw, e in self.entries[system].items():
            if e["service_id"] is None or e["rule"] != "canon":
                continue
            by_id[e["service_id"]].add(raw)
        out = {}
        for sid, raws in by_id.items():
            folded = {re.sub(r"[^a-z0-9]", "", r.lower()) for r in raws}
            if len(folded) > 1:
                out[sid] = sorted(raws)
        return out

    def to_json(self) -> dict:
        return {s: {r: dict(e) for r, e in sorted(m.items())} for s, m in sorted(self.entries.items())}

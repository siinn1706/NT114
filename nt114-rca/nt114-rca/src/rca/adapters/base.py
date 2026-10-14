"""Adapter contract shared by every dataset adapter.

Adapters discover incidents, read labels, map service identities, place the anchor and window, and
yield normalized Arrow batches. They never write files; the build driver (`rca.prep`) owns
missingness, provenance, validation and persistence.
"""
from __future__ import annotations

import hashlib
import io
import zipfile
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Iterator, Literal

Severity = Literal["info", "warn", "quarantine", "reject"]


@dataclass(frozen=True)
class RawRef:
    """Lazy pointer to raw bytes: `member` is `<relpath under raw>` or `<archive relpath>!<member>`."""
    source_id: str
    member: str
    sha256: str | None = None
    size: int | None = None
    crc32: int | None = None   # zip member CRC; part of the input digest without re-reading bytes


@dataclass
class Finding:
    code: str
    severity: Severity
    modality: str | None = None
    detail: str = ""
    evidence_ref: str | None = None

    def to_json(self) -> dict:
        return {"code": self.code, "severity": self.severity, "modality": self.modality,
                "detail": self.detail, "evidence_ref": self.evidence_ref}


@dataclass
class DiscoveredIncident:
    source_incident_key: str
    source_incident_id: str
    refs: dict[str, list[RawRef]]          # role -> refs; roles: metrics:<set>, logs, traces, label, aux
    hints: dict = field(default_factory=dict)  # adapter-private; never written to visible/


@dataclass
class LabelDraft:
    original: object
    entities: list[dict]
    root_service_ids: list[str]
    primary_root_service: str | None
    label_granularity: str
    fault_type_raw: str
    fault_family: str
    label_source: str
    injection_kind: str
    label_validity: str
    validity_notes: list[str]
    eval_tier: str
    eval_tier_reason: str
    fault_cell: str
    system: str
    dataset_subset: str | None
    lineage_group: str
    copy_of: str | None = None
    duplicate_of_key: str | None = None
    group_key: str | None = None       # label-free key shared by records of one source incident
    label_artifacts: list[dict] = field(default_factory=list)
    truth_end_ns: int | None = None


@dataclass
class TimeInfo:
    anchor_ns: int
    anchor_kind: str
    anchor_original: dict
    end_ns: int | None
    window_start_ns: int | None    # None: whole member (pre-cut cases)
    window_end_ns: int | None
    clipped_start: bool = False
    clipped_end: bool = False


@dataclass
class BuildContext:
    data_home: Path
    raw_root: Path
    config: dict
    dataset_cfg: dict
    work: Path


class MemberSource:
    """Read-only access to members of a directory tree or a zip archive, in binary mode."""

    def __init__(self, source_id: str, raw_root: Path, rel: str):
        self.source_id, self.raw_root, self.rel = source_id, Path(raw_root), rel
        self.path = self.raw_root / rel
        self.is_zip = self.path.is_file() and zipfile.is_zipfile(self.path)
        self._zip: zipfile.ZipFile | None = None
        self._infos: dict[str, zipfile.ZipInfo] | None = None

    def __getstate__(self):
        return {"source_id": self.source_id, "raw_root": self.raw_root, "rel": self.rel}

    def __setstate__(self, st):
        self.__init__(st["source_id"], st["raw_root"], st["rel"])

    def _z(self) -> zipfile.ZipFile:
        if self._zip is None:
            self._zip = zipfile.ZipFile(self.path)
            self._infos = {i.filename: i for i in self._zip.infolist() if not i.is_dir()}
        return self._zip

    def names(self) -> list[str]:
        if self.is_zip:
            self._z()
            return sorted(self._infos)
        return sorted(p.relative_to(self.path).as_posix() for p in self.path.rglob("*") if p.is_file())

    def size(self, name: str) -> int:
        if self.is_zip:
            self._z()
            return self._infos[name].file_size
        return (self.path / PurePosixPath(name)).stat().st_size

    def open(self, name: str):
        if self.is_zip:
            return self._z().open(name)
        return open(self.path / PurePosixPath(name), "rb")

    def read_bytes(self, name: str) -> bytes:
        with self.open(name) as f:
            return f.read()

    def read_text(self, name: str) -> str:
        return self.read_bytes(name).decode("utf-8", errors="strict")

    def ref(self, name: str, with_hash: bool = False) -> RawRef:
        member = f"{self.rel}!{name}" if self.is_zip else f"{self.rel}/{name}"
        return RawRef(self.source_id, member, sha256_member(self, name) if with_hash else None, self.size(name))

    def close(self):
        if self._zip is not None:
            self._zip.close()
            self._zip = None


def sha256_member(src: MemberSource, name: str) -> str:
    h = hashlib.sha256()
    with src.open(name) as f:
        while b := f.read(1 << 20):
            h.update(b)
    return h.hexdigest()


class Adapter:
    """Base class; subclasses implement the five contract methods."""
    name = "base"
    version = "0.0.0"
    dataset_id = "base"
    source_ids: tuple[str, ...] = ()

    def discover(self, ctx: BuildContext) -> Iterator[DiscoveredIncident]:
        raise NotImplementedError

    def read_label(self, inc: DiscoveredIncident, ctx: BuildContext) -> tuple[LabelDraft | None, list[Finding]]:
        raise NotImplementedError

    def service_map(self, ctx: BuildContext):
        raise NotImplementedError

    def anchor_and_window(self, inc: DiscoveredIncident, label: LabelDraft, ctx: BuildContext) -> tuple[TimeInfo | None, list[Finding]]:
        raise NotImplementedError

    def normalize(self, inc: DiscoveredIncident, modality: str, tinfo: TimeInfo, smap, ctx: BuildContext,
                  findings: list[Finding]) -> Iterator:
        """Yield Arrow batches of `modality`. Raise `ModalityAbsent` when the source never collected
        it; return without yielding when a member exists but has no rows."""
        raise NotImplementedError

    def candidates(self, inc: DiscoveredIncident, services_by_modality: dict[str, list[str]], smap, system: str) -> tuple[list[str], str]:
        svcs = set()
        for s in services_by_modality.values():
            svcs |= set(s)
        return sorted(s for s in svcs if s and not smap.is_infra(system, s)), "telemetry"

    def close(self):
        pass


def checksum_index(ctx: BuildContext) -> dict[str, str]:
    """{member path relative to raw/: sha256} from the acquisition manifest (`manifests/checksums.sha256`,
    paths written as `data/raw/<...>`). Empty when the manifest is absent (fixtures, bundles)."""
    p = ctx.data_home / "manifests" / "checksums.sha256"
    if not p.is_file():
        return {}
    out = {}
    with open(p, encoding="utf-8") as f:
        for line in f:
            h, _, path = line.rstrip("\n").partition("  ")
            if path.startswith("data/raw/"):
                out[path[len("data/raw/"):]] = h
    return out


def member_index(inc: DiscoveredIncident, member: str) -> int:
    """Index of `member` in the source_index member list (role-sorted, as written by the driver)."""
    i = 0
    for _role, refs in sorted(inc.refs.items()):
        for r in refs:
            if r.member == member:
                return i
            i += 1
    raise KeyError(member)


class ModalityAbsent(Exception):
    """The source never collected this modality for the incident (natural absence)."""


def text_stream(src: MemberSource, name: str) -> io.BufferedReader:
    return io.BufferedReader(src.open(name))

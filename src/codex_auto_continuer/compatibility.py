"""Exact-build certification and a small, consumer-specific schema contract."""
from __future__ import annotations

import hashlib
import json
import platform
import re
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path

from . import __version__
from .codex import DaemonInfo, _run, binary_version, codex_version, daemon_version
from .errors import CodexCommandError, ProtocolError
from .telemetry import failure

RECORD = Path(__file__).with_name("compatibility.json")
_CONSTRAINTS = {"type", "enum", "const", "minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum",
                "multipleOf", "minItems", "maxItems", "uniqueItems", "minLength", "maxLength", "pattern",
                "format", "additionalProperties", "additionalItems", "minProperties", "maxProperties",
                "dependencies", "not", "if", "then", "else", "contains", "patternProperties"}
THREAD = {key: None for key in ("id", "updatedAt", "status", "source", "originator", "archived")}
TURN = {key: None for key in ("id", "status", "completedAt", "error")}
TURN["items"] = {"$type": "userMessage", "type": None, "clientId": None}
QUEUE = {"id": None, "clientUserMessageId": None, "input": None}
WINDOWS = {key: {"usedPercent": None, "resetsAt": None} for key in ("primary", "secondary")}
# Only fields read or sent by CAC. New unrelated endpoints/optional fields do not change this contract.
METHODS = {
    "initialize": ("Initialize", {"clientInfo": dict.fromkeys(("name", "title", "version")),
        "capabilities": dict.fromkeys(("experimentalApi", "requestAttestation", "optOutNotificationMethods"))}, {"userAgent": None}),
    "thread/list": ("ThreadList", dict.fromkeys(("cursor", "limit", "sortKey", "sortDirection", "modelProviders", "sourceKinds", "archived")), {"data": THREAD, "nextCursor": None}),
    "thread/read": ("ThreadRead", {"threadId": None, "includeTurns": None}, {"thread": THREAD}),
    "thread/turns/list": ("ThreadTurnsList", dict.fromkeys(("threadId", "cursor", "limit", "sortDirection", "itemsView")), {"data": TURN, "nextCursor": None}),
    "account/rateLimits/read": ("GetAccountRateLimits", {}, {"ordinaryUsageAllowed": None, "rateLimits": WINDOWS, "rateLimitsByLimitId": WINDOWS}),
    "thread/resume": ("ThreadResume", {"threadId": None, "excludeTurns": None}, {"thread": THREAD}),
    "thread/queue/add": ("ThreadQueueAdd", {"threadId": None, "input": None, "clientUserMessageId": None}, {"queuedSubmission": QUEUE}),
    "thread/queue/list": ("ThreadQueueList", {"threadId": None, "cursor": None, "limit": None}, {"data": QUEUE, "nextCursor": None}),
    "thread/queue/delete": ("ThreadQueueDelete", {"threadId": None, "queuedSubmissionId": None}, {"deleted": None}),
}
READ_METHODS = {"initialize", "thread/list", "thread/read", "thread/turns/list", "account/rateLimits/read"}


class CompatibilityBlocked(ProtocolError):
    pass


def _project(node: dict, document: dict, fields=None, *, request=False, depth=0):
    if depth > 40 or not isinstance(node, dict):
        raise ProtocolError("Unsupported or recursive Codex schema contract.")
    if "$ref" in node:
        ref = node["$ref"]
        if not ref.startswith("#/definitions/"):
            raise ProtocolError("Codex schema uses an unsupported external reference.")
        node = document["definitions"][ref.removeprefix("#/definitions/")]
    result = {key: node[key] for key in sorted(_CONSTRAINTS & node.keys())}
    if "properties" in node:
        properties = node["properties"]
        selected = properties if fields is None else fields
        result["properties"] = {key: _project(properties[key], document, None if fields is None else fields[key],
            request=request, depth=depth+1) for key in sorted(selected) if key in properties}
        required = set(node.get("required", []))
        result["required"] = sorted(required if request else required & set(selected))
    if "items" in node:
        result["items"] = _project(node["items"], document, fields, request=request, depth=depth+1)
    if isinstance(node.get("additionalProperties"), dict):
        result["additionalProperties"] = _project(node["additionalProperties"], document, fields, request=request, depth=depth+1)
    for union in ("allOf", "anyOf", "oneOf"):
        if union in node:
            choices = node[union]
            if fields and "$type" in fields:
                choices = [value for value in choices if fields["$type"] in value.get("properties", {}).get("type", {}).get("enum", [])]
            variants = [_project(value, document, fields, request=request, depth=depth+1) for value in choices]
            result[union] = sorted(variants, key=lambda value: json.dumps(value, sort_keys=True))
    return result


def schema_contract(directory: Path) -> dict:
    try:
        requests = json.loads((directory / "ClientRequest.json").read_text(encoding="utf-8"))
        variants = {entry["properties"]["method"]["enum"][0]: entry for entry in requests["oneOf"]}
        # Initialize uses v1 definitions in the aggregate schema; v2 responses are standalone.
        aggregate = json.loads((directory / "codex_app_server_protocol.schemas.json").read_text(encoding="utf-8"))
        out = {}
        for method, (name, sent, received) in METHODS.items():
            params = variants[method]["properties"]["params"]
            response_path = directory / "v2" / f"{name}Response.json"
            if method == "initialize":
                response = aggregate["definitions"]["InitializeResponse"]
                document = aggregate
            else:
                document = json.loads(response_path.read_text(encoding="utf-8"))
                response = document
            out[method] = {"request": _project(params, requests, sent, request=True),
                           "response": _project(response, document, received)}
        notifications = json.loads((directory / "ServerNotification.json").read_text(encoding="utf-8"))
        selected = {entry["properties"]["method"]["enum"][0]: entry for entry in notifications["oneOf"]}
        for method in ("thread/queue/changed", "turn/completed"):
            out["thread/queue/list"][method] = _project(selected[method]["properties"]["params"], notifications,
                {"threadId": None, **({"turn": TURN} if method == "turn/completed" else {})})
        return out
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise ProtocolError("Codex experimental schema is missing a required CAC method or field.") from exc


def contract_digest(contract: dict) -> str:
    return hashlib.sha256(json.dumps(contract, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


@dataclass(frozen=True)
class Compatibility:
    status: str = "unverified"
    reason: str = "Codex compatibility has not been checked. Queue writes are blocked."
    cli_version: str | None = None
    app_server_version: str | None = None
    cli_sha256: str | None = None
    server_sha256: str | None = None
    schema_sha256: str | None = None
    schema_source: str | None = None
    read_allowed: bool = True
    policy: str = "strict"

    @property
    def dispatch_allowed(self):
        return self.status == "certified" or (self.status == "untested" and self.policy == "balanced"
            and all(re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+(?:\+[0-9A-Za-z.-]+)?", value or "")
                    for value in (self.cli_version, self.app_server_version)))

    def report(self):
        return asdict(self) | {"dispatch_allowed": self.dispatch_allowed}


class CompatibilityGate:
    def __init__(self, staging: Path):
        self.staging = staging
        self._schemas = {}
        self._hashes = {}
        self.record = json.loads(RECORD.read_text(encoding="utf-8"))

    def binary_hash(self, binary: str | Path) -> str:
        path = Path(binary).resolve(strict=True)
        stat = path.stat()
        key = (str(path), stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns)
        if key not in self._hashes:
            with path.open("rb") as stream:
                self._hashes[key] = hashlib.file_digest(stream, "sha256").hexdigest()
            if len(self._hashes) > 8:
                del self._hashes[next(iter(self._hashes))]
        return self._hashes[key]

    def inspect(self, cli: str, daemon: DaemonInfo, user_agent: str, timeout: float, policy: str = "strict") -> Compatibility:
        if policy not in {"balanced", "strict"}:
            raise ValueError("Invalid compatibility policy.")
        values = {"cli_version": codex_version(cli, timeout), "app_server_version": daemon.app_server_version, "policy": policy}
        check = "binary identity"
        try:
            values["cli_sha256"] = self.binary_hash(cli)
            server = daemon.managed_codex_path
            connected = re.fullmatch(r"[^/\s]+/([^\s]+) .*", user_agent or "")
            if (not connected or not server or not server.is_absolute() or
                daemon.cli_version != values["cli_version"] or
                connected.group(1) != daemon.app_server_version or
                daemon.managed_codex_version != daemon.app_server_version):
                return Compatibility(reason="Codex daemon/connection identity is missing or changed. Scanning and queue writes are blocked; check Codex daemon health.", read_allowed=False, **values)
            server_version, server_kind = binary_version(str(server), timeout)
            if server_version != daemon.app_server_version:
                return Compatibility(reason="Managed binary and connected daemon versions differ. Scanning and queue writes are blocked; inspect daemon health.", read_allowed=False, **values)
            values["server_sha256"] = self.binary_hash(server)
            if server_kind != "codex-cli":
                return Compatibility(reason="The managed executable is a standalone app-server, not the supported full CLI package. Its own schema cannot be verified. Scanning and queue writes are blocked; inspect Codex daemon health and update CAC.", read_allowed=False, **values)
            values["schema_source"] = "managed_binary"
            key = (values["server_sha256"], daemon.app_server_version)
            if key not in self._schemas:
                check = "experimental schema generation"
                self.staging.mkdir(parents=True, exist_ok=True)
                with tempfile.TemporaryDirectory(prefix="schema-", dir=self.staging) as temporary:
                    result = _run(str(server), ["app-server", "generate-json-schema", "--experimental", "--out", temporary], timeout)
                    if result.returncode != 0:
                        raise ProtocolError("Codex could not generate its experimental schema.")
                    check = "experimental schema contract"
                    self._schemas = {key: schema_contract(Path(temporary))}
            contract = self._schemas[key]
            values["schema_sha256"] = contract_digest(contract)
            different = [name for name in METHODS if contract[name] != self.record["contract"][name]]
            if different:
                return Compatibility(status="schema_mismatch", reason="Codex contract changed: " + ", ".join(different) + ". Update CAC; pending work is preserved.", read_allowed=not bool(READ_METHODS & set(different)), **values)
            target = "windows-x86_64" if platform.system() == "Windows" and platform.machine().lower() in {"amd64", "x86_64"} else "unsupported"
            if target == "unsupported":
                return Compatibility(status="unsupported", reason="CAC supports native Windows x86_64 recovery only. Queue writes are blocked on this platform.", **values)
            for certificate in self.record["certificates"]:
                if (certificate["cac_version"] == __version__ and certificate["platform"] == target and
                    all(certificate[field] == values[field] for field in ("cli_version", "app_server_version", "cli_sha256", "server_sha256", "schema_sha256"))):
                    return Compatibility(status="certified", reason="Exact Codex CLI/daemon build passed CAC's native recovery tests.", **values)
            provisional = Compatibility(status="untested", **values)
            action = ("Balanced mode permits recovery with runtime checks. Select Read Full Status for evidence."
                      if provisional.dispatch_allowed else "Queue writes are blocked. Use a certified stable build or update CAC.")
            reason = f"Codex CLI {values['cli_version']} / daemon {daemon.app_server_version} passes schema checks but is not behavior-certified for CAC {__version__}. " + action
            return Compatibility(status="untested", reason=reason, **values)
        except (OSError, CodexCommandError, ProtocolError) as exc:
            failure("compatibility.verification_failed", exc, check=check, cliVersion=values["cli_version"],
                daemonVersion=daemon.app_server_version, errorCode=getattr(exc, "errno", None))
            return Compatibility(status="unverified", reason=f"Cannot verify Codex {check}. Scanning and queue writes are blocked. Check daemon health, file permissions and local telemetry; update CAC if the interface changed.", read_allowed=False, **values)

    def recheck(self, cli: str, user_agent: str, timeout: float, policy: str = "strict") -> Compatibility:
        try:
            return self.inspect(cli, daemon_version(cli, timeout), user_agent, timeout, policy)
        except (CodexCommandError, ProtocolError) as exc:
            failure("compatibility.identity_unavailable", exc)
            return Compatibility(reason="Codex daemon identity is unavailable or unsupported. Scanning and queue writes are blocked; CAC will recheck. Inspect daemon health and local telemetry.", read_allowed=False, policy=policy)

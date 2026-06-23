"""Resolve the set of per-event namespaces this Pulumi stack should bind to.

The tenant rams-config repo ships an `events.yaml` at its root listing every
event instance. Pulumi reads that same file (via the relative path set in
`RAMS:events_file`) and derives `uber_instances` from it — eliminating the
drift risk of maintaining two separate lists.

If `RAMS:events_file` is unset (e.g. when running Pulumi against the
Ubersystem-EKS repo alone for development), this falls back to the legacy
`RAMS:uber_instances` list. That preserves the old behavior for any caller
who hasn't migrated yet.
"""
from __future__ import annotations

from pathlib import Path

import pulumi
import yaml


def _events_path() -> Path | None:
    cfg = pulumi.Config()
    rel = cfg.get("events_file")
    if not rel:
        return None
    # Resolve relative to the project working directory (platform/).
    return (Path.cwd() / rel).resolve()


def _normalize_server(entry) -> dict:
    """Coerce a server entry into a dict with at least a `name` key.

    Entries may be a bare namespace string (legacy) or a dict carrying
    per-instance `email_identities` and `lambdas` lists.
    """
    if isinstance(entry, str):
        return {"name": entry}
    if isinstance(entry, dict):
        if not entry.get("name"):
            raise ValueError(f"server entry missing `name`: {entry!r}")
        return entry
    raise ValueError(f"unexpected server entry: {entry!r}")


def load_servers() -> list[dict]:
    """Return the per-instance server definitions for this stack.

    Each server is a dict with a `name` (the namespace / event name) and
    optional `email_identities` and `lambdas` lists used to scope its IAM
    role. Order matches the source list for stable Pulumi resource ordering.
    """
    cfg = pulumi.Config()
    stack = pulumi.get_stack()

    events_yaml = _events_path()
    if events_yaml is None or not events_yaml.exists():
        # Legacy fallback: hand-maintained list in Pulumi.<stack>.yaml.
        return [_normalize_server(entry) for entry in cfg.require_object("uber_instances")]

    with events_yaml.open() as fh:
        data = yaml.safe_load(fh) or {}

    servers: list[dict] = []
    for event in data.get("events", []):
        if event.get("environment") != stack:
            continue
        name = event.get("name")
        if not name:
            raise ValueError(f"event entry missing `name`: {event!r}")
        servers.append({
            "name": name,
            "email_identities": event.get("email_identities"),
            "lambdas": event.get("lambdas"),
        })

    if not servers:
        raise ValueError(
            f"events.yaml at {events_yaml} has no events for stack {stack!r}"
        )
    return servers


def load_namespaces() -> list[str]:
    """Return just the namespace names for this stack.

    Order matches load_servers() — useful for stable Pulumi resource ordering.
    """
    return [server["name"] for server in load_servers()]

"""Reviewed release artifact packaging, not an HTTP file/code distribution API.

T6.6C §4 uses build-embedded exact artifact allow-lists. No downloadable engine
execution or arbitrary file endpoint is specified. E must ship these bytes and
an explicitly reviewed compatibility allow-list in its own build.
"""

import base64
from dataclasses import dataclass
import hashlib

from app.authoritative_schemas import AuthoritativeProjections
from app.services.card_charge.registry import card_charge_policy_manifest
from isolated_sync.canonical import encode
from isolated_sync.finalization import schema_artifact
from isolated_sync.observation import engine_artifact, reject, versions


def release_bundle():
    artifacts = dict(raw_schema=schema_artifact(), projection_schema=encode(AuthoritativeProjections.model_json_schema()),
                     policy_registry=encode(card_charge_policy_manifest()), financial_engine=engine_artifact())
    return dict(packaging="money-note.isolated-release-artifacts/1", versions=versions(), artifacts={
        name: dict(sha256=hashlib.sha256(raw).hexdigest(), bytes=str(len(raw)), data_base64=base64.b64encode(raw).decode("ascii"))
        for name, raw in artifacts.items()})


@dataclass(frozen=True)
class ArtifactContract:
    versions_c1: bytes
    financial_engine: str

    @classmethod
    def current(cls):
        bundle = release_bundle()
        if any(bundle["versions"][key] != bundle["artifacts"][key]["sha256"] for key in ("raw_schema", "projection_schema", "policy_registry")):
            reject("UNSUPPORTED_CONTRACT")
        return cls(encode(bundle["versions"]), bundle["artifacts"]["financial_engine"]["sha256"])

    def verify(self, target):
        if encode(target["versions"]) != self.versions_c1 or target["context"]["financial_engine"] != self.financial_engine:
            reject("UNSUPPORTED_CONTRACT")

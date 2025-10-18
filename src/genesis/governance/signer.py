"""Signing utilities for module lineage."""
from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from genesis.metrics import genesis_signature_verifications_total


@dataclass
class SignatureRecord:
    module_version_id: str
    hash_hex: str
    signer: str
    verified: bool
    previous_hash: Optional[str] = None


class ModuleSigner:
    """Signs module contents and validates lineage."""

    def __init__(self, secret: bytes, on_verify: Optional[Callable[[bool], None]] = None) -> None:
        self.secret = secret
        self.on_verify = on_verify
        self._previous_hash: Optional[str] = None

    def sign(self, module_version_id: str, source_path: Path, metadata: str, signer: str) -> SignatureRecord:
        payload = self._compose_payload(source_path, metadata)
        digest = hmac.new(self.secret, payload, hashlib.sha256).hexdigest()
        record = SignatureRecord(
            module_version_id=module_version_id,
            hash_hex=digest,
            signer=signer,
            verified=True,
            previous_hash=self._previous_hash,
        )
        self._previous_hash = digest
        return record

    def verify(self, record: SignatureRecord, source_path: Path, metadata: str) -> bool:
        payload = self._compose_payload(source_path, metadata)
        expected = hmac.new(self.secret, payload, hashlib.sha256).hexdigest()
        success = hmac.compare_digest(expected, record.hash_hex)
        if record.previous_hash and self._previous_hash and record.previous_hash != self._previous_hash:
            success = False
        if self.on_verify:
            self.on_verify(success)
        else:
            status = "success" if success else "failed"
            genesis_signature_verifications_total.labels(status=status).inc()
        if success:
            self._previous_hash = record.hash_hex
        return success

    def _compose_payload(self, source_path: Path, metadata: str) -> bytes:
        contents = source_path.read_bytes()
        return contents + metadata.encode("utf-8")

"""Governance and compliance primitives."""
from .policy import PolicyEngine, PolicyRule, ResourceUsage
from .rbac import RBACManager, require_role
from .signer import ModuleSigner, SignatureRecord

try:  # pragma: no cover - optional FastAPI dependency
    from .compliance import ComplianceChecker
except ModuleNotFoundError as exc:  # pragma: no cover - optional FastAPI dependency
    if exc.name != "fastapi":
        raise
    ComplianceChecker = None  # type: ignore[assignment]

__all__ = [
    "PolicyEngine",
    "PolicyRule",
    "ResourceUsage",
    "ComplianceChecker",
    "RBACManager",
    "require_role",
    "ModuleSigner",
    "SignatureRecord",
]

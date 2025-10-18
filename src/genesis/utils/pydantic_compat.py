"""Compatibility layer providing minimal Pydantic-like primitives."""
from __future__ import annotations

from typing import Any, Callable, Dict

try:  # pragma: no cover - optional dependency path
    from pydantic import BaseModel as _BaseModel
    from pydantic import Field as _Field

    PYDANTIC_AVAILABLE = True
except Exception:  # pragma: no cover - fallback when pydantic is absent
    _BaseModel = None  # type: ignore[assignment]
    _Field = None  # type: ignore[assignment]
    PYDANTIC_AVAILABLE = False


if PYDANTIC_AVAILABLE:
    BaseModel = _BaseModel  # type: ignore[misc]

    def Field(*args: Any, **kwargs: Any) -> Any:
        return _Field(*args, **kwargs)

else:

    class _DefaultFactory:
        __slots__ = ("factory", "default")

        def __init__(self, factory: Callable[[], Any] | None, default: Any) -> None:
            self.factory = factory
            self.default = default

        def create(self) -> Any:
            if self.factory is not None:
                return self.factory()
            return self.default

    class BaseModel:  # type: ignore[override]
        """Very small subset mimicking Pydantic's BaseModel."""

        __field_defaults__: Dict[str, _DefaultFactory]

        def __init_subclass__(cls, **kwargs: Any) -> None:
            super().__init_subclass__(**kwargs)
            defaults: Dict[str, _DefaultFactory] = {}
            for name, value in cls.__dict__.items():
                if isinstance(value, _DefaultFactory):
                    defaults[name] = value
                    setattr(cls, name, value.create())
            cls.__field_defaults__ = defaults

        def __init__(self, **data: Any) -> None:
            for name, factory in getattr(self, "__field_defaults__", {}).items():
                if name not in data:
                    data[name] = factory.create()
            for key, value in data.items():
                setattr(self, key, value)

        def dict(self) -> dict[str, Any]:
            return dict(self.__dict__)

        class Config:
            frozen = False

    def Field(*, default: Any | None = None, default_factory: Callable[[], Any] | None = None) -> _DefaultFactory:  # type: ignore[misc]
        return _DefaultFactory(default_factory, default)


__all__ = ["BaseModel", "Field", "PYDANTIC_AVAILABLE"]

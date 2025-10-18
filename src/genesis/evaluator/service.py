"""Evaluator service orchestrating benchmark execution for Genesis modules."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Any, Dict, Iterable, Optional

try:  # pragma: no cover - optional dependency
    import yaml
except Exception:  # pragma: no cover - fallback to internal parser
    yaml = None

from genesis.metrics import genesis_eval_duration_seconds

from .autotest_client import AutoTestClient


@dataclass(slots=True)
class EvaluationResult:
    """Container representing the outcome of an evaluation run."""

    module: str
    version: str
    metrics: Dict[str, float]
    passed: bool
    metadata: Dict[str, Any]
    duration: float


class EvaluatorService:
    """Coordinates benchmark execution via the :class:`AutoTestClient`."""

    def __init__(
        self,
        autotest_client: AutoTestClient,
        benchmarks_path: Path | str = Path("benchmarks"),
    ) -> None:
        self._client = autotest_client
        self._benchmarks_path = Path(benchmarks_path)

    async def evaluate_module(
        self,
        module: str,
        version: str,
        benchmark_name: Optional[str] = None,
        overrides: Optional[Dict[str, Any]] = None,
    ) -> EvaluationResult:
        """Run the benchmark suite for ``module`` and return structured metrics."""

        config = self._load_benchmark_config(benchmark_name or module)
        payload = {**config, **(overrides or {})}

        start = perf_counter()
        autotest_result = await self._client.run_suite(module, payload)
        duration = perf_counter() - start

        metrics = dict(autotest_result.metrics)
        # Ensure latency is populated even if AutoTest Cloud omits it.
        metrics.setdefault("latency", duration)
        evaluation_result = EvaluationResult(
            module=module,
            version=version,
            metrics=metrics,
            passed=autotest_result.passed,
            metadata=autotest_result.metadata,
            duration=duration,
        )

        genesis_eval_duration_seconds.observe(duration)
        return evaluation_result

    def discover_modules(self) -> Iterable[str]:
        """Discover candidate module names from the ``modules`` directory."""

        modules_dir = self._benchmarks_path.parent / "src" / "genesis" / "modules"
        if not modules_dir.exists():
            return []
        return sorted({path.stem for path in modules_dir.glob("*.py") if path.is_file()})

    def _load_benchmark_config(self, benchmark_name: str) -> Dict[str, Any]:
        benchmark_file = self._benchmarks_path / f"{benchmark_name}.yaml"
        if not benchmark_file.exists():
            raise FileNotFoundError(f"Benchmark definition missing for {benchmark_name!r}")
        with benchmark_file.open("r", encoding="utf8") as handle:
            raw_text = handle.read()

        data = self._parse_yaml(raw_text)
        data.setdefault("name", benchmark_name)
        return data

    def _parse_yaml(self, raw_text: str) -> Dict[str, Any]:
        if yaml is not None:  # pragma: no branch - executed when dependency available
            loaded = yaml.safe_load(raw_text) or {}
            if not isinstance(loaded, dict):
                raise ValueError("Benchmark configuration must be a mapping")
            return loaded
        return _simple_yaml_loader(raw_text)


def _parse_scalar(value: str) -> Any:
    if value == "":
        return None
    lowered = value.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        return value


def _simple_yaml_loader(raw_text: str) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    current_list_key: Optional[str] = None
    current_item: Optional[Dict[str, Any]] = None

    lines = raw_text.splitlines()
    for line in lines:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip(" "))
        stripped = line.strip()

        if indent == 0:
            current_item = None
            current_list_key = None
            if ":" not in stripped:
                raise ValueError(f"Unable to parse line: {line}")
            key, _, remainder = stripped.partition(":")
            key = key.strip()
            remainder = remainder.strip()
            if remainder:
                result[key] = _parse_scalar(remainder)
            else:
                # Assume the next indented lines form a list.
                result[key] = []
                current_list_key = key
        elif indent == 2 and stripped.startswith("- "):
            if current_list_key is None:
                raise ValueError("List item defined without a parent key")
            item_body = stripped[2:].strip()
            current_item = {}
            if item_body:
                if ":" in item_body:
                    sub_key, _, sub_val = item_body.partition(":")
                    current_item[sub_key.strip()] = _parse_scalar(sub_val.strip())
                else:
                    current_item["value"] = _parse_scalar(item_body)
            result[current_list_key].append(current_item)
        elif indent >= 4:
            if current_item is None:
                raise ValueError("Unexpected indentation in benchmark configuration")
            if ":" not in stripped:
                raise ValueError(f"Unable to parse line: {line}")
            sub_key, _, sub_val = stripped.partition(":")
            current_item[sub_key.strip()] = _parse_scalar(sub_val.strip())
        else:
            raise ValueError(f"Unsupported indentation level in line: {line}")

    return result


__all__ = ["EvaluationResult", "EvaluatorService"]

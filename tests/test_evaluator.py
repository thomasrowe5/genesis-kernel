import asyncio
import pytest

from genesis.evaluator.autotest_client import AutoTestClient
from genesis.evaluator.service import EvaluatorService


def test_evaluator_returns_metrics(tmp_path):
    benchmarks_dir = tmp_path / "benchmarks"
    benchmarks_dir.mkdir()
    (benchmarks_dir / "demo.yaml").write_text(
        """
name: demo
expected_accuracy: 0.75
expected_latency: 0.2
expected_stability: 0.9
        """.strip()
    )

    service = EvaluatorService(AutoTestClient(), benchmarks_path=benchmarks_dir)
    result = asyncio.run(service.evaluate_module("demo", "v1"))
    assert result.passed is True
    assert result.metrics["accuracy"] == pytest.approx(0.75)
    assert result.metrics["latency"] == pytest.approx(0.2)
    assert result.metrics["stability"] == pytest.approx(0.9)


def test_discover_modules(tmp_path):
    root = tmp_path
    benchmarks_dir = root / "benchmarks"
    modules_dir = root / "src" / "genesis" / "modules"
    benchmarks_dir.mkdir()
    modules_dir.mkdir(parents=True)
    (benchmarks_dir / "demo.yaml").write_text("{}")
    (modules_dir / "alpha.py").write_text("# alpha module")
    (modules_dir / "beta.py").write_text("# beta module")

    service = EvaluatorService(AutoTestClient(), benchmarks_path=benchmarks_dir)
    discovered = list(service.discover_modules())
    assert discovered == ["alpha", "beta"]

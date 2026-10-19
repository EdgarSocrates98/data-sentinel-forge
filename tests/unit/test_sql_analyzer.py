"""Tests for the SQLGlot static SQL analyzer."""

from pathlib import Path

import pytest

from data_sentinel.analyzers import registry
from data_sentinel.analyzers.sql import SQL_CHECKS, SqlStaticAnalyzer
from data_sentinel.core.contracts import (
    ArtifactReference,
    DiagnosticRequest,
    ExecutionContext,
    FindingStatus,
    Platform,
    Severity,
    SourceType,
)
from data_sentinel.core.exceptions import InputValidationError
from data_sentinel.core.security import read_input_file

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "sql"
ANALYZER = SqlStaticAnalyzer()


def request_for(
    name: str,
    platform: Platform = Platform.SPARK,
    dialect: str | None = None,
) -> DiagnosticRequest:
    extra = {"sql_dialect": dialect} if dialect else {}
    return DiagnosticRequest(
        source_type=SourceType.SQL_QUERY,
        artifact_references=[ArtifactReference(uri=str(FIXTURES / name))],
        platform=platform,
        execution_context=ExecutionContext(extra=extra),
    )


def inputs_for(name: str) -> list:
    return [read_input_file(FIXTURES / name, max_file_bytes=1_000_000)]


def check_ids(result) -> set[str]:
    return {f.explanation.split(":")[0] for f in result.findings}


class TestChecks:
    @pytest.mark.parametrize(
        ("fixture", "check_id"),
        [
            ("select_star.sql", "SELECT * / projeção ampla"),
            ("join_no_predicate.sql", "JOIN sem predicado (produto cartesiano)"),
            ("implicit_join.sql", "Join implícito com vírgula"),
            ("union_query.sql", "UNION sem ALL"),
            ("order_by.sql", "ORDER BY sem LIMIT"),
            ("in_list.sql", "Lista IN literal grande"),
            ("select_star.sql", "Predicado não-sargable (função envolvendo coluna)"),
        ],
    )
    def test_check_fires(self, fixture: str, check_id: str) -> None:
        result = ANALYZER.analyze(request_for(fixture), inputs_for(fixture))
        assert check_id in check_ids(result), [f.explanation for f in result.findings]

    def test_clean_query_no_high_findings(self) -> None:
        result = ANALYZER.analyze(request_for("clean.sql"), inputs_for("clean.sql"))
        bad = [f for f in result.findings if f.severity in (Severity.HIGH, Severity.CRITICAL)]
        assert bad == [], [f.explanation for f in bad]

    def test_cross_join_confirmed_presence(self) -> None:
        result = ANALYZER.analyze(
            request_for("join_no_predicate.sql"), inputs_for("join_no_predicate.sql")
        )
        hit = next(
            f for f in result.findings if "produto cartesiano" in f.explanation
        )
        assert hit.status is FindingStatus.CONFIRMED
        assert hit.evidence_ids

    def test_heuristic_checks_capped_at_possible(self) -> None:
        for fixture in ("select_star.sql", "union_query.sql", "order_by.sql"):
            result = ANALYZER.analyze(request_for(fixture), inputs_for(fixture))
            for f in result.findings:
                if "cartesiano" not in f.explanation and "vírgula" not in f.explanation:
                    assert f.status in (
                        FindingStatus.POSSIBLE,
                        FindingStatus.UNKNOWN,
                    ), f.explanation

    def test_windowed_cte_does_not_crash(self) -> None:
        result = ANALYZER.analyze(
            request_for("windowed_cte.sql"), inputs_for("windowed_cte.sql")
        )
        queries = result.metadata["queries"]
        assert queries and queries[0]["cte_count"] >= 1

    def test_broken_sql_yields_limitation(self) -> None:
        result = ANALYZER.analyze(request_for("broken.sql"), inputs_for("broken.sql"))
        assert any("não pôde ser analisado" in lim for lim in result.limitations)
        assert all(f.status is FindingStatus.UNKNOWN for f in result.findings)

    def test_no_runtime_claims(self) -> None:
        result = ANALYZER.analyze(
            request_for("select_star.sql"), inputs_for("select_star.sql")
        )
        for f in result.findings:
            assert "será lento" not in f.explanation.lower()
        assert any("não observa execução física" in lim for lim in result.limitations)

    def test_static_limitation_always_present(self) -> None:
        result = ANALYZER.analyze(request_for("clean.sql"), inputs_for("clean.sql"))
        assert any("execução física" in lim for lim in result.limitations)


class TestDialects:
    def test_platform_maps_to_dialect(self) -> None:
        assert result_dialect(Platform.ATHENA) == "trino"
        assert result_dialect(Platform.SPARK) == "spark"

    def test_dialect_override_via_context(self) -> None:
        result = ANALYZER.analyze(
            request_for("clean.sql", dialect="trino"),
            inputs_for("clean.sql"),
        )
        assert result.metadata["dialect"] == "trino"

    def test_dialects_not_treated_as_equivalent(self, tmp_path: Path) -> None:
        spark_only = _write(
            "SELECT TRANSFORM(x) USING 'cat' FROM t;", tmp_path, "spark_only.sql"
        )
        f = read_input_file(
            spark_only, max_file_bytes=10000, allowed_roots=[tmp_path]
        )
        req = request_for("spark_only.sql", platform=Platform.ATHENA)
        r_trino = ANALYZER.analyze(req, [f])
        r_spark = ANALYZER.analyze(
            request_for("spark_only.sql", platform=Platform.SPARK), [f]
        )
        assert r_spark.metadata["dialect"] == "spark"
        assert r_trino.metadata["dialect"] == "trino"
        assert r_spark.metadata["dialect"] != r_trino.metadata["dialect"]


def result_dialect(platform: Platform) -> str:
    result = ANALYZER.analyze(
        request_for("clean.sql", platform=platform), inputs_for("clean.sql")
    )
    return result.metadata["dialect"]  # type: ignore[return-value]


def _write(text: str, d: Path, name: str) -> Path:
    p = d / name
    p.write_text(text)
    return p


class TestProtocol:
    def test_registered_for_sql_source(self) -> None:
        found = registry.for_source_type(SourceType.SQL_QUERY)
        assert any(a.analyzer_id == "sql-static-analyzer" for a in found)

    def test_rejects_log_input(self) -> None:
        request = DiagnosticRequest(
            source_type=SourceType.LOG,
            artifact_references=[ArtifactReference(uri="x.log")],
            platform=Platform.SPARK,
        )
        with pytest.raises(InputValidationError):
            ANALYZER.analyze(request, inputs_for("clean.sql"))

    def test_checks_are_data(self) -> None:
        assert len(SQL_CHECKS) >= 8
        assert all(c.title and c.rationale and c.suggestion for c in SQL_CHECKS)

    def test_evidence_provenance_static(self) -> None:
        result = ANALYZER.analyze(
            request_for("select_star.sql"), inputs_for("select_star.sql")
        )
        assert result.evidence
        assert all(
            ev.provenance.value == "static_inferred" for ev in result.evidence
        )

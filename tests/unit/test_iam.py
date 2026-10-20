"""ds-0025 — IAM/S3/KMS diagnostics."""

import json
from pathlib import Path

import pytest

from data_sentinel.analyzers.iam import (
    PolicyParseError,
    evaluate,
    parse_policy,
)
from data_sentinel.analyzers.protocol import InputFile
from data_sentinel.analyzers.registry import registry
from data_sentinel.core.contracts.entities import (
    ArtifactReference,
    DiagnosticRequest,
)
from data_sentinel.core.contracts.enums import (
    FindingStatus,
    Platform,
    SourceType,
)

FX = Path("fixtures/policies")


def _run(name: str):
    p = FX / name
    t = p.read_text(encoding="utf-8")
    req = DiagnosticRequest(
        source_type=SourceType.POLICY_DOC,
        artifact_references=[ArtifactReference(uri="file://pol")],
        platform=Platform.AWS_GLUE,
    )
    return registry.get("iam.policy").analyze(
        req, [InputFile(path=p, text=t, size_bytes=len(t.encode()))]
    )


class TestParser:
    def test_parse_statements(self):
        d = parse_policy((FX / "glue_role.json").read_text(encoding="utf-8"))
        assert len(d.statements) == 3
        assert d.statements[2].effect == "Deny"

    def test_malformed_raises(self):
        with pytest.raises(PolicyParseError):
            parse_policy((FX / "malformed.json").read_text(encoding="utf-8"))

    def test_principal_dict_flattened(self):
        d = parse_policy(json.dumps({"Statement": [{
            "Effect": "Allow", "Action": "sts:AssumeRole",
            "Principal": {"AWS": "arn:aws:iam::1:root", "Service": "glue.amazonaws.com"}}]}))
        assert "arn:aws:iam::1:root" in d.statements[0].principals
        assert "glue.amazonaws.com" in d.statements[0].principals


class TestEvaluate:
    def test_deny_wins_over_allow(self):
        env = json.loads((FX / "deny_wins.json").read_text(encoding="utf-8"))
        docs = [parse_policy(json.dumps(v), name=k)
                for k, v in env["policies"].items()]
        r = evaluate(docs, "s3:GetObject", "arn:aws:s3:::b/file")
        assert r.verdict == "denied"

    def test_allow_is_not_proof(self):
        d = parse_policy((FX / "glue_role.json").read_text(encoding="utf-8"))
        r = evaluate([d], "s3:GetObject", "arn:aws:s3:::data-bucket/x")
        assert r.verdict == "allowed"
        assert any("não prova" in x for x in r.reasons)

    def test_no_match_unknown(self):
        d = parse_policy((FX / "glue_role.json").read_text(encoding="utf-8"))
        r = evaluate([d], "s3:PutObject", "arn:aws:s3:::other/x")
        assert r.verdict == "unknown"

    def test_wildcard_action_matches(self):
        d = parse_policy((FX / "wildcard.json").read_text(encoding="utf-8"))
        r = evaluate([d], "anything:Do", "arn:aws:s3:::x")
        assert r.verdict == "allowed"


class TestAnalyzer:
    def test_registered(self):
        assert registry.get("iam.policy").analyzer_id == "iam.policy"

    def test_wildcard_policy_flagged(self):
        r = _run("wildcard.json")
        f = next(f for f in r.findings if "Action='*'" in f.explanation)
        assert f.status == FindingStatus.CONFIRMED

    def test_envelope_deny_wins_confirmed(self):
        r = _run("deny_wins.json")
        f = next(f for f in r.findings if "Deny explícito" in f.explanation)
        assert f.status == FindingStatus.CONFIRMED

    def test_cross_kms_two_keys_possible(self):
        r = _run("cross_kms.json")
        f = next(f for f in r.findings if "duas chaves" in f.explanation
                 or "KMS" in f.explanation)
        assert f.status == FindingStatus.POSSIBLE

    def test_cross_bucket_unknown(self):
        r = _run("cross_kms.json")
        f = next(f for f in r.findings if "Bucket cross-account" in f.explanation)
        assert f.status == FindingStatus.UNKNOWN

    def test_no_s3_put_allow_unknown_not_denied(self):
        r = _run("cross_kms.json")
        f = next(f for f in r.findings if "PutObject" in f.explanation)
        assert f.status == FindingStatus.UNKNOWN
        assert "hipótese" in f.explanation

    def test_malformed_limitation(self):
        r = _run("malformed.json")
        assert any("policy" in lim for lim in r.limitations)
        assert r.findings[0].status == FindingStatus.UNKNOWN

    def test_simulate_limitation_documented(self):
        r = _run("glue_role.json")
        assert any("SimulatePrincipalPolicy" in lim for lim in r.limitations)

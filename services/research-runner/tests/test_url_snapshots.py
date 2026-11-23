import json

from contracts import ThreatLevel
from research_runner.application.ablation_study import StudyConfig, run_study
from research_runner.domain.dataset import Sample
from research_runner.infrastructure.url_snapshots import (
    SnapshotDomainEvidenceClient,
    SnapshotInspectorClient,
    load_url_snapshots,
)


def _write_snapshot(tmp_path, payload: dict):
    path = tmp_path / "snapshots.json"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


async def test_snapshot_domain_client_returns_recorded_evidence_or_unknown(tmp_path):
    path = _write_snapshot(
        tmp_path,
        {
            "collected_at": "2026-11-22T20:00:00+00:00",
            "domains": {
                "banco-falso.xyz": {
                    "age_days": 5,
                    "certificate_age_days": 3,
                    "tranco_rank": None,
                }
            },
            "pages": {},
        },
    )
    store, sha = load_url_snapshots(str(path))
    client = SnapshotDomainEvidenceClient(store)

    known = await client.lookup("banco-falso.xyz")
    unknown = await client.lookup("desconhecido.example")

    assert len(sha) == 64
    assert known.age_days == 5
    assert known.certificate_age_days == 3
    assert known.tranco_rank is None
    assert unknown.age_days is None
    assert unknown.certificate_age_days is None
    assert unknown.tranco_rank is None


async def test_snapshot_inspector_returns_recorded_page_and_blocks_missing_urls(tmp_path):
    path = _write_snapshot(
        tmp_path,
        {
            "collected_at": "2026-11-22T20:00:00+00:00",
            "domains": {},
            "pages": {
                "https://golpe.example/login": {
                    "dom_text": "Informe sua senha e faca um pix urgente",
                    "final_url": "https://golpe.example/login",
                    "has_password_field": True,
                    "is_blocked": False,
                    "blocked_reason": None,
                }
            },
        },
    )
    store, _ = load_url_snapshots(str(path))
    inspector = SnapshotInspectorClient(store)

    found = await inspector.inspect("https://golpe.example/login")
    missing = await inspector.inspect("https://nao-gravada.example/")

    assert found.is_blocked is False
    assert found.has_password_field is True
    assert "pix urgente" in found.dom_text
    assert missing.is_blocked is True
    assert missing.blocked_reason == "not_in_snapshot"


async def test_study_with_url_snapshots_enables_stages_1_and_2_and_records_meta(tmp_path):
    samples = [
        Sample("s1", "texto", "me manda pix urgente conta bloqueada", "GOLPE", "real", "t"),
        Sample("s2", "texto", "taxa encomenda retida pague pix agora", "GOLPE", "real", "t"),
        Sample("s3", "texto", "oi mae troquei numero me faz pix", "GOLPE", "real", "t"),
        Sample("s4", "texto", "bom dia reuniao confirmada amanha", "SEGURO", "real", "t"),
        Sample("s5", "texto", "consulta medica agendada sexta", "SEGURO", "real", "t"),
        Sample("s6", "texto", "pedido entregue obrigado pela compra", "SEGURO", "real", "t"),
        Sample("u1", "url", "https://itau-atualizacao.xyz/pix", "GOLPE", "real", "t"),
        Sample("u2", "url", "https://caixa-resgate.xyz/pix", "GOLPE", "real", "t"),
        Sample("u3", "url", "https://correios-taxa.xyz/pix", "GOLPE", "real", "t"),
        Sample("u4", "url", "https://exemplo-legitimo.org/", "SEGURO", "real", "t"),
        Sample("u5", "url", "https://portal-legitimo.org/", "SEGURO", "real", "t"),
        Sample("u6", "url", "https://noticias-legitimo.org/", "SEGURO", "real", "t"),
    ]
    path = _write_snapshot(
        tmp_path,
        {
            "collected_at": "2026-11-22T20:00:00+00:00",
            "domains": {
                "itau-atualizacao.xyz": {"age_days": 4, "certificate_age_days": 2},
                "caixa-resgate.xyz": {"age_days": 4, "certificate_age_days": 2},
                "correios-taxa.xyz": {"age_days": 4, "certificate_age_days": 2},
                "exemplo-legitimo.org": {"age_days": 900, "tranco_rank": 5000},
                "portal-legitimo.org": {"age_days": 900, "tranco_rank": 5000},
                "noticias-legitimo.org": {"age_days": 900, "tranco_rank": 5000},
            },
            "pages": {
                "https://exemplo-legitimo.org/": {
                    "dom_text": "bom dia reuniao confirmada amanha",
                    "final_url": "https://exemplo-legitimo.org/",
                    "has_password_field": False,
                    "is_blocked": False,
                },
                "https://portal-legitimo.org/": {
                    "dom_text": "consulta medica agendada sexta",
                    "final_url": "https://portal-legitimo.org/",
                    "has_password_field": False,
                    "is_blocked": False,
                },
                "https://noticias-legitimo.org/": {
                    "dom_text": "pedido entregue obrigado pela compra",
                    "final_url": "https://noticias-legitimo.org/",
                    "has_password_field": False,
                    "is_blocked": False,
                },
            },
        },
    )
    store, sha = load_url_snapshots(str(path))
    config = StudyConfig(
        test_ratio=0.35,
        seed=42,
        url_snapshots=store,
        url_snapshots_path=str(path),
        url_snapshots_sha256=sha,
    )

    report = await run_study(samples, config)
    cascade = next(m for m in report["modes"] if m["mode"] == "cascade")

    assert report["meta"]["disabled_stages"] == ["visual_rag"]
    assert report["meta"]["url_snapshots"]["sha256"] == sha
    # With stage 1 domain age recorded, the young lookalike URL in test is caught as GOLPE.
    assert cascade["metrics"]["confusion_matrix"]["tp"] >= 1
    assert ThreatLevel.SCAM.value == "GOLPE"

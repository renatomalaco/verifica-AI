import pytest
from scan_orchestrator.domain.scan_input import ScanInput
from scan_orchestrator.domain.risk_score import RiskScore


def test_scan_input_empty_raises_value_error():
    with pytest.raises(ValueError):
        ScanInput(content="   ")


def test_scan_input_identifies_url_only():
    inp1 = ScanInput(content="https://itau-seguranca.com.br")
    assert inp1.is_url_only is True

    inp2 = ScanInput(content="www.banco-falso.xyz/login")
    assert inp2.is_url_only is True

    inp3 = ScanInput(content="Oi mãe, acesse https://site.com para ver o produto")
    assert inp3.is_url_only is False


def test_scan_input_identifies_embedded_links():
    inp1 = ScanInput(content="Oi mãe, acesse https://site.com para ver o produto")
    assert inp1.has_links is True

    inp2 = ScanInput(content="Veja em www.promocao.com/ganhe")
    assert inp2.has_links is True

    inp3 = ScanInput(content="Oi mãe, troquei de número, me faz um pix urgente")
    assert inp3.has_links is False


def test_scan_input_sha256():
    inp = ScanInput(content="Teste de mensagem")
    assert len(inp.sha256) == 64


def test_risk_score_invariants():
    score = RiskScore(value=0.85)
    assert score.value == 0.85

    with pytest.raises(ValueError):
        RiskScore(value=-0.01)

    with pytest.raises(ValueError):
        RiskScore(value=1.01)


def test_zero_width_characters_do_not_hide_a_link():
    scan = ScanInput(content="Acesse itau\u200b.com.br para regularizar")
    assert scan.has_links
    assert scan.extract_urls() == ["itau.com.br"]


def test_bare_domain_with_any_public_suffix_is_a_link():
    assert ScanInput(content="Resgate em caixa-premios.club hoje").has_links


def test_email_address_is_not_a_link():
    scan = ScanInput(content="Mande o comprovante para joao@exemplo.com")
    assert not scan.has_links
    assert scan.extract_urls() == []


def test_word_joined_by_a_dot_is_not_a_link():
    assert not ScanInput(content="Até logo.Obrigado pela atenção").has_links

import pytest
from contracts.url_utils import normalize_url, extract_domain


def test_normalize_url_lowercases_and_strips_fragments():
    url = "HTTPS://WWW.Exemplo.Com.BR:443/login?user=123#topo"
    normalized = normalize_url(url)
    assert normalized == "https://www.exemplo.com.br/login?user=123"


def test_normalize_url_strips_tracking_params():
    url = "https://loja.com/produto?id=10&utm_source=whatsapp&utm_medium=cpc&fbclid=abc123"
    normalized = normalize_url(url)
    assert normalized == "https://loja.com/produto?id=10"
    assert "utm_source" not in normalized
    assert "fbclid" not in normalized


def test_normalize_url_handles_punycode():
    # 'itаu' with Cyrillic 'а' (\u0430)
    cyrillic_url = "https://it\u0430u.com.br/seguranca"
    normalized = normalize_url(cyrillic_url)
    assert "xn--" in normalized  # Must convert to canonical punycode


def test_extract_domain():
    assert extract_domain("https://sub.empresa.com.br/teste") == "sub.empresa.com.br"
    assert extract_domain("http://BANCO.XYZ:8080/path") == "banco.xyz"

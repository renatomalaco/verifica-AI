from ai_gateway.domain.data_masker import mask_pii


def test_mask_cpf_formatted_and_unformatted():
    text1 = "Meu CPF é 123.456.789-00 para cadastro."
    assert "[CPF_MASCARADO]" in mask_pii(text1)
    assert "123.456.789-00" not in mask_pii(text1)

    text2 = "Transfira para o documento 12345678900 agora."
    assert "[CPF_MASCARADO]" in mask_pii(text2)
    assert "12345678900" not in mask_pii(text2)


def test_mask_cnpj():
    text = "Empresa registrada sob CNPJ 12.345.678/0001-90."
    masked = mask_pii(text)
    assert "[CNPJ_MASCARADO]" in masked
    assert "12.345.678/0001-90" not in masked


def test_mask_credit_card_with_luhn():
    valid_card = "Pague com o cartão 4000 0012 3456 7899 por favor."
    masked = mask_pii(valid_card)
    assert "[CARTAO_MASCARADO]" in masked
    assert "4000 0012 3456 7899" not in masked

    protocolo = "Protocolo de atendimento: 4532015000000001."
    assert "[CARTAO_MASCARADO]" not in mask_pii(protocolo)


def test_mask_pix_uuid():
    text = "Minha chave PIX aleatória é c1db20fe-d015-45ae-9b2d-55e12bb6390c."
    masked = mask_pii(text)
    assert "[PIX_MASCARADO]" in masked
    assert "c1db20fe-d015-45ae-9b2d-55e12bb6390c" not in masked


def test_mask_phone_brazil():
    text1 = "Me chame no whatsapp (11) 98765-4321 urgente."
    assert "[TELEFONE_MASCARADO]" in mask_pii(text1)
    assert "98765-4321" not in mask_pii(text1)

    text2 = "Ligue para +55 11 98765-4321."
    assert "[TELEFONE_MASCARADO]" in mask_pii(text2)


def test_mask_email():
    text = "Envie o comprovante para contato.financeiro@banco-falso.com.br."
    masked = mask_pii(text)
    assert "[EMAIL_MASCARADO]" in masked
    assert "contato.financeiro@banco-falso.com.br" not in masked


def test_mask_password_and_token():
    text = "Sua senha: SuperSecret123 e o token é eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozG66."
    masked = mask_pii(text)
    assert "[CHAVE_SENSIVEL]" in masked
    assert "SuperSecret123" not in masked
    assert "eyJhbGciOiJIUzI1Ni" not in masked


def test_preserve_currency_and_dates():
    text = "O valor cobrado é de R$ 1.250,50 no dia 15/08/2026."
    masked = mask_pii(text)
    assert "R$ 1.250,50" in masked
    assert "15/08/2026" in masked

import pytest

from ai_gateway.application.seed_brands import brand_folders, seed_references
from ai_gateway.infrastructure.fakes import FakeVisualEmbedder


class RecordingCatalog:
    def __init__(self) -> None:
        self.saved: list[tuple[str, str, int]] = []

    async def save_reference(self, brand: str, source: str, embedding: list[float]) -> None:
        self.saved.append((brand, source, len(embedding)))


def test_every_protected_brand_has_a_plain_folder_name():
    folders = brand_folders()
    assert folders["banco-do-brasil"] == "Banco do Brasil"
    assert folders["caixa-economica-federal"] == "Caixa Econômica Federal"
    assert folders["receita-federal-gov-br"] == "Receita Federal / Gov.br"


async def test_each_image_becomes_one_reference_of_its_brand(tmp_path):
    (tmp_path / "nubank").mkdir()
    (tmp_path / "nubank" / "logo.png").write_bytes(b"png")
    (tmp_path / "nubank" / "login.JPG").write_bytes(b"jpg")
    (tmp_path / "nubank" / "FONTES.md").write_text("onde e quando cada imagem foi obtida")
    catalog = RecordingCatalog()

    saved = await seed_references(tmp_path, FakeVisualEmbedder(dimension=768), catalog)

    assert saved == 2
    assert sorted(catalog.saved) == [("Nubank", "nubank/login.JPG", 768), ("Nubank", "nubank/logo.png", 768)]


async def test_a_folder_that_is_not_a_protected_brand_stops_the_seed(tmp_path):
    # Official domains come from the contract; a brand outside it could never be judged.
    (tmp_path / "banco-inventado").mkdir()
    (tmp_path / "banco-inventado" / "logo.png").write_bytes(b"png")

    with pytest.raises(ValueError, match="banco-inventado"):
        await seed_references(tmp_path, FakeVisualEmbedder(dimension=768), RecordingCatalog())

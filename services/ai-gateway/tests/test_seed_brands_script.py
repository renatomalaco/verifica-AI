import importlib.util
from pathlib import Path

from ai_gateway.settings import Settings

SCRIPT = Path(__file__).parents[3] / "scripts" / "seed_brands.py"


def load_script():
    spec = importlib.util.spec_from_file_location("seed_brands_script", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


async def test_the_seed_script_embeds_with_the_same_pinned_model_as_the_api(tmp_path, monkeypatch):
    script = load_script()
    built: dict[str, object] = {}

    # Same signature as SiglipEmbedder, so a missing argument fails here as it would for real.
    def embedder(model_name: str, revision: str, dimension: int) -> object:
        built.update(model_name=model_name, revision=revision, dimension=dimension)
        return object()

    async def seed(root: Path, embedder: object, store: object) -> int:
        return 1

    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://seed@localhost/verifica")
    monkeypatch.setattr(script, "SiglipEmbedder", embedder)
    monkeypatch.setattr(script, "seed_references", seed)

    assert await script.main(tmp_path) == 0
    settings = Settings()
    assert built == {
        "model_name": settings.SIGLIP_MODEL,
        "revision": settings.SIGLIP_REVISION,
        "dimension": settings.EMBEDDING_DIM,
    }

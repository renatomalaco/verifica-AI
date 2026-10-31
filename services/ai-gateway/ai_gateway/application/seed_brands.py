import base64
import re
import unicodedata
from pathlib import Path
from typing import Protocol

from contracts.protected_brands import PROTECTED_BRANDS
from ai_gateway.application.match_brand import VisualEmbedder

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}


class ReferenceStore(Protocol):
    async def save_reference(self, brand: str, source: str, embedding: list[float]) -> None:
        ...


def brand_folders() -> dict[str, str]:
    """Folder name expected under the seed root for each protected brand."""
    return {_slug(brand): brand for brand in PROTECTED_BRANDS}


async def seed_references(root: Path, embedder: VisualEmbedder, store: ReferenceStore) -> int:
    """Embeds every image in root/<brand-folder>/ and stores it; returns how many were saved."""
    folders = brand_folders()
    unknown = [d.name for d in root.iterdir() if d.is_dir() and d.name not in folders]
    if unknown:
        raise ValueError(f"not protected brands: {unknown}; expected folders: {sorted(folders)}")

    saved = 0
    for image in sorted(p for p in root.glob("*/*") if p.suffix.lower() in IMAGE_SUFFIXES):
        embedding = await embedder.embed_image(base64.b64encode(image.read_bytes()).decode())
        await store.save_reference(folders[image.parent.name], f"{image.parent.name}/{image.name}", embedding)
        saved += 1
    return saved


def _slug(name: str) -> str:
    ascii_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", ascii_name.lower()).strip("-")

"""Calibrates Visual RAG (SigLIP) thresholds using real brand references and real negative pages.

Computes cosine similarity distributions for:
  1. Same-brand leave-one-out pairs (positive signal)
  2. Cross-brand catalog pairs (brand confusion)
  3. Legitimate pages outside the catalog (false positive signal)
"""

import asyncio
import base64
from pathlib import Path

from ai_gateway.infrastructure.siglip_embedder import SiglipEmbedder
from ai_gateway.settings import Settings

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}


def _dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


async def _embed_file(embedder: SiglipEmbedder, path: Path) -> list[float]:
    b64 = base64.b64encode(path.read_bytes()).decode("ascii")
    return await embedder.embed_image(b64)


async def main() -> None:
    settings = Settings()
    embedder = SiglipEmbedder(
        model_name=settings.SIGLIP_MODEL,
        revision=settings.SIGLIP_REVISION,
        dimension=settings.EMBEDDING_DIM,
    )

    brands_dir = Path("data/brands")
    neg_dir = Path("data/brands_negatives")

    refs: list[tuple[str, str, list[float]]] = []
    for brand_folder in sorted(p for p in brands_dir.iterdir() if p.is_dir()):
        for img in sorted(brand_folder.iterdir()):
            if img.suffix.lower() not in IMAGE_EXTS:
                continue
            vec = await _embed_file(embedder, img)
            refs.append((brand_folder.name, img.name, vec))
    print(f"Embedded {len(refs)} brand references across {len({b for b, _, _ in refs})} brands.")

    # 1. Leave-one-out on brand references (same brand vs other brand)
    same_brand_best: list[float] = []
    cross_brand_best: list[tuple[float, str, str]] = []
    for i, (brand, name, vec) in enumerate(refs):
        same = [_dot(vec, v) for j, (b, _, v) in enumerate(refs) if j != i and b == brand]
        other = [(_dot(vec, v), b) for j, (b, _, v) in enumerate(refs) if b != brand]
        if same:
            same_brand_best.append(max(same))
        if other:
            best_score, best_brand = max(other, key=lambda x: x[0])
            cross_brand_best.append((best_score, f"{brand}/{name}", best_brand))

    # 2. Real legitimate pages outside the catalog
    neg_scores: list[tuple[float, float, str, str]] = []
    for img in sorted(neg_dir.iterdir()):
        if img.suffix.lower() not in IMAGE_EXTS:
            continue
        vec = await _embed_file(embedder, img)
        by_brand: dict[str, float] = {}
        for brand, _, ref_vec in refs:
            score = _dot(vec, ref_vec)
            if score > by_brand.get(brand, -1.0):
                by_brand[brand] = score
        ranked = sorted(by_brand.items(), key=lambda x: x[1], reverse=True)
        top1_brand, top1 = ranked[0]
        top2 = ranked[1][1] if len(ranked) > 1 else 0.0
        neg_scores.append((top1, top1 - top2, img.name, top1_brand))

    print("\n=== SAME-BRAND LEAVE-ONE-OUT (n=%d) ===" % len(same_brand_best))
    print(
        f"  min={min(same_brand_best):.4f}  median={sorted(same_brand_best)[len(same_brand_best)//2]:.4f}  "
        f"max={max(same_brand_best):.4f}"
    )

    cross_vals = [x[0] for x in cross_brand_best]
    print("\n=== CROSS-BRAND CONFUSION (n=%d) ===" % len(cross_vals))
    print(
        f"  min={min(cross_vals):.4f}  median={sorted(cross_vals)[len(cross_vals)//2]:.4f}  "
        f"max={max(cross_vals):.4f}"
    )
    for score, src, matched in sorted(cross_brand_best, reverse=True)[:5]:
        print(f"    {score:.4f}  {src} -> {matched}")

    print("\n=== EXTERNAL LEGITIMATE PAGES (n=%d) ===" % len(neg_scores))
    for top1, margin, name, brand in sorted(neg_scores, reverse=True):
        print(f"  {top1:.4f} (margin={margin:.4f})  {name:24s} -> {brand}")

    print("\n=== THRESHOLD SWEEP (false positives on external legit pages) ===")
    for th in (0.75, 0.80, 0.82, 0.85, 0.88, 0.90, 0.92):
        ext_fp = sum(1 for s, _, _, _ in neg_scores if s >= th)
        same_tp = sum(1 for s in same_brand_best if s >= th)
        print(
            f"  threshold={th:.2f}: same_brand_recall={same_tp}/{len(same_brand_best)} "
            f"({same_tp/len(same_brand_best):.0%})  external_FP={ext_fp}/{len(neg_scores)} "
            f"({ext_fp/len(neg_scores):.0%})"
        )


if __name__ == "__main__":
    asyncio.run(main())

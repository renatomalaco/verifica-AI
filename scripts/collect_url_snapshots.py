"""Collects frozen Stage 1 (RDAP, crt.sh) and Stage 2 (url-inspector) snapshots for test URLs.

Run with url-inspector behind the egress proxy (never browse phishing URLs directly on the host):
    uv run python scripts/collect_url_snapshots.py \
        --inspector-url http://127.0.0.1:8002 \
        --output data/snapshots/url_snapshots_2026-11-22.json
"""

import argparse
import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path

import httpx
from contracts import extract_domain, normalize_url
from research_runner.domain.dataset import Split, assign_splits
from research_runner.infrastructure.dataset_file import load_samples
from scan_orchestrator.domain.official_addresses import official_registrant
from scan_orchestrator.domain.scan_input import ScanInput
from scan_orchestrator.infrastructure.domain_evidence_client import CrtShClient, RdapClient


def _normalize(raw_url: str) -> tuple[str, str]:
    normalized = normalize_url(raw_url)
    return normalized, extract_domain(normalized).lower()


async def _collect_domain(
    sem: asyncio.Semaphore, rdap: RdapClient, crt: CrtShClient, domain: str
) -> tuple[str, dict]:
    async with sem:
        age, cert = await asyncio.gather(
            rdap.age_days(domain),
            crt.certificate_age_days(domain),
        )
        print(f"  [stage1] {domain}: age_days={age}, cert_age_days={cert}")
        return domain, {
            "age_days": age,
            "certificate_age_days": cert,
            "tranco_rank": None,
        }


async def _collect_page(
    sem: asyncio.Semaphore,
    client: httpx.AsyncClient,
    inspector_url: str,
    url: str,
    keep_screenshot: bool,
) -> tuple[str, dict]:
    async with sem:
        try:
            resp = await client.post(
                f"{inspector_url.rstrip('/')}/inspect",
                json={"url": url},
                timeout=35.0,
            )
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPError as exc:
            print(f"  [stage2] {url}: ERROR {exc}")
            return url, {
                "dom_text": "",
                "final_url": url,
                "screenshot_b64": None,
                "has_password_field": False,
                "is_blocked": True,
                "blocked_reason": "inspector_http_error",
            }
        if not keep_screenshot:
            data["screenshot_b64"] = None
        status = f"blocked({data.get('blocked_reason')})" if data.get("is_blocked") else "ok"
        print(f"  [stage2] {url}: {status}, dom_len={len(data.get('dom_text', ''))}")
        return url, {
            "dom_text": data.get("dom_text", ""),
            "final_url": data.get("final_url", url),
            "screenshot_b64": data.get("screenshot_b64"),
            "has_password_field": bool(data.get("has_password_field", False)),
            "is_blocked": bool(data.get("is_blocked", False)),
            "blocked_reason": data.get("blocked_reason"),
        }


async def run(args: argparse.Namespace) -> None:
    samples = load_samples(args.dataset)
    splits = assign_splits(samples, test_ratio=args.test_ratio, seed=args.seed)
    target_samples = (
        samples if args.all_samples else [s for s in samples if splits[s.id] is Split.TEST]
    )

    urls: list[str] = []
    domains: set[str] = set()
    for s in target_samples:
        for raw_url in ScanInput(content=s.content).extract_urls():
            norm, domain = _normalize(raw_url)
            if not domain:
                continue
            if norm not in urls:
                urls.append(norm)
            domains.add(domain)

    print(f"Collecting snapshots for {len(urls)} unique URLs across {len(domains)} domains...")
    sem = asyncio.Semaphore(4)
    rdap = RdapClient(timeout_seconds=6.0)
    crt = CrtShClient(timeout_seconds=8.0)

    domain_entries = dict(
        await asyncio.gather(*(_collect_domain(sem, rdap, crt, d) for d in sorted(domains)))
    )

    page_entries: dict[str, dict] = {}
    if args.inspector_url:
        # Skip official addresses already short-circuited at Stage 1.
        to_inspect = [u for u in urls if not official_registrant(_normalize(u)[1])]
        print(f"Inspecting {len(to_inspect)} non-official URLs via {args.inspector_url}...")
        page_sem = asyncio.Semaphore(2)
        async with httpx.AsyncClient() as client:
            results = await asyncio.gather(
                *(
                    _collect_page(page_sem, client, args.inspector_url, u, args.keep_screenshots)
                    for u in to_inspect
                )
            )
            page_entries = dict(results)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "collected_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "seed": args.seed,
        "test_ratio": args.test_ratio,
        "domains": domain_entries,
        "pages": page_entries,
    }
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] Saved {len(domain_entries)} domains and {len(page_entries)} pages to {out_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect frozen URL snapshots for ablation study.")
    parser.add_argument("--dataset", default=None)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--test-ratio", type=float, default=0.3)
    parser.add_argument("--all-samples", action="store_true")
    parser.add_argument("--inspector-url", default=None, help="URL of isolated url-inspector.")
    parser.add_argument("--keep-screenshots", action="store_true")
    parser.add_argument(
        "--output",
        default="data/snapshots/url_snapshots_2026-11-22.json",
    )
    asyncio.run(run(parser.parse_args()))


if __name__ == "__main__":
    main()

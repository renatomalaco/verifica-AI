import re
from pathlib import Path

ROOT = Path(__file__).parents[3]
DOCKERFILE = ROOT / "services" / "url-inspector" / "Dockerfile"


def _locked_playwright() -> str:
    lock = (ROOT / "uv.lock").read_text(encoding="utf-8")
    return re.search(r'name = "playwright"\nversion = "([^"]+)"', lock).group(1)


def test_the_image_runs_the_playwright_version_of_the_lock():
    # A newer Playwright than the base image's browsers left the driver hanging in production:
    # base image, installed package and tests must use one version.
    dockerfile = DOCKERFILE.read_text(encoding="utf-8")
    version = re.search(r"^ARG PLAYWRIGHT_VERSION=(\S+)$", dockerfile, re.M).group(1)

    assert version == _locked_playwright()
    assert "playwright/python:v${PLAYWRIGHT_VERSION}-" in dockerfile
    assert '"playwright==${PLAYWRIGHT_VERSION}"' in dockerfile

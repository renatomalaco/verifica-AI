from url_inspector.infrastructure.playwright_driver import browser_launch_args, capture_within_budget


def test_with_a_proxy_every_request_goes_through_it_including_loopback():
    args = browser_launch_args("golpe.example", "203.0.113.7", proxy_url="http://egress:3128")
    assert "--proxy-server=http://egress:3128" in args
    assert "--proxy-bypass-list=<-loopback>" in args
    assert not any(a.startswith("--host-resolver-rules") for a in args)


def test_without_a_proxy_only_the_first_host_is_pinned_for_local_development():
    args = browser_launch_args("golpe.example", "203.0.113.7", proxy_url="")
    assert "--host-resolver-rules=MAP golpe.example 203.0.113.7" in args
    assert not any(a.startswith("--proxy-server") for a in args)


async def test_screenshot_starts_at_quality_80_and_recompresses_until_it_fits():
    sizes = {80: 900_000, 70: 850_000, 60: 700_000}
    asked: list[int] = []

    async def capture(quality: int) -> bytes:
        asked.append(quality)
        return b"x" * sizes.get(quality, 100)

    shot = await capture_within_budget(capture, budget_bytes=800_000)

    assert asked == [80, 70, 60]
    assert len(shot) == 700_000


async def test_screenshot_that_never_fits_returns_the_smallest_attempt():
    async def capture(quality: int) -> bytes:
        return b"x" * (quality * 100_000)

    assert len(await capture_within_budget(capture, budget_bytes=1)) == 40 * 100_000

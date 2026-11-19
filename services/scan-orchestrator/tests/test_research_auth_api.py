from datetime import datetime, timedelta, timezone

import pytest
from httpx import ASGITransport, AsyncClient

from contracts import ResearchRole
from scan_orchestrator.api.dependencies import (
    get_login_store,
    get_research_account_repository,
    get_research_auth,
    get_settings,
)
from scan_orchestrator.api.main import app
from scan_orchestrator.api.research_guard import ACCESS_COOKIE, REFRESH_COOKIE
from scan_orchestrator.infrastructure.access_tokens import generate_key_pair
from scan_orchestrator.infrastructure.quota_store import InMemoryQuotaStore
from scan_orchestrator.infrastructure.research_account_repository import (
    InMemoryResearchAccountRepository,
)
from scan_orchestrator.settings import Settings

PRIVATE_KEY, PUBLIC_KEY = generate_key_pair()
ORIGIN = "https://verifica.test"
PASSWORD = "senha-da-banca-2026"


def settings(**overrides) -> Settings:
    fields = {
        "AUTH_JWT_PRIVATE_KEY": PRIVATE_KEY,
        "AUTH_JWT_PUBLIC_KEY": PUBLIC_KEY,
        "AUTH_ALLOWED_ORIGINS": [ORIGIN],
        "LOGIN_ACCOUNT_LIMIT": 3,
    }
    return Settings(_env_file=None, **(fields | overrides))


@pytest.fixture
async def client():
    repo = InMemoryResearchAccountRepository()
    store = InMemoryQuotaStore()
    app.dependency_overrides[get_settings] = lambda: settings()
    app.dependency_overrides[get_research_account_repository] = lambda: repo
    app.dependency_overrides[get_login_store] = lambda: store
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="https://test", headers={"Origin": ORIGIN}
    ) as http:
        yield http
    for dependency in (get_research_account_repository, get_login_store):
        app.dependency_overrides.pop(dependency, None)


async def create_account(
    email: str, role: ResearchRole, expires_at: datetime | None = None
) -> None:
    auth = get_research_auth(
        settings=settings(),
        repository=app.dependency_overrides[get_research_account_repository](),
        store=app.dependency_overrides[get_login_store](),
    )
    await auth.accept_invite(await auth.invite(email, role, expires_at=expires_at), PASSWORD)


async def refresh_with(client: AsyncClient, refresh_token: str):
    """Presents a specific refresh token, as a second device holding a copy would."""
    client.cookies.clear()
    client.cookies.set(REFRESH_COOKIE, refresh_token)
    return await client.post("/api/v1/auth/refresh")


async def login(client: AsyncClient, email: str = "banca@exemplo.com", password: str = PASSWORD):
    return await client.post("/api/v1/auth/login", json={"email": email, "password": password})


async def test_metrics_are_not_served_publicly_even_to_a_researcher(client):
    # Prometheus scrapes the OTel Collector on the internal network (R6), never the orchestrator.
    await create_account("banca@exemplo.com", ResearchRole.RESEARCHER)
    await login(client)

    assert (await client.get("/metrics")).status_code == 404


async def test_login_returns_the_user_and_sets_hardened_cookies(client):
    await create_account("banca@exemplo.com", ResearchRole.RESEARCHER)

    res = await login(client, email="  Banca@Exemplo.com")

    assert res.status_code == 200
    assert res.json() == {"email": "banca@exemplo.com", "role": "researcher", "expires_at": None}
    cookies = {c.split("=", 1)[0]: c.lower() for c in res.headers.get_list("set-cookie")}
    for name in (ACCESS_COOKIE, REFRESH_COOKIE):
        assert "httponly" in cookies[name]
        assert "secure" in cookies[name]
        assert "samesite=strict" in cookies[name]
    assert "path=/api/v1/auth/refresh" in cookies[REFRESH_COOKIE]


@pytest.mark.parametrize(
    "email, password",
    [("banca@exemplo.com", "senha-errada-qualquer"), ("ninguem@exemplo.com", PASSWORD)],
)
async def test_failed_logins_look_identical(client, email, password):
    await create_account("banca@exemplo.com", ResearchRole.RESEARCHER)

    res = await login(client, email=email, password=password)

    assert res.status_code == 401
    assert res.json() == {"detail": "invalid_credentials"}


async def test_an_expired_account_cannot_sign_in(client):
    await create_account(
        "banca@exemplo.com",
        ResearchRole.RESEARCHER,
        expires_at=datetime.now(timezone.utc) - timedelta(seconds=1),
    )

    assert (await login(client)).status_code == 401


async def test_too_many_attempts_answer_429_with_retry_after(client):
    for _ in range(3):
        await login(client, password="senha-errada-qualquer")

    res = await login(client)

    assert res.status_code == 429
    assert res.headers["retry-after"] == "900"


@pytest.mark.parametrize("origin", ["https://site-malicioso.test", None])
async def test_posts_from_another_origin_are_refused(client, origin):
    await create_account("banca@exemplo.com", ResearchRole.RESEARCHER)
    headers = {"Origin": origin} if origin else {}
    if origin is None:
        client.headers.pop("Origin")

    res = await client.post(
        "/api/v1/auth/login",
        json={"email": "banca@exemplo.com", "password": PASSWORD},
        headers=headers,
    )

    assert res.status_code == 403


async def test_refresh_rotates_the_cookies(client):
    await create_account("banca@exemplo.com", ResearchRole.RESEARCHER)
    await login(client)
    old_refresh = client.cookies.get(REFRESH_COOKIE)

    res = await client.post("/api/v1/auth/refresh")

    assert res.status_code == 200
    assert res.json()["email"] == "banca@exemplo.com"
    assert client.cookies.get(REFRESH_COOKIE) != old_refresh


async def test_the_current_refresh_token_is_accepted_when_presented(client):
    await create_account("banca@exemplo.com", ResearchRole.RESEARCHER)
    await login(client)

    assert (await refresh_with(client, client.cookies.get(REFRESH_COOKIE))).status_code == 200


async def test_a_reused_refresh_revokes_the_session(client):
    await create_account("banca@exemplo.com", ResearchRole.RESEARCHER)
    await login(client)
    stolen = client.cookies.get(REFRESH_COOKIE)
    await client.post("/api/v1/auth/refresh")
    legit = client.cookies.get(REFRESH_COOKIE)

    reused = await refresh_with(client, stolen)
    after = await refresh_with(client, legit)

    assert reused.status_code == 401
    assert after.status_code == 401


async def test_logout_clears_the_cookies_and_ends_the_session(client):
    await create_account("banca@exemplo.com", ResearchRole.RESEARCHER)
    await login(client)
    refresh = client.cookies.get(REFRESH_COOKIE)

    res = await client.delete("/api/v1/auth/refresh")

    assert res.status_code == 204
    assert client.cookies.get(ACCESS_COOKIE) is None
    assert (await refresh_with(client, refresh)).status_code == 401


async def test_me_tells_who_is_signed_in(client):
    assert (await client.get("/api/v1/auth/me")).status_code == 401

    await create_account("admin@exemplo.com", ResearchRole.ADMIN)
    await login(client, email="admin@exemplo.com")

    assert (await client.get("/api/v1/auth/me")).json()["role"] == "admin"


async def test_accepting_an_invite_sets_the_password(client):
    auth = get_research_auth(
        settings=settings(),
        repository=app.dependency_overrides[get_research_account_repository](),
        store=app.dependency_overrides[get_login_store](),
    )
    token = await auth.invite("banca@exemplo.com", ResearchRole.RESEARCHER)

    short = await client.post(
        "/api/v1/auth/invites/accept", json={"token": token, "password": "curta"}
    )
    accepted = await client.post(
        "/api/v1/auth/invites/accept", json={"token": token, "password": PASSWORD}
    )
    again = await client.post(
        "/api/v1/auth/invites/accept", json={"token": token, "password": PASSWORD}
    )

    assert short.status_code == 422 and short.json() == {"detail": "password_too_short"}
    assert accepted.status_code == 204
    assert again.status_code == 400 and again.json() == {"detail": "invite_invalid"}
    assert (await login(client)).status_code == 200


async def test_without_the_signing_key_login_is_unavailable(client):
    app.dependency_overrides[get_settings] = lambda: settings(AUTH_JWT_PRIVATE_KEY="")

    assert (await login(client)).status_code == 503


def test_allowed_origins_come_comma_separated_from_the_environment(monkeypatch):
    # JSON lists lose their quotes in some .env readers; a plain comma list survives everywhere.
    monkeypatch.setenv("AUTH_ALLOWED_ORIGINS", "https://verifica.ai, https://www.verifica.ai")

    assert Settings(_env_file=None).AUTH_ALLOWED_ORIGINS == [
        "https://verifica.ai",
        "https://www.verifica.ai",
    ]


# --- Admin screen: list accounts, create invite links and block access. ---

ACCOUNTS = "/api/v1/auth/accounts"
INVITES = "/api/v1/auth/invites"
DISABLE = "/api/v1/auth/accounts/disable"


async def sign_in_as_admin(client) -> None:
    await create_account("admin@exemplo.com", ResearchRole.ADMIN)
    await login(client, email="admin@exemplo.com")


async def test_the_admin_lists_every_account_with_its_status(client):
    await sign_in_as_admin(client)
    await client.post(INVITES, json={"email": "banca@exemplo.com"})

    response = await client.get(ACCOUNTS)

    assert response.status_code == 200
    assert response.json() == [
        {"email": "admin@exemplo.com", "role": "admin", "expires_at": None, "status": "active"},
        {
            "email": "banca@exemplo.com",
            "role": "researcher",
            "expires_at": None,
            "status": "invited",
        },
    ]


async def test_an_invite_returns_a_one_time_link_that_sets_the_password(client):
    await sign_in_as_admin(client)

    response = await client.post(
        INVITES, json={"email": "Banca@Exemplo.com", "expires_on": "2026-12-20"}
    )

    assert response.status_code == 201
    url = response.json()["url"]
    assert url.startswith("http://localhost:5173/pesquisa/convite#token=")
    token = url.split("#token=")[1]
    accepted = await client.post(
        "/api/v1/auth/invites/accept", json={"token": token, "password": PASSWORD}
    )
    assert accepted.status_code == 204
    accounts = (await client.get(ACCOUNTS)).json()
    banca = next(a for a in accounts if a["email"] == "banca@exemplo.com")
    # Midnight after the last day, in Brasília.
    assert datetime.fromisoformat(banca["expires_at"]) == datetime(
        2026, 12, 21, 3, 0, tzinfo=timezone.utc
    )


async def test_the_admin_blocks_another_account(client):
    await create_account("banca@exemplo.com", ResearchRole.RESEARCHER)
    await sign_in_as_admin(client)

    blocked = await client.post(DISABLE, json={"email": "banca@exemplo.com"})
    unknown = await client.post(DISABLE, json={"email": "ninguem@exemplo.com"})

    assert blocked.status_code == 204
    assert unknown.status_code == 404 and unknown.json() == {"detail": "account_not_found"}
    assert (await login(client, email="banca@exemplo.com")).status_code == 401


async def test_the_admin_cannot_block_their_own_account(client):
    await sign_in_as_admin(client)

    response = await client.post(DISABLE, json={"email": "admin@exemplo.com"})

    assert response.status_code == 409 and response.json() == {"detail": "cannot_disable_self"}


@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        ("get", ACCOUNTS, None),
        ("post", INVITES, {"email": "outra@exemplo.com"}),
        ("post", DISABLE, {"email": "admin@exemplo.com"}),
    ],
)
async def test_a_researcher_cannot_manage_accounts(client, method, path, body):
    await create_account("banca@exemplo.com", ResearchRole.RESEARCHER)
    await login(client)

    kwargs = {"json": body} if body else {}
    response = await getattr(client, method)(path, **kwargs)

    assert response.status_code == 403 and response.json() == {"detail": "admin_only"}


async def test_without_signing_in_the_accounts_stay_hidden(client):
    assert (await client.get(ACCOUNTS)).status_code == 401


async def test_an_invite_from_another_origin_is_refused(client):
    await sign_in_as_admin(client)

    response = await client.post(
        INVITES, json={"email": "outra@exemplo.com"}, headers={"Origin": "https://evil.test"}
    )

    assert response.status_code == 403

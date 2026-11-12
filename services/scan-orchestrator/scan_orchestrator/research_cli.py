"""Operator CLI for research accounts (R5a). There is no public sign-up: every account starts here.

python -m scan_orchestrator.research_cli keygen
python -m scan_orchestrator.research_cli invite --email banca@exemplo.com --expires-on 2026-12-20
python -m scan_orchestrator.research_cli invite --email autor@exemplo.com --role admin
python -m scan_orchestrator.research_cli disable --email banca@exemplo.com
"""

import argparse
import asyncio
import sys
from datetime import date, datetime, time, timedelta, timezone

from contracts import ResearchRole
from scan_orchestrator.api.dependencies import (
    get_login_store,
    get_research_account_repository,
    get_research_auth,
)
from scan_orchestrator.application.research_auth import ResearchAuth
from scan_orchestrator.infrastructure.access_tokens import generate_key_pair
from scan_orchestrator.settings import Settings

BRASILIA = timezone(timedelta(hours=-3))


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="research_cli")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("keygen", help="print a new Ed25519 key pair as .env lines")
    invite = commands.add_parser(
        "invite", help="create or renew an account and print its one-time link"
    )
    invite.add_argument("--email", required=True)
    invite.add_argument(
        "--role", choices=[r.value for r in ResearchRole], default=ResearchRole.RESEARCHER.value
    )
    invite.add_argument(
        "--expires-on", type=date.fromisoformat, help="last day of access (YYYY-MM-DD, Brasília)"
    )
    disable = commands.add_parser("disable", help="block an account and end its sessions")
    disable.add_argument("--email", required=True)
    return parser.parse_args(argv)


def _end_of_day(day: date) -> datetime:
    return datetime.combine(day + timedelta(days=1), time(0), tzinfo=BRASILIA).astimezone(
        timezone.utc
    )


async def run(args: argparse.Namespace, auth: ResearchAuth | None, base_url: str) -> str:
    if args.command == "keygen":
        private, public = generate_key_pair()
        return f"AUTH_JWT_PRIVATE_KEY={private}\nAUTH_JWT_PUBLIC_KEY={public}"
    if args.command == "invite":
        expires_at = _end_of_day(args.expires_on) if args.expires_on else None
        token = await auth.invite(args.email, ResearchRole(args.role), expires_at=expires_at)
        # After "#": the token never reaches server logs or Referer headers.
        return (
            f"Invite link (valid for 48 h, single use):\n{base_url}/pesquisa/convite#token={token}"
        )
    blocked = await auth.disable(args.email)
    return f"{args.email}: blocked" if blocked else f"{args.email}: not found"


def main(argv: list[str]) -> None:
    args = parse_args(argv)
    settings = Settings()
    auth = None
    if args.command != "keygen":
        if not settings.DATABASE_URL:
            sys.exit("DATABASE_URL is not set: accounts must be stored in Postgres.")
        if not settings.AUTH_JWT_PRIVATE_KEY:
            sys.exit("AUTH_JWT_PRIVATE_KEY is not set: run the keygen command first.")
        auth = get_research_auth(
            settings=settings,
            repository=get_research_account_repository(settings),
            store=get_login_store(settings),
        )
    print(asyncio.run(run(args, auth=auth, base_url=settings.PUBLIC_BASE_URL)))


if __name__ == "__main__":
    main(sys.argv[1:])

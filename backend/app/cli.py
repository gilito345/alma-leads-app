"""Admin commands.

    python -m app.cli create-user --email jane@firm.com --name "Jane Doe"

Creates the Supabase Auth identity and the matching attorney record. The password is prompted
for (or read from --password / the CREATE_USER_PASSWORD env var for scripted setups).
"""

import argparse
import getpass
import os
import sys

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.security import TokenVerifier
from app.db.session import get_sessionmaker
from app.services.auth import AuthService
from app.services.supabase_auth import SupabaseAuthClient


def create_user(args: argparse.Namespace) -> int:
    password = args.password or os.environ.get("CREATE_USER_PASSWORD")
    if not password:
        password = getpass.getpass("Password (min 12 characters): ")
        if password != getpass.getpass("Repeat password: "):
            print("Passwords don't match", file=sys.stderr)
            return 1

    settings = get_settings()
    with get_sessionmaker()() as db:
        auth = AuthService(
            db, settings, SupabaseAuthClient.from_settings(settings), TokenVerifier(settings)
        )
        try:
            user = auth.create_user(args.email, args.name, password)
        except AppError as exc:
            print(exc.message, file=sys.stderr)
            return 1
    print(f"Created user {user.email} ({user.id})")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    commands = parser.add_subparsers(dest="command", required=True)

    create = commands.add_parser("create-user", help="Create an attorney account")
    create.add_argument("--email", required=True)
    create.add_argument("--name", required=True)
    create.add_argument("--password", help="Omit to be prompted (recommended)")
    create.set_defaults(func=create_user)

    args = parser.parse_args(argv)
    result: int = args.func(args)
    return result


if __name__ == "__main__":
    sys.exit(main())

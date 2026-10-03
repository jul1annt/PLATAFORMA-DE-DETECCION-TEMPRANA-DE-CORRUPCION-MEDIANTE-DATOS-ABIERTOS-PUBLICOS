"""Create the initial administrator from a trusted terminal.

Run from Backend after applying migrations:
    python scripts/create_first_admin.py --username admin --email admin@example.com
The password is requested without echoing it.
"""
import argparse
from getpass import getpass
from pathlib import Path
import sys
from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.database import SessionLocal
from modules.auth.dto.request import CreateAdminRequest
from modules.auth.repository.AuthRepository import AuthRepository
from modules.auth.service.AuthService import AuthService


def _create_first_admin_locked(db, data: CreateAdminRequest):
    if AuthRepository(db).exists_any_admin():
        raise SystemExit("An administrator already exists; use the authenticated API")
    return AuthService(db).create_admin(data)


def create_first_admin(db, data: CreateAdminRequest):
    """Serialize and create the only bootstrap administrator."""
    db.execute(text("SELECT pg_advisory_xact_lock(:lock_id)"), {"lock_id": 74101})
    return _create_first_admin_locked(db, data)


def main() -> int:
    parser = argparse.ArgumentParser(description="Create the first administrator")
    parser.add_argument("--username", required=True)
    parser.add_argument("--email", required=True)
    args = parser.parse_args()
    password = getpass("Password (minimum 12 characters): ")
    confirmation = getpass("Confirm password: ")
    if password != confirmation:
        raise SystemExit("Passwords do not match")

    db = SessionLocal()
    try:
        data = CreateAdminRequest(username=args.username, email=args.email, password=password)
        created = create_first_admin(db, data)
        print(f"Administrator created: {created.username}")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())

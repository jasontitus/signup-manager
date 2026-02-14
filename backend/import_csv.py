#!/usr/bin/env python3
"""
CSV Import Script for Signup Manager

Usage:
    python import_csv.py <csv_file> [--vetted] [--user-id USER_ID]

Arguments:
    csv_file: Path to the CSV file to import
    --vetted: Mark all imported records as VETTED (default: PENDING)
    --user-id: User ID to assign as the vetter (optional, only used with --vetted)

Example:
    python import_csv.py example.csv --vetted --user-id 1
"""

import argparse
import csv
import getpass
import sys
from datetime import datetime
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from app.database import SessionLocal, engine
from app.models.member import Member, MemberStatus
from app.models.audit_log import AuditLog
from app.services.encryption import encryption_service
from app.services.blind_index import generate_blind_index
from app.vault import vault_manager
from app.config import settings, load_secrets_from_vault
from sqlalchemy.orm import Session


def unlock_vault():
    """Unlock the vault interactively, or skip if encryption is already configured."""
    if settings.ENCRYPTION_KEY:
        encryption_service.initialize(settings.ENCRYPTION_KEY)
        return

    if not vault_manager.vault_exists():
        print("Error: No .vault file found and no ENCRYPTION_KEY in environment.")
        sys.exit(1)

    password = getpass.getpass("Master password: ")
    if not vault_manager.unlock(password):
        print("Error: Invalid master password.")
        sys.exit(1)

    load_secrets_from_vault(vault_manager.secrets)
    encryption_service.initialize(settings.ENCRYPTION_KEY)


def parse_name(full_name: str) -> tuple[str, str]:
    """
    Parse full name into first and last name.
    Assumes format: "FirstName LastName" or "FirstName MiddleName LastName"
    """
    parts = full_name.strip().split()
    if len(parts) == 0:
        return "", ""
    elif len(parts) == 1:
        return parts[0], ""
    else:
        # First part is first name, rest is last name
        return parts[0], " ".join(parts[1:])


def import_csv(
    csv_file: str,
    is_vetted: bool = False,
    vetter_id: int | None = None
) -> dict:
    """
    Import members from a CSV file.

    Args:
        csv_file: Path to the CSV file
        is_vetted: If True, mark records as VETTED, otherwise PENDING
        vetter_id: User ID to assign as vetter (optional)

    Returns:
        Dictionary with import statistics
    """
    stats = {
        "total": 0,
        "success": 0,
        "skipped": 0,
        "errors": []
    }

    db: Session = SessionLocal()

    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)

            for row_num, row in enumerate(reader, start=2):  # Start at 2 (1 is header)
                stats["total"] += 1

                try:
                    # Parse name
                    full_name = row.get("Name", "").strip()
                    first_name, last_name = parse_name(full_name)

                    if not first_name and not last_name:
                        stats["skipped"] += 1
                        stats["errors"].append(f"Row {row_num}: Empty name field")
                        continue

                    # Extract fields
                    street_address = row.get("Street address", "").strip()
                    city = row.get("City", "").strip()
                    zip_code = row.get("Zip code", "").strip()
                    phone_number = row.get("Phone number", "").strip()
                    email = row.get("Email address (for newsletter)", "").strip()

                    # Check if email already exists (using blind index)
                    if email:
                        blind_index = generate_blind_index(email)
                        existing = db.query(Member).filter(
                            Member.email_blind_index == blind_index
                        ).first()

                        if existing:
                            stats["skipped"] += 1
                            stats["errors"].append(
                                f"Row {row_num}: Email already exists (Member ID: {existing.id})"
                            )
                            continue

                    # Build custom fields dictionary
                    custom_fields = {}

                    if row.get("Where did you learn about IPA+?"):
                        custom_fields["where_learn"] = row["Where did you learn about IPA+?"].strip()

                    if row.get("What personal talent, skill, experience, or superpower do you bring to the group? We believe everyone has a superpower!"):
                        custom_fields["superpower"] = row["What personal talent, skill, experience, or superpower do you bring to the group? We believe everyone has a superpower!"].strip()

                    if row.get("What is your occupational background? Feel free to share your LinkedIn if you like. This helps us connect people to each other and to understand the skills and experience in the group."):
                        custom_fields["occupational_background"] = row["What is your occupational background? Feel free to share your LinkedIn if you like. This helps us connect people to each other and to understand the skills and experience in the group."].strip()

                    if row.get("Do you know someone who is a member of IPA+? If so, who?"):
                        custom_fields["know_member"] = row["Do you know someone who is a member of IPA+? If so, who?"].strip()

                    if row.get("What impact do you hope to have by joining IPA+? (If you don't know, that's OK!)"):
                        custom_fields["hoped_impact"] = row["What impact do you hope to have by joining IPA+? (If you don't know, that's OK!)"].strip()

                    # Add timestamp if available
                    if row.get("Timestamp"):
                        custom_fields["original_timestamp"] = row["Timestamp"].strip()

                    # Determine status
                    status = MemberStatus.VETTED if is_vetted else MemberStatus.PENDING

                    # Create member with non-hybrid fields only
                    member = Member(
                        status=status,
                        assigned_vetter_id=vetter_id if is_vetted and vetter_id else None
                    )

                    # Set encrypted fields via hybrid properties
                    member.first_name = first_name
                    member.last_name = last_name
                    member.city = city
                    member.zip_code = zip_code
                    member.street_address = street_address
                    member.phone_number = phone_number
                    member.email = email  # This also sets the blind index
                    member.custom_fields = custom_fields

                    db.add(member)
                    db.flush()  # Get the member ID

                    # Create audit log entry (only if user_id is provided)
                    if vetter_id:
                        audit = AuditLog(
                            user_id=vetter_id,
                            member_id=member.id,
                            action="CSV Import",
                            details=f"Imported from {Path(csv_file).name} as {status.value}"
                        )
                        db.add(audit)

                    stats["success"] += 1

                except Exception as e:
                    stats["skipped"] += 1
                    stats["errors"].append(f"Row {row_num}: {str(e)}")
                    continue

        # Commit all changes
        db.commit()

    except Exception as e:
        db.rollback()
        stats["errors"].append(f"Fatal error: {str(e)}")
    finally:
        db.close()

    return stats


def main():
    parser = argparse.ArgumentParser(
        description="Import members from CSV file into Signup Manager database"
    )
    parser.add_argument(
        "csv_file",
        help="Path to the CSV file to import"
    )
    parser.add_argument(
        "--vetted",
        action="store_true",
        help="Mark all imported records as VETTED (default: PENDING)"
    )
    parser.add_argument(
        "--user-id",
        type=int,
        help="User ID to assign as the vetter (optional, only used with --vetted)"
    )

    args = parser.parse_args()

    # Unlock vault / initialize encryption
    unlock_vault()

    # Check if file exists
    if not Path(args.csv_file).exists():
        print(f"Error: File not found: {args.csv_file}")
        sys.exit(1)

    # Run import
    print(f"Importing from: {args.csv_file}")
    print(f"Status: {'VETTED' if args.vetted else 'PENDING'}")
    if args.user_id:
        print(f"Assigned vetter ID: {args.user_id}")
    print()

    stats = import_csv(args.csv_file, args.vetted, args.user_id)

    # Print results
    print("\n" + "="*50)
    print("Import Complete")
    print("="*50)
    print(f"Total rows processed: {stats['total']}")
    print(f"Successfully imported: {stats['success']}")
    print(f"Skipped/Errors: {stats['skipped']}")

    if stats["errors"]:
        print("\nErrors/Warnings:")
        for error in stats["errors"]:
            print(f"  - {error}")

    sys.exit(0 if stats["skipped"] == 0 else 1)


if __name__ == "__main__":
    main()

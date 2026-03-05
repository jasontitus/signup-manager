#!/usr/bin/env python3
"""
CSV Import Script for Signup Manager

Usage:
    python import_csv.py <csv_file> [--vetted] [--user-id USER_ID] [--match-emails]

Arguments:
    csv_file: Path to the CSV file to import
    --vetted: Mark all imported records as VETTED (default: auto-detect from Decision column)
    --user-id: User ID to assign as the vetter (optional, only used with --vetted)
    --match-emails: Use email-only duplicate detection instead of name+phone

Example:
    python import_csv.py example.csv --vetted --user-id 1
    python import_csv.py example.csv --match-emails
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


def normalize_phone(phone: str) -> str:
    """Strip phone to digits only for comparison."""
    import re
    return re.sub(r'\D', '', phone.strip())


def normalize_name(name: str) -> str:
    """Lowercase and strip whitespace for comparison."""
    return name.lower().strip()


def get_csv_field(row: dict, *candidate_keys: str) -> str:
    """Try multiple column name variants and return the first non-empty match."""
    for key in candidate_keys:
        val = row.get(key, "").strip()
        if val:
            return val
    return ""


def build_existing_member_set(db: Session) -> set[tuple[str, str]]:
    """
    Load all existing members and build a set of (normalized_full_name, normalized_phone)
    tuples for duplicate detection. Since PII is encrypted, we must decrypt each record.
    """
    existing = set()
    members = db.query(Member).all()
    for m in members:
        try:
            fname = normalize_name(m.first_name or "")
            lname = normalize_name(m.last_name or "")
            phone = normalize_phone(m.phone_number or "")
            full_name = f"{fname} {lname}".strip()
            if full_name or phone:
                existing.add((full_name, phone))
        except Exception:
            # Skip members that can't be decrypted
            continue
    return existing


def decision_is_vetted(decision: str) -> bool:
    """Check if a CSV Decision value indicates the member was vetted."""
    d = decision.strip().lower()
    return d == "y" or "yes" in d


def import_csv(
    csv_file: str,
    is_vetted: bool = False,
    vetter_id: int | None = None,
    match_emails: bool = False,
) -> dict:
    """
    Import members from a CSV file.

    Args:
        csv_file: Path to the CSV file
        is_vetted: If True, force all records to VETTED (overrides Decision column)
        vetter_id: User ID to assign as vetter (optional)
        match_emails: If True, use email-only dedup; otherwise use name+phone

    Returns:
        Dictionary with import statistics
    """
    stats = {
        "total": 0,
        "success": 0,
        "skipped": 0,
        "imported_vetted": 0,
        "imported_pending": 0,
        "duplicate_name_phone": 0,
        "duplicate_email": 0,
        "errors": []
    }

    db: Session = SessionLocal()

    try:
        # Build dedup sets
        if match_emails:
            print("Using email-only duplicate detection...")
        else:
            print("Loading existing members for name+phone duplicate detection...")
            existing_name_phone = build_existing_member_set(db)
            print(f"  Found {len(existing_name_phone)} existing members")

        with open(csv_file, 'r', encoding='utf-8', errors='replace') as f:
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

                    # Extract fields — support both old and new column name formats
                    street_address = get_csv_field(row, "Street address", "Street Address")
                    city = get_csv_field(row, "City")
                    zip_code = get_csv_field(row, "Zip code", "Zip")
                    phone_number = get_csv_field(row, "Phone number", "Phone")
                    email = get_csv_field(row, "Email address (for newsletter)", "Email")

                    # Duplicate detection
                    if match_emails:
                        # Email-only dedup
                        if email:
                            blind_index = generate_blind_index(email)
                            existing = db.query(Member).filter(
                                Member.email_blind_index == blind_index
                            ).first()

                            if existing:
                                stats["skipped"] += 1
                                stats["duplicate_email"] += 1
                                stats["errors"].append(
                                    f"Row {row_num}: Email already exists (Member ID: {existing.id})"
                                )
                                continue
                    else:
                        # Name+phone dedup
                        norm_full = f"{normalize_name(first_name)} {normalize_name(last_name)}".strip()
                        norm_phone = normalize_phone(phone_number)
                        if (norm_full, norm_phone) in existing_name_phone:
                            stats["skipped"] += 1
                            stats["duplicate_name_phone"] += 1
                            stats["errors"].append(
                                f"Row {row_num}: Duplicate name+phone ({full_name} / {phone_number})"
                            )
                            continue

                    # Build custom fields dictionary
                    custom_fields = {}

                    where_learn = get_csv_field(
                        row, "Where did you learn about IPA+?", "Referral source"
                    )
                    if where_learn:
                        custom_fields["where_learn"] = where_learn

                    superpower = get_csv_field(
                        row,
                        "What personal talent, skill, experience, or superpower do you bring to the group? We believe everyone has a superpower!",
                        "Talent/skill",
                    )
                    if superpower:
                        custom_fields["superpower"] = superpower

                    background = get_csv_field(
                        row,
                        "What is your occupational background? Feel free to share your LinkedIn if you like. This helps us connect people to each other and to understand the skills and experience in the group.",
                        "Background",
                    )
                    if background:
                        custom_fields["occupational_background"] = background

                    know_member = get_csv_field(
                        row, "Do you know someone who is a member of IPA+? If so, who?", "Person they know"
                    )
                    if know_member:
                        custom_fields["know_member"] = know_member

                    hoped_impact = get_csv_field(
                        row,
                        "What impact do you hope to have by joining IPA+? (If you don't know, that's OK!)",
                        "Impact want to have",
                    )
                    if hoped_impact:
                        custom_fields["hoped_impact"] = hoped_impact

                    # Add timestamp if available
                    if row.get("Timestamp"):
                        custom_fields["original_timestamp"] = row["Timestamp"].strip()

                    # Determine status from Decision column (or --vetted flag)
                    csv_decision = get_csv_field(row, "Decision")
                    csv_vetter = get_csv_field(row, "Vetter")
                    if is_vetted:
                        status = MemberStatus.VETTED
                    elif csv_decision and decision_is_vetted(csv_decision):
                        status = MemberStatus.VETTED
                    elif csv_decision:
                        # Decision exists but isn't yes/Y — keep as pending
                        status = MemberStatus.PENDING
                    else:
                        # No decision at all — processed + archived
                        status = MemberStatus.PROCESSED

                    # Put CSV Notes into member.notes (visible/editable in detail view)
                    csv_notes = get_csv_field(row, "Notes")
                    member_notes = None
                    note_parts = []
                    if csv_vetter:
                        note_parts.append(f"CSV Vetter: {csv_vetter}")
                    if csv_decision:
                        note_parts.append(f"CSV Decision: {csv_decision}")
                    if csv_notes:
                        note_parts.append(f"CSV Notes: {csv_notes}")
                    if note_parts:
                        member_notes = "\n".join(note_parts)

                    # Create member with non-hybrid fields only
                    member = Member(
                        status=status,
                        archived=(status == MemberStatus.PROCESSED and not is_vetted),
                        assigned_vetter_id=vetter_id if status == MemberStatus.VETTED and vetter_id else None,
                        notes=member_notes,
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

                    # Track the newly added member for within-file dedup
                    if not match_emails:
                        existing_name_phone.add((norm_full, norm_phone))

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
                    if status == MemberStatus.VETTED:
                        stats["imported_vetted"] += 1
                    else:
                        stats["imported_pending"] += 1

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
    parser.add_argument(
        "--match-emails",
        action="store_true",
        help="Use email-only duplicate detection instead of name+phone"
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
    if args.vetted:
        print(f"Status: VETTED (forced via --vetted flag)")
    else:
        print(f"Status: Auto-detect from Decision column (yes/Y → VETTED, otherwise PENDING)")
    print(f"Dedup mode: {'email-only' if args.match_emails else 'name+phone'}")
    if args.user_id:
        print(f"Assigned vetter ID: {args.user_id}")
    print()

    stats = import_csv(args.csv_file, args.vetted, args.user_id, args.match_emails)

    # Print results
    print("\n" + "="*50)
    print("Import Complete")
    print("="*50)
    print(f"Total rows processed: {stats['total']}")
    print(f"Successfully imported: {stats['success']}")
    if stats.get("imported_vetted"):
        print(f"  - As VETTED: {stats['imported_vetted']}")
    if stats.get("imported_pending"):
        print(f"  - As PENDING: {stats['imported_pending']}")
    print(f"Skipped/Errors: {stats['skipped']}")
    if stats.get("duplicate_name_phone"):
        print(f"  - Duplicate name+phone: {stats['duplicate_name_phone']}")
    if stats.get("duplicate_email"):
        print(f"  - Duplicate email: {stats['duplicate_email']}")

    if stats["errors"]:
        print("\nErrors/Warnings:")
        for error in stats["errors"]:
            print(f"  - {error}")

    sys.exit(0 if stats["skipped"] == 0 else 1)


if __name__ == "__main__":
    main()

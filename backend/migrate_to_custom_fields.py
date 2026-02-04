#!/usr/bin/env python3
"""
Migration script to convert custom fields from individual columns to JSON column.

This script:
1. Backs up the existing database
2. Reads all member data from old schema
3. Migrates data to new schema with custom_fields JSON column
4. Validates migration success
5. Reports any issues
"""

import sys
import os
import shutil
import json
from datetime import datetime
from pathlib import Path

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Enum, ForeignKey, inspect
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.sql import text

from app.config import settings
from app.services.encryption import encryption_service

Base = declarative_base()


class OldMember(Base):
    """Old schema with individual custom field columns."""
    __tablename__ = "members"

    id = Column(Integer, primary_key=True)
    first_name = Column(String)
    last_name = Column(String)
    city = Column(String)
    zip_code = Column(String)
    street_address = Column(String)  # Encrypted
    phone_number = Column(String)    # Encrypted
    email = Column(String)           # Encrypted
    email_blind_index = Column(String)
    occupational_background = Column(Text)  # Encrypted
    know_member = Column(Text)              # Encrypted
    hoped_impact = Column(Text)             # Encrypted
    status = Column(String)
    assigned_vetter_id = Column(Integer)
    notes = Column(Text)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)


def get_db_path():
    """Extract the database file path from DATABASE_URL."""
    db_url = settings.DATABASE_URL
    if db_url.startswith("sqlite:///"):
        return db_url.replace("sqlite:///", "")
    raise ValueError(f"Unsupported DATABASE_URL format: {db_url}")


def backup_database(db_path):
    """Create a backup of the database."""
    backup_path = f"{db_path}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    print(f"Creating backup: {backup_path}")
    shutil.copy2(db_path, backup_path)
    print(f"✓ Backup created successfully")
    return backup_path


def read_old_data(engine):
    """Read all member data from old schema."""
    print("\nReading existing member data...")
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        members = session.query(OldMember).all()
        print(f"✓ Found {len(members)} members to migrate")

        member_data = []
        for member in members:
            # Decrypt old custom fields
            occupational_background = None
            know_member_val = None
            hoped_impact = None

            if member.occupational_background:
                try:
                    occupational_background = encryption_service.decrypt(member.occupational_background)
                except Exception as e:
                    print(f"⚠ Warning: Could not decrypt occupational_background for member {member.id}: {e}")

            if member.know_member:
                try:
                    know_member_val = encryption_service.decrypt(member.know_member)
                except Exception as e:
                    print(f"⚠ Warning: Could not decrypt know_member for member {member.id}: {e}")

            if member.hoped_impact:
                try:
                    hoped_impact = encryption_service.decrypt(member.hoped_impact)
                except Exception as e:
                    print(f"⚠ Warning: Could not decrypt hoped_impact for member {member.id}: {e}")

            # Build custom fields dict
            custom_fields = {}
            if occupational_background:
                custom_fields['occupational_background'] = occupational_background
            if know_member_val:
                custom_fields['know_member'] = know_member_val
            if hoped_impact:
                custom_fields['hoped_impact'] = hoped_impact

            member_data.append({
                'id': member.id,
                'first_name': member.first_name,
                'last_name': member.last_name,
                'city': member.city,
                'zip_code': member.zip_code,
                'street_address': member.street_address,  # Keep encrypted
                'phone_number': member.phone_number,      # Keep encrypted
                'email': member.email,                    # Keep encrypted
                'email_blind_index': member.email_blind_index,
                'custom_fields': custom_fields,
                'status': member.status,
                'assigned_vetter_id': member.assigned_vetter_id,
                'notes': member.notes,
                'created_at': member.created_at,
                'updated_at': member.updated_at
            })

        return member_data
    finally:
        session.close()


def migrate_schema(engine):
    """Migrate database schema."""
    print("\nMigrating database schema...")

    with engine.connect() as conn:
        # Check if old columns exist
        inspector = inspect(engine)
        columns = [col['name'] for col in inspector.get_columns('members')]

        # Add new custom_fields column if it doesn't exist
        if 'custom_fields' not in columns:
            print("Adding custom_fields column...")
            conn.execute(text("ALTER TABLE members ADD COLUMN custom_fields TEXT"))
            conn.commit()
            print("✓ Added custom_fields column")

        # Drop old custom field columns if they exist
        for old_column in ['occupational_background', 'know_member', 'hoped_impact']:
            if old_column in columns:
                print(f"Dropping {old_column} column...")
                try:
                    # SQLite doesn't support DROP COLUMN directly in older versions
                    # We'll need to recreate the table
                    conn.execute(text(f"ALTER TABLE members DROP COLUMN {old_column}"))
                    conn.commit()
                    print(f"✓ Dropped {old_column} column")
                except Exception as e:
                    print(f"⚠ Note: Could not drop column {old_column} (SQLite limitation): {e}")
                    print("   This is OK - the column will be ignored.")

    print("✓ Schema migration complete")


def populate_custom_fields(engine, member_data):
    """Populate the custom_fields column with encrypted JSON data."""
    print("\nPopulating custom_fields data...")

    with engine.connect() as conn:
        for member in member_data:
            # Encrypt custom fields JSON
            if member['custom_fields']:
                json_str = json.dumps(member['custom_fields'])
                encrypted_json = encryption_service.encrypt(json_str)
            else:
                encrypted_json = None

            # Update the member record
            conn.execute(
                text("UPDATE members SET custom_fields = :custom_fields WHERE id = :id"),
                {"custom_fields": encrypted_json, "id": member['id']}
            )

        conn.commit()

    print(f"✓ Populated custom_fields for {len(member_data)} members")


def validate_migration(engine, original_count):
    """Validate that migration was successful."""
    print("\nValidating migration...")

    with engine.connect() as conn:
        result = conn.execute(text("SELECT COUNT(*) FROM members"))
        new_count = result.scalar()

        if new_count != original_count:
            raise Exception(f"Migration validation failed: Expected {original_count} members, found {new_count}")

        print(f"✓ Record count verified: {new_count} members")

        # Check that custom_fields are populated
        result = conn.execute(text("SELECT COUNT(*) FROM members WHERE custom_fields IS NOT NULL"))
        custom_fields_count = result.scalar()
        print(f"✓ {custom_fields_count} members have custom_fields data")

    print("✓ Migration validation successful")


def main():
    """Run the migration."""
    print("=" * 70)
    print("CUSTOM FIELDS MIGRATION")
    print("=" * 70)
    print("\nThis script will migrate custom fields from individual columns")
    print("to a single encrypted JSON column.")
    print()

    try:
        # Get database path
        db_path = get_db_path()
        print(f"Database: {db_path}")

        if not os.path.exists(db_path):
            print(f"✗ Error: Database not found at {db_path}")
            return 1

        # Backup database
        backup_path = backup_database(db_path)

        # Connect to database
        engine = create_engine(settings.DATABASE_URL)

        # Read old data
        member_data = read_old_data(engine)
        original_count = len(member_data)

        if original_count == 0:
            print("\nNo members to migrate. Proceeding with schema update only.")

        # Migrate schema
        migrate_schema(engine)

        # Populate custom fields
        if original_count > 0:
            populate_custom_fields(engine, member_data)

        # Validate
        validate_migration(engine, original_count)

        print("\n" + "=" * 70)
        print("MIGRATION COMPLETE")
        print("=" * 70)
        print(f"\n✓ Successfully migrated {original_count} members")
        print(f"✓ Backup saved to: {backup_path}")
        print("\nYou can now restart your application to use the new schema.")

        return 0

    except Exception as e:
        print("\n" + "=" * 70)
        print("MIGRATION FAILED")
        print("=" * 70)
        print(f"\n✗ Error: {e}")
        print("\nThe database backup is available for rollback if needed.")
        if 'backup_path' in locals():
            print(f"Backup location: {backup_path}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

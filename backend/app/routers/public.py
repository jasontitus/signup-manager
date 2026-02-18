from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.member import Member, MemberStatus
from app.schemas.member import MemberCreate
from app.services.blind_index import generate_blind_index
import json
import os

router = APIRouter(prefix="/public", tags=["Public"])

# Path to configuration files
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")
FORM_CONFIG_PATH = os.path.join(DATA_DIR, "form_config.json")
TAG_CONFIG_PATH = os.path.join(DATA_DIR, "tag_config.json")


def load_form_config():
    """Load form configuration, with optional local override."""
    local_path = FORM_CONFIG_PATH.replace('.json', '.local.json')
    path = local_path if os.path.exists(local_path) else FORM_CONFIG_PATH
    with open(path, 'r') as f:
        return json.load(f)


def load_tag_config():
    """Load and return the tag configuration."""
    with open(TAG_CONFIG_PATH, 'r') as f:
        return json.load(f)


@router.get("/form-config")
def get_form_config():
    """Return the form field configuration for dynamic form rendering."""
    return load_form_config()


@router.get("/tag-config")
def get_tag_config():
    """Return the tag category configuration for member tagging."""
    return load_tag_config()


@router.post("/apply", status_code=status.HTTP_201_CREATED)
def submit_application(application: dict, db: Session = Depends(get_db)):
    """Public endpoint for submitting membership applications."""

    # Load form config for validation
    config = load_form_config()

    # Extract and validate standard fields
    try:
        standard_fields = MemberCreate(
            first_name=application.get('first_name'),
            last_name=application.get('last_name'),
            street_address=application.get('street_address'),
            city=application.get('city'),
            zip_code=application.get('zip_code'),
            phone_number=application.get('phone_number'),
            email=application.get('email')
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Validation error: {str(e)}"
        )

    # Check for duplicate email using blind index
    email_index = generate_blind_index(standard_fields.email)
    existing = db.query(Member).filter(Member.email_blind_index == email_index).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An application with this email address already exists"
        )

    # Validate and extract custom fields
    custom_fields = {}
    for field_config in config['fields']:
        key = field_config['key']
        value = application.get(key)

        # Validate required fields
        if field_config.get('required') and not value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{field_config['label']} is required"
            )

        # Validate max length if specified
        if value and 'validation' in field_config:
            max_length = field_config['validation'].get('maxLength')
            if max_length and len(str(value)) > max_length:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"{field_config['label']} exceeds maximum length of {max_length}"
                )

        # Store non-empty values
        if value:
            custom_fields[key] = value

    # Create new member — all PII set via hybrid properties for encryption
    member = Member(status=MemberStatus.PENDING)
    member.first_name = standard_fields.first_name
    member.last_name = standard_fields.last_name
    member.city = standard_fields.city
    member.zip_code = standard_fields.zip_code
    member.street_address = standard_fields.street_address
    member.phone_number = standard_fields.phone_number
    member.email = standard_fields.email  # Also sets blind index
    member.custom_fields = custom_fields

    db.add(member)
    db.commit()
    db.refresh(member)

    return {
        "message": "Application submitted successfully",
        "application_id": member.id
    }

import json
import os
import re

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_admin
from app.models.member import Member
from app.models.user import User
from app.services.audit import audit_service

router = APIRouter(prefix="/tags", tags=["Tags"])

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")
TAG_CONFIG_PATH = os.path.join(DATA_DIR, "tag_config.json")

KEY_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")


def load_tag_config():
    with open(TAG_CONFIG_PATH, "r") as f:
        return json.load(f)


def save_tag_config(config):
    with open(TAG_CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)
        f.write("\n")


class CategoryCreate(BaseModel):
    key: str
    label: str
    options: list[str]
    multiple: bool = False

    @field_validator("key")
    @classmethod
    def validate_key(cls, v):
        if not KEY_PATTERN.match(v):
            raise ValueError("Key must be lowercase alphanumeric with underscores, starting with a letter")
        return v

    @field_validator("options")
    @classmethod
    def validate_options(cls, v):
        if len(v) == 0:
            raise ValueError("At least one option is required")
        if len(v) != len(set(v)):
            raise ValueError("Options must be unique")
        return v


class CategoryUpdate(BaseModel):
    label: str | None = None
    options: list[str] | None = None
    multiple: bool | None = None

    @field_validator("options")
    @classmethod
    def validate_options(cls, v):
        if v is not None:
            if len(v) == 0:
                raise ValueError("At least one option is required")
            if len(v) != len(set(v)):
                raise ValueError("Options must be unique")
        return v


@router.get("")
def get_tag_config(current_user: User = Depends(require_admin)):
    """Return the full tag configuration."""
    return load_tag_config()


@router.post("/categories", status_code=status.HTTP_201_CREATED)
def add_category(
    category: CategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    config = load_tag_config()
    existing_keys = {c["key"] for c in config["categories"]}

    if category.key in existing_keys:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Category with key '{category.key}' already exists",
        )

    config["categories"].append(category.model_dump())
    save_tag_config(config)

    audit_service.log_action(
        db=db,
        user_id=current_user.id,
        member_id=None,
        action="TAG_CATEGORY_ADDED",
        details=f"Added tag category '{category.key}' ({category.label})",
    )

    return category.model_dump()


@router.put("/categories/{key}")
def update_category(
    key: str,
    update: CategoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    config = load_tag_config()
    for cat in config["categories"]:
        if cat["key"] == key:
            changes = []
            if update.label is not None:
                cat["label"] = update.label
                changes.append(f"label='{update.label}'")
            if update.options is not None:
                cat["options"] = update.options
                changes.append(f"options={update.options}")
            if update.multiple is not None:
                cat["multiple"] = update.multiple
                changes.append(f"multiple={update.multiple}")

            save_tag_config(config)

            audit_service.log_action(
                db=db,
                user_id=current_user.id,
                member_id=None,
                action="TAG_CATEGORY_UPDATED",
                details=f"Updated tag category '{key}': {', '.join(changes)}",
            )

            return cat

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Category '{key}' not found",
    )


@router.delete("/categories/{key}")
def delete_category(
    key: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    config = load_tag_config()
    original_len = len(config["categories"])
    config["categories"] = [c for c in config["categories"] if c["key"] != key]

    if len(config["categories"]) == original_len:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Category '{key}' not found",
        )

    save_tag_config(config)

    audit_service.log_action(
        db=db,
        user_id=current_user.id,
        member_id=None,
        action="TAG_CATEGORY_DELETED",
        details=f"Deleted tag category '{key}'",
    )

    return {"message": f"Category '{key}' deleted"}


@router.get("/categories/{key}/usage")
def get_option_usage(
    key: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Get per-option member usage counts for a category."""
    config = load_tag_config()
    category = next((c for c in config["categories"] if c["key"] == key), None)
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Category '{key}' not found",
        )

    members = db.query(Member).filter(Member.tags.isnot(None)).all()
    usage = {}
    for option in category["options"]:
        usage[option] = 0

    for member in members:
        tags = member.tags or {}
        value = tags.get(key)
        if value is None:
            continue
        if isinstance(value, list):
            for v in value:
                if v in usage:
                    usage[v] = usage[v] + 1
                else:
                    usage[v] = 1
        else:
            if value in usage:
                usage[value] = usage[value] + 1
            else:
                usage[value] = 1

    total = sum(usage.values())
    return {"category": key, "usage": usage, "total_members_using": total}

import enum
from sqlalchemy import Column, Integer, String, Enum, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.ext.hybrid import hybrid_property
from datetime import datetime
from app.database import Base
from app.services.encryption import encryption_service
from app.services.blind_index import generate_blind_index


class MemberStatus(str, enum.Enum):
    PENDING = "PENDING"
    ASSIGNED = "ASSIGNED"
    VETTED = "VETTED"
    REJECTED = "REJECTED"


class Member(Base):
    __tablename__ = "members"

    id = Column(Integer, primary_key=True, index=True)

    # Public fields (not encrypted)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    city = Column(String, nullable=False)
    zip_code = Column(String, nullable=False)

    # Encrypted PII fields (stored encrypted)
    _street_address = Column("street_address", String, nullable=False)
    _phone_number = Column("phone_number", String, nullable=False)
    _email = Column("email", String, nullable=False)
    _occupational_background = Column("occupational_background", Text, nullable=True)
    _know_member = Column("know_member", Text, nullable=True)
    _hoped_impact = Column("hoped_impact", Text, nullable=True)

    # Blind index for email (for duplicate checking)
    email_blind_index = Column(String, index=True, nullable=False)

    # Workflow fields
    status = Column(Enum(MemberStatus), default=MemberStatus.PENDING, nullable=False, index=True)
    assigned_vetter_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)

    # Internal notes (not visible to applicant)
    notes = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Hybrid properties for transparent encryption/decryption
    @hybrid_property
    def street_address(self):
        return encryption_service.decrypt(self._street_address)

    @street_address.setter
    def street_address(self, value):
        self._street_address = encryption_service.encrypt(value)

    @hybrid_property
    def phone_number(self):
        return encryption_service.decrypt(self._phone_number)

    @phone_number.setter
    def phone_number(self, value):
        self._phone_number = encryption_service.encrypt(value)

    @hybrid_property
    def email(self):
        return encryption_service.decrypt(self._email)

    @email.setter
    def email(self, value):
        self._email = encryption_service.encrypt(value)
        self.email_blind_index = generate_blind_index(value)

    @hybrid_property
    def occupational_background(self):
        if self._occupational_background:
            return encryption_service.decrypt(self._occupational_background)
        return None

    @occupational_background.setter
    def occupational_background(self, value):
        if value:
            self._occupational_background = encryption_service.encrypt(value)
        else:
            self._occupational_background = None

    @hybrid_property
    def know_member(self):
        if self._know_member:
            return encryption_service.decrypt(self._know_member)
        return None

    @know_member.setter
    def know_member(self, value):
        if value:
            self._know_member = encryption_service.encrypt(value)
        else:
            self._know_member = None

    @hybrid_property
    def hoped_impact(self):
        if self._hoped_impact:
            return encryption_service.decrypt(self._hoped_impact)
        return None

    @hoped_impact.setter
    def hoped_impact(self, value):
        if value:
            self._hoped_impact = encryption_service.encrypt(value)
        else:
            self._hoped_impact = None

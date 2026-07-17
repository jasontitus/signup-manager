from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    # Generous bounds — just enough to stop megabyte-sized credential
    # payloads from reaching bcrypt / the DB lookup.
    username: str = Field(min_length=1, max_length=150)
    password: str = Field(min_length=1, max_length=512)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    username: str
    role: str
    full_name: str

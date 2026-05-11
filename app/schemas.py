import re
from datetime import datetime

from pydantic import BaseModel, field_validator

SLUG_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")
RESERVED_SLUGS = {"api", "health", "docs", "openapi.json", "redoc", "ui"}


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    ok: bool = True


class RouteCreate(BaseModel):
    slug: str
    destination_url: str
    signing_secret: str | None = None
    description: str | None = None

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, v: str) -> str:
        if not SLUG_PATTERN.match(v):
            raise ValueError("slug must match ^[a-zA-Z0-9_-]{1,64}$")
        if v.lower() in RESERVED_SLUGS:
            raise ValueError(f"slug '{v}' is reserved")
        return v

    @field_validator("destination_url")
    @classmethod
    def validate_destination(cls, v: str) -> str:
        if not v.startswith(("http://", "https://")):
            raise ValueError("destination_url must start with http:// or https://")
        return v


class RouteUpdate(BaseModel):
    destination_url: str | None = None
    enabled: bool | None = None
    signing_secret: str | None = None
    description: str | None = None

    @field_validator("destination_url")
    @classmethod
    def validate_destination(cls, v: str | None) -> str | None:
        if v is not None and not v.startswith(("http://", "https://")):
            raise ValueError("destination_url must start with http:// or https://")
        return v


class RouteResponse(BaseModel):
    id: int
    slug: str
    destination_url: str
    enabled: bool
    signing_secret_set: bool
    description: str | None
    webhook_url: str
    created_at: datetime

    model_config = {"from_attributes": True}


class DeliveryResponse(BaseModel):
    id: int
    route_id: int
    source_event_id: str | None
    method: str
    status: str
    attempt_count: int
    response_status: int | None
    response_body_excerpt: str | None
    error: str | None
    latency_ms: int | None
    created_at: datetime

    model_config = {"from_attributes": True}

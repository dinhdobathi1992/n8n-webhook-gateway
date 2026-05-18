import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, field_validator, model_validator

SLUG_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")
RESERVED_SLUGS = {"api", "health", "docs", "openapi.json", "redoc", "ui"}

SourceType = Literal["slack", "gchat", "generic"]


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    ok: bool = True


class RouteCreate(BaseModel):
    slug: str
    destination_url: str
    source_type: SourceType = "slack"
    signing_secret: str | None = None
    secret_header_name: str | None = None
    auth_header_name: str | None = None
    auth_header_value: str | None = None
    description: str | None = None
    workflow_url: str | None = None

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

    @model_validator(mode="after")
    def validate_source_fields(self):
        if self.source_type == "slack":
            if not self.signing_secret:
                raise ValueError("signing_secret is required for slack source")
        elif self.source_type == "generic":
            if not self.signing_secret:
                raise ValueError("signing_secret is required for generic source")
            if not self.secret_header_name:
                raise ValueError("secret_header_name is required for generic source")
        elif self.source_type == "gchat":
            self.signing_secret = None
        return self


class RouteUpdate(BaseModel):
    destination_url: str | None = None
    enabled: bool | None = None
    signing_secret: str | None = None
    secret_header_name: str | None = None
    auth_header_name: str | None = None
    auth_header_value: str | None = None
    description: str | None = None
    workflow_url: str | None = None

    @field_validator("destination_url")
    @classmethod
    def validate_destination(cls, v: str | None) -> str | None:
        if v is not None and not v.startswith(("http://", "https://")):
            raise ValueError("destination_url must start with http:// or https://")
        return v


class ChannelRuleCreate(BaseModel):
    channel_id: str
    destination_url: str
    workflow_url: str | None = None
    description: str | None = None

    @field_validator("channel_id")
    @classmethod
    def validate_channel_id(cls, v: str) -> str:
        if not v or len(v) > 64:
            raise ValueError("channel_id must be 1-64 characters")
        return v

    @field_validator("destination_url")
    @classmethod
    def validate_destination(cls, v: str) -> str:
        if not v.startswith(("http://", "https://")):
            raise ValueError("destination_url must start with http:// or https://")
        return v


class ChannelRuleResponse(BaseModel):
    id: int
    route_id: int
    channel_id: str
    destination_url: str
    workflow_url: str | None
    description: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class RouteResponse(BaseModel):
    id: int
    slug: str
    destination_url: str
    enabled: bool
    source_type: str
    signing_secret_set: bool
    auth_header_set: bool
    auth_header_name: str | None
    secret_header_name: str | None
    description: str | None
    workflow_url: str | None
    webhook_url: str
    channel_rules: list["ChannelRuleResponse"] = []
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

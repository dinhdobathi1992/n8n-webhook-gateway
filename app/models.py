from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.encrypted_string_type import EncryptedString


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    routes: Mapped[list["WebhookRoute"]] = relationship(back_populates="creator")


class WebhookRoute(Base):
    __tablename__ = "webhook_routes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    destination_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    signing_secret: Mapped[str | None] = mapped_column(EncryptedString(255), nullable=True)
    auth_header_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    auth_header_value: Mapped[str | None] = mapped_column(EncryptedString(2048), nullable=True)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False, default="slack")
    secret_header_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    creator: Mapped["User"] = relationship(back_populates="routes")
    deliveries: Mapped[list["DeliveryAttempt"]] = relationship(back_populates="route")


class DeliveryAttempt(Base):
    __tablename__ = "delivery_attempts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    route_id: Mapped[int] = mapped_column(Integer, ForeignKey("webhook_routes.id"), nullable=False)
    source_event_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    method: Mapped[str] = mapped_column(String(10), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    response_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_body_excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    route: Mapped["WebhookRoute"] = relationship(back_populates="deliveries")

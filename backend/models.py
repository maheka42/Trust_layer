"""Dataclasses that mirror the TrustLayer SQLite schema."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

GroundTruth = Literal["normal", "fraud", "trap"]


@dataclass(frozen=True)
class User:
    id: str
    full_name: str
    email: str
    phone: str
    country: str
    city: str
    home_lat: float
    home_lng: float
    currency: str
    typical_avg_amount: float
    created_at: str


@dataclass(frozen=True)
class Device:
    id: str
    user_id: str
    fingerprint: str
    device_type: str
    os_name: str
    browser: str
    is_primary: int
    first_seen: str


@dataclass(frozen=True)
class Merchant:
    id: str
    name: str
    category: str
    country: str
    mcc: str
    risk_level: str


@dataclass(frozen=True)
class Transaction:
    id: str
    user_id: str
    device_id: str
    merchant_id: str
    amount: float
    currency: str
    timestamp: str
    ip_address: str
    city: str
    country: str
    latitude: float
    longitude: float
    channel: str
    payment_method: str
    card_last4: str
    ground_truth: GroundTruth


@dataclass(frozen=True)
class Chargeback:
    id: str
    transaction_id: str
    user_id: str
    amount: float
    reason: str
    status: str
    filed_at: str

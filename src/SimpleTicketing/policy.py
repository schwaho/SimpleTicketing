"""Policy decision types and reason codes."""

from dataclasses import dataclass
from typing import Optional
from enum import StrEnum, auto


class PolicyReason(StrEnum):
    """Reason codes describing why a policy decision was rejected."""

    OFFER_QUANTITY_INVALID = auto()
    OFFER_QUANTITY_EXCEEDED = auto()
    OFFER_PRICE_TOO_LOW = auto()
    OFFER_PRICE_TOO_HIGH = auto()
    OFFER_EXPIRED = auto()
    TICKET_NOT_PAID = auto()
    TICKET_SHIPPED = auto()
    TICKET_CANCELLED = auto()
    TICKET_CODE_INVALID = auto()
    TICKET_ALREADY_CHECKED_IN = auto()
    NO_AVAILABLE_CREDITS = auto()
    NO_UNBOOKED_PAYMENT = auto()


@dataclass(frozen=True)
class PolicyDecision:
    """
    Result of evaluating a business policy.

    Attributes:
        allowed: Whether the requested operation is permitted.
        reason: Reason for rejection, or None if the operation is permitted.
    """

    allowed: bool
    reason: Optional[PolicyReason] = None

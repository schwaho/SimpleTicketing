from dataclasses import dataclass
from typing import Optional
from enum import StrEnum, auto


class PolicyReason(StrEnum):
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
    allowed: bool
    reason: Optional[PolicyReason] = None

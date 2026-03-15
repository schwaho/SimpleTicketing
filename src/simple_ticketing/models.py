"""
This module defines domain records
"""

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional, Dict, Any


@dataclass
class BaseDomainRecord:
    """Base domain record providing generic mapping"""

    id: int
    created_at: datetime

    def as_dict(self) -> Dict[str, Any]:
        """
        Return Domain record as dict and convert all datetime values
        in a dictionary to ISO 8601 strings.

        Iterates over all key-value pairs in the input dictionary and replaces
        values of type `datetime` with their ISO 8601 string representation
        using `datetime.isoformat()`."""

        return {
            key: value.isoformat() if isinstance(value, datetime) else value
            for key, value in asdict(self).items()
        }


# pylint: disable=too-many-instance-attributes
@dataclass(slots=True)
class Ticket(BaseDomainRecord):
    """Domain record representing a row in the 'tickets' table."""

    ticket_code: str
    seat_type: str
    target_amount: int
    customer_id: int
    offer_id: int
    check_in_at: Optional[datetime]
    cancelled_at: Optional[datetime]


@dataclass(slots=True)
class Customer(BaseDomainRecord):
    """Domain record representing a row in the 'customers' table."""

    name: str
    email: str


@dataclass(slots=True)
class Offer(BaseDomainRecord):
    """Domain record representing a row in the 'offers' table."""

    offer_code: str
    customer_id: int
    ticket_count: int
    ticket_price: int
    valid_until: Optional[datetime]


@dataclass(slots=True)
class Payment(BaseDomainRecord):
    """Domain record representing a row in the 'payments' table."""

    customer_id: int
    amount: int
    payment_ref: Optional[str]


@dataclass(slots=True)
class Credit(BaseDomainRecord):
    """Domain record representing a row in the 'credits' table."""

    customer_id: int
    amount: int
    reason: Optional[str]


@dataclass(slots=True)
class Shipment(BaseDomainRecord):
    """Domain record representing a row in the 'shipments' table."""

    customer_id: int
    sent_at: datetime

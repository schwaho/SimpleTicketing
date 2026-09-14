"""
Repository for persisting entity relations.
"""

from SimpleTicketing import models
from SimpleTicketing.repository.base import RelationRepository


class PaymentCreditsRepository(
    RelationRepository[models.Payment, models.Credit]
):  # pylint: disable=too-few-public-methods
    """Manage relationships between payments and credits."""

    def __init__(self) -> None:
        super().__init__("payment_credits", "payment_id", "credit_id")


class PaymentOffersRepository(
    RelationRepository[models.Payment, models.Offer]
):  # pylint: disable=too-few-public-methods
    """Manage relationships between payments and offers."""

    def __init__(self) -> None:
        super().__init__("payment_offers", "payment_id", "offer_id")


class ShiptmentTicketsRepository(
    RelationRepository[models.Shipment, models.Ticket]
):  # pylint: disable=too-few-public-methods
    """Manage relationships between shipments and tickets."""

    def __init__(self) -> None:
        super().__init__("shipment_tickets", "shipment_id", "ticket_id")


class TicketCreditsRepository(
    RelationRepository[models.Ticket, models.Credit]
):  # pylint: disable=too-few-public-methods
    """Manage relationships between tickets and credits."""

    def __init__(self) -> None:
        super().__init__("ticket_credits", "ticket_id", "credit_id")

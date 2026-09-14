"""
Repository for persisting entity relations.
"""

from simple_ticketing import models
from simple_ticketing.repository.base import RelationRepository


class PaymentCreditsRepository(RelationRepository[models.Payment, models.Credit]):
    def __init__(self):
        super().__init__("payment_credits", "payment_id", "credit_id")


class PaymentOffersRepository(RelationRepository[models.Payment, models.Offer]):
    def __init__(self):
        super().__init__("payment_offers", "payment_id", "offer_id")


class ShiptmentTicketsRepository(RelationRepository[models.Shipment, models.Ticket]):
    def __init__(self):
        super().__init__("shipment_tickets", "shipment_id", "ticket_id")


class TicketCreditsRepository(RelationRepository[models.Ticket, models.Credit]):
    def __init__(self):
        super().__init__("ticket_credits", "ticket_id", "credit_id")

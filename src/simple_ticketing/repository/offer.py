"""
Repository for persisting and retrieving offer entities.

This module provides the persistence operations for :class:`models.Offer`
entities. It maps between domain models and database records while delegating
database access to the database abstraction layer.
"""

from typing import List
from pypika import Table, Parameter
from simple_ticketing import database
from simple_ticketing import models
from simple_ticketing.repository.base import DataRepository, RecordNotFound
from simple_ticketing.repository.mapping import row_to_record, rows_to_records


class OfferRepository(DataRepository[models.Offer]):

    def __init__(self) -> None:
        super().__init__("offers", models.Offer)
        self._payment_offers = Table("payment_offers")
        self._tickets = Table("tickets")

    def from_customer(self, customer_id: int) -> List[models.Offer]:
        """
        Get offer entities by customer ID.

        Args:
            customer_id: ID of the customer associated with the offers.

        Returns:
            A list containing the offer entities associated with the given customer ID.
        """

        query = (
            self._query.from_(self._table)
            .select("*")
            .where(self._table.customer_id == Parameter(":customer_id"))
        )

        rows = database.fetch_all(query.get_sql(), {"customer_id": customer_id})
        return rows_to_records(models.Offer, rows)

    def from_payment(self, payment_id: int) -> List[models.Offer]:
        """
        Get offer entities by payment ID.

        Args:
            payment_id: ID of the payment associated with the offers.

        Returns:
            A list containing the offer entities associated with the given payment ID.
        """

        query = (
            self._query.from_(self._table)
            .join(self._payment_offers)
            .on(self._table.id == self._payment_offers.offer_id)
            .select(self._table.star)
            .where(self._table.payment_id == Parameter(":payment_id"))
        )

        rows = database.fetch_all(query.get_sql(), {"payment_id": payment_id})
        return rows_to_records(models.Offer, rows)

    def from_ticket(self, ticket_id: int) -> models.Offer:
        """
        Get offer entity by ticket ID.

        Args:
            ticket_id: ID of the ticket associated with the offer.

        Returns:
            The offer entity associated with the given ticket ID.

        Raises:
            RecordNotFound: If no offer is associated with the given ticket ID.
        """

        query = (
            self._query.from_(self._table)
            .join(self._tickets)
            .on(self._table.id == self._tickets.offer_id)
            .select(self._table.star)
            .where(self._tickets.id == Parameter(":ticket_id"))
        )

        row = database.fetch_one(query.get_sql(), {"ticket_id": ticket_id})
        if row:
            return row_to_record(models.Offer, row)
        raise RecordNotFound(f"No Entity for ticket_id={ticket_id}")

    def from_offer_code(self, offer_code: str) -> models.Offer:
        """
        Get offer entity by the offer code.

        Args:
            offer_ocde: Offer code associated with the offer.

        Returns:
            The offer entity associated with the given offer code.

        Raises:
            RecordNotFound: If no offer is associated with the given offer code.
        """

        query = (
            self._query.from_(self._table)
            .select(self._table.star)
            .where(self._table.offer_code == Parameter(":offer_code"))
        )

        row = database.fetch_one(query.get_sql(), {"offer_code": offer_code})
        if row:
            return row_to_record(models.Offer, row)
        raise RecordNotFound(f"No Entity for offer_code={offer_code}")

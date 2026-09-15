"""
Repository for persisting and retrieving offer entities.

This module provides the persistence operations for :class:`models.Offer`
entities. It maps between domain models and database records while delegating
database access to the database abstraction layer.
"""

from typing import List
from pypika import Table
from pypika.dialects import SQLLiteQuery as Query
from simple_ticketing import database
from simple_ticketing import models
from simple_ticketing.repository.base import DataRepository
from simple_ticketing.repository.mapping import rows_to_records


class OfferRepository(DataRepository[models.Offer]):
    def __init__(self):
        super().__init__("offers", models.Offer)
        self._payment_offers = Table("payment_offers")

    def from_customer(self, customer_id: int) -> List[models.Offer]:
        """
        Get offer entities by customer ID.

        Args:
            customer_id: ID of the customer associated with the offer.

        Returns:
            A list containing the offer entities associated with the given customer ID.
        """

        query = (
            Query.from_(self._table).select("*").where(self._offers.customer_id == ":customer_id")
        )

        rows = database.fetch_all(query.get_sql(), {"customer_id": customer_id})
        return rows_to_records(models.Offer, rows)

    def from_payment(self, payment_id: int) -> List[models.Offer]:
        """
        Get offer entities by payment ID.

        Args:
            payment_id: ID of the payment associated with the offer.

        Returns:
            A list containing the offer entities associated with the given payment ID.
        """

        query = (
            Query.from_(self._table)
            .join(self._payment_offers)
            .on(self._table.id == self._payment_offers.offer_id)
            .select(self._table.star)
            .where(self._table.payment_id == ":payment_id")
        )

        rows = database.fetch_all(query.get_sql(), {"payment_id": payment_id})
        return rows_to_records(models.Offer, rows)

"""
Repository for persisting and retrieving payment entities.

This module provides the persistence operations for :class:`models.Payment`
entities. It maps between domain models and database records while delegating
database access to the database abstraction layer.
"""

from typing import List
from pypika import Table, Parameter
from simple_ticketing import database
from simple_ticketing import models
from simple_ticketing.repository.base import DataRepository
from simple_ticketing.repository.mapping import rows_to_records


class PaymentRepository(DataRepository[models.Payment]):

    def __init__(self) -> None:
        super().__init__("payments", models.Payment)
        self._payment_offers = Table("payment_offers")
        self._payment_credits = Table("payment_credits")

    def from_customer(self, customer_id: int) -> List[models.Payment]:
        """
        Get payment entities by customer ID.

        Args:
            customer_id: ID of the customer associated with the payment.

        Returns:
            A list containing the payment entities associated with the given customer ID.
        """

        query = (
            self._query.from_(self._table)
            .select("*")
            .where(self._table.customer_id == Parameter(":customer_id"))
        )

        rows = database.fetch_all(query.get_sql(), {"customer_id": customer_id})
        return rows_to_records(models.Payment, rows)

    def from_offer(self, offer_id: int) -> List[models.Payment]:
        """
        Get payment entities by offer ID.

        Args:
            offer_id: ID of the offer associated with the payment.

        Returns:
            A list containing the payment entities associated with the given offer ID.
        """

        query = (
            self._query.from_(self._table)
            .join(self._payment_offers)
            .on(self._table.id == self._payment_offers.payment_id)
            .select(self._table.star)
            .where(self._payment_offers.offer_id == Parameter(":offer_id"))
        )

        rows = database.fetch_all(query.get_sql(), {"offer_id": offer_id})
        return rows_to_records(models.Payment, rows)

    def from_credit(self, credit_id: int) -> List[models.Payment]:
        """
        Get payment entities by credit ID.

        Args:
            credit_id: ID of the credit associated with the payment.

        Returns:
            A list containing the payment entities associated with the given credit ID.
        """

        query = (
            self._query.from_(self._table)
            .join(self._payment_credits)
            .on(self._table.id == self._payment_credits.payment_id)
            .select(self._table.star)
            .where(self._payment_credits.credit_id == Parameter(":credit_id"))
        )

        rows = database.fetch_all(query.get_sql(), {"credit_id": credit_id})
        return rows_to_records(models.Payment, rows)

"""
Repository for persisting and retrieving credit entities.

This module provides the persistence operations for :class:`models.Credit`
entities. It maps between domain models and database records while delegating
database access to the database abstraction layer.
"""

from typing import List
from pypika import Table, Parameter
from simple_ticketing import database
from simple_ticketing import models
from simple_ticketing.repository.base import DataRepository
from simple_ticketing.repository.mapping import rows_to_records


class CreditRepository(DataRepository[models.Credit]):

    def __init__(self) -> None:
        super().__init__("credits", models.Credit)
        self._credits = Table("credits")
        self._payment_credits = Table("payment_credits")
        self._ticket_credits = Table("ticket_credits")

    def from_payment(self, payment_id: int) -> List[models.Credit]:
        """
        Get credit entities by payment ID.

        Args:
            payment_id: ID of the payment associated with the credit.

        Returns:
            A list containing the credit entities associated with the given payment ID.
        """

        query = (
            self._query.from_(self._table)
            .join(self._payment_credits)
            .on(self._table.id == self._payment_credits.credit_id)
            .select(self._table.star)
            .where(self._payment_credits.payment_id == Parameter(":payment_id"))
        )

        rows = database.fetch_all(query.get_sql(), {"payment_id": payment_id})
        return rows_to_records(models.Credit, rows)

    def from_ticket(self, ticket_id: int) -> List[models.Credit]:
        """
        Get credit entities by ticket ID.

        Args:
            ticket_id: ID of the ticket associated with the credit.

        Returns:
            A list containing the credit entities associated with the given ticket ID.
        """

        query = (
            self._query.from_(self._table)
            .join(self._ticket_credits)
            .on(self._table.id == self._ticket_credits.credit_id)
            .select(self._table.star)
            .where(self._ticket_credits.ticket_id == Parameter(":ticket_id"))
        )

        rows = database.fetch_all(query.get_sql(), {"ticket_id": ticket_id})
        return rows_to_records(models.Credit, rows)

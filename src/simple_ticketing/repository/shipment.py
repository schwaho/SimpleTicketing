"""
Repository for persisting and retrieving shipment entities.

This module provides the persistence operations for :class:`models.Shipment`
entities. It maps between domain models and database records while delegating
database access to the database abstraction layer.
"""

from typing import List
from pypika import Table, Parameter
from simple_ticketing import database
from simple_ticketing import models
from simple_ticketing.repository.base import DataRepository
from simple_ticketing.repository.mapping import rows_to_records


class ShiptmentRepository(DataRepository[models.Shipment]):

    def __init__(self) -> None:
        super().__init__("shipments", models.Shipment)
        self._shipment_tickets = Table("shipment_tickets")

    def from_ticket(self, ticket_id: int) -> List[models.Shipment]:
        """
        Get shipment entities by ticket ID.

        Args:
            ticket_id: ID of the ticket associated with the shipment.

        Returns:
            A list containing the shipment entities associated with the given ticket ID.
        """

        query = (
            self._query.from_(self._table)
            .join(self._shipment_tickets)
            .on(self._table.id == self._shipment_tickets.shipment_id)
            .select(self._table.star)
            .where(self._shipment_tickets.ticket_id == Parameter(":ticket_id"))
        )

        rows = database.fetch_all(query.get_sql(), {"ticket_id": ticket_id})
        return rows_to_records(models.Shipment, rows)

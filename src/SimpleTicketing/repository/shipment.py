"""
Repository for persisting and retrieving shipment entities.

This module provides the persistence operations for :class:`models.Shipment`
entities. It maps between domain models and database records while delegating
database access to the database abstraction layer.
"""

from typing import List
from pypika import Table, Parameter
from SimpleTicketing import database
from SimpleTicketing import models
from SimpleTicketing.repository.base import DataRepository
from SimpleTicketing.repository.mapping import rows_to_records


class ShipmentRepository(DataRepository[models.Shipment]):
    """Repository for accessing and managing shipments."""

    def __init__(self) -> None:
        super().__init__("shipments", models.Shipment)
        self._shipment_tickets = Table("shipment_tickets")

    def from_ticket(self, ticket_id: int) -> List[models.Shipment]:
        """
        Get shipment entities by ticket ID.

        Args:
            ticket_id: ID of the ticket associated with the shipments.

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

    def from_customer(self, customer_id: int) -> List[models.Shipment]:
        """
        Get shipment entities by customer ID.

        Args:
            customer_id: ID of the customer associated with the shipments.

        Returns:
            A list containing the shipment entities associated with the given customer ID.
        """

        query = (
            self._query.from_(self._table)
            .select(self._table.star)
            .where(self._table.customer_id == Parameter(":customer_id"))
        )

        rows = database.fetch_all(query.get_sql(), {"customer_id": customer_id})
        return rows_to_records(models.Shipment, rows)

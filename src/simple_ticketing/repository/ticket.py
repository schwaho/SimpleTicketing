"""
Repository for persisting and retrieving ticket entities.

This module provides the persistence operations for :class:`models.Ticket`
entities. It maps between domain models and database records while delegating
database access to the database abstraction layer.
"""

from typing import List, cast
from pypika import Table, Parameter, functions as fn
from simple_ticketing import database
from simple_ticketing import models
from simple_ticketing.repository.mapping import row_to_record, rows_to_records
from simple_ticketing.repository.base import DataRepository, RecordNotFound


class TicketRepository(DataRepository[models.Ticket]):

    def __init__(self) -> None:
        super().__init__("tickets", models.Ticket)
        self._credits = Table("credits")
        self._ticket_credits = Table("ticket_credits")
        self._shipment_tickets = Table("shipment_tickets")

    def from_credit(self, credit_id: int) -> models.Ticket:
        """
        Get a ticket entity by its credit ID.

        Args:
            credit_id: ID of the credit associated with the ticket.

        Returns:
            The ticket entity associated with the given credit ID.

        Raises:
            RecordNotFound: If no ticket is associated with the given credit ID.
        """

        query = (
            self._query.from_(self._table)
            .join(self._ticket_credits)
            .on(self._table.id == self._ticket_credits.ticket_id)
            .select(self._table.star)
            .where(self._ticket_credits.credit_id == Parameter(":credit_id"))
        )

        row = database.fetch_one(query.get_sql(), {"credit_id": credit_id})
        if row:
            return row_to_record(models.Ticket, row)
        raise RecordNotFound(f"No Entity for credit_id={credit_id}")

    def from_shipment(self, shipment_id: int) -> List[models.Ticket]:
        """
        Get ticket entities by their shipment ID.

        Args:
            shipment_id: ID of the shipment associated with the tickets.

        Returns:
            A list containing the ticket entities associated with the given
            shipment ID.
        """

        query = (
            self._query.from_(self._table)
            .join(self._shipment_tickets)
            .on(self._table.id == self._shipment_tickets.ticket_id)
            .select(self._table.star)
            .where(self._shipment_tickets.shipment_id == Parameter(":shipment_id"))
        )
        rows = database.fetch_all(query.get_sql(), {"shipment_id": shipment_id})

        return rows_to_records(models.Ticket, rows)

    def from_customer(self, customer_id: int) -> List[models.Ticket]:
        """
        Get ticket entities by their customer ID.

        Args:
            customer_id: ID of the customer associated with the tickets.

        Returns:
            A list containing the ticket entities belonging to the given
            customer ID.
        """

        query = (
            self._query.from_(self._table)
            .select("*")
            .where(self._table.customer_id == Parameter(":customer_id"))
        )
        rows = database.fetch_all(query.get_sql(), {"customer_id": customer_id})

        return rows_to_records(models.Ticket, rows)

    def from_offer(self, offer_id: int) -> List[models.Ticket]:
        """
        Get ticket entities by their offer ID.

        Args:
            offer_id: ID of the offer associated with the tickets.

        Returns:
            A list containing the ticket entities associated with the given
            offer ID.
        """

        query = (
            self._query.from_(self._table)
            .select("*")
            .where(self._table.offer_id == Parameter(":offer_id"))
        )
        rows = database.fetch_all(query.get_sql(), {"offer_id": offer_id})
        return rows_to_records(models.Ticket, rows)

    def total_credit_amount(self, ticket_id: int) -> int:
        """Get the total credit amount for a ticket.

        Args:
            ticket_id: ID of the ticket for which to calculate the total credit
                amount.

        Returns:
            The total amount of all credits associated with the ticket, or 0 if
            no credits are associated with the ticket.
        """

        query = (
            self._query.from_(self._credits)
            .join(self._ticket_credits)
            .on(self._credits.id == self._ticket_credits.credit_id)
            .select(
                fn.Coalesce(fn.Sum(self._credits.amount), 0).as_(  # type: ignore[no-untyped-call]
                    "total_credit_amount"
                )
            )
            .where(self._ticket_credits.ticket_id == Parameter(":ticket_id"))
        )
        row = database.fetch_one(query.get_sql(), {"ticket_id": ticket_id})

        if row:
            total = cast(int, row.get("total_credit_amount", 0))
            return total
        return 0

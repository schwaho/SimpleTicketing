"""
Repository for persisting and retrieving customer entities.

This module provides the persistence operations for :class:`models.Customer`
entities. It maps between domain models and database records while delegating
database access to the database abstraction layer.
"""

from pypika import Table, Parameter
from simple_ticketing import database
from simple_ticketing import models
from simple_ticketing.repository.base import DataRepository, RecordNotFound
from simple_ticketing.repository.mapping import row_to_record


class CustomerRepository(DataRepository[models.Customer]):

    def __init__(self) -> None:
        super().__init__("customers", models.Customer)
        self._tickets = Table("tickets")
        self._offers = Table("offers")
        self._payments = Table("payments")
        self._credits = Table("credits")
        self._shipments = Table("shipments")

    def from_ticket(self, ticket_id: int) -> models.Customer:
        """
        Get customer entity by ticket ID.

        Args:
            ticket_id: ID of the ticket associated with the customer.

        Returns:
            The customer entity associated with the given ticket ID.

        Raises:
            RecordNotFound: If no customer is associated with the given ticket ID.
        """

        query = (
            self._query.from_(self._table)
            .join(self._tickets)
            .on(self._table.id == self._tickets.customer_id)
            .select(self._table.star)
            .where(self._tickets.id == Parameter(":ticket_id"))
        )

        row = database.fetch_one(query.get_sql(), {"ticket_id": ticket_id})
        if row:
            return row_to_record(models.Customer, row)
        raise RecordNotFound(f"No Entity for ticket_id={ticket_id}")

    def from_offer(self, offer_id: int) -> models.Customer:
        """
        Get customer entity by offer ID.

        Args:
            offer_id: ID of the offer associated with the customer.

        Returns:
            The customer entity associated with the given offer ID.

        Raises:
            RecordNotFound: If no customer is associated with the given offer ID.
        """

        query = (
            self._query.from_(self._table)
            .join(self._offers)
            .on(self._table.id == self._offers.customer_id)
            .select(self._table.star)
            .where(self._offers.id == Parameter(":offer_id"))
        )

        row = database.fetch_one(query.get_sql(), {"offer_id": offer_id})
        if row:
            return row_to_record(models.Customer, row)
        raise RecordNotFound(f"No Entity for offer_id={offer_id}")

    def from_payment(self, payment_id: int) -> models.Customer:
        """
        Get customer entity by payment ID.

        Args:
            payment_id: ID of the payment associated with the customer.

        Returns:
            The customer entity associated with the given payment ID.

        Raises:
            RecordNotFound: If no customer is associated with the given payment ID.
        """

        query = (
            self._query.from_(self._table)
            .join(self._payments)
            .on(self._table.id == self._payments.customer_id)
            .select(self._table.star)
            .where(self._payments.id == Parameter(":payment_id"))
        )

        row = database.fetch_one(query.get_sql(), {"payment_id": payment_id})
        if row:
            return row_to_record(models.Customer, row)
        raise RecordNotFound(f"No Entity for payment_id={payment_id}")

    def from_credit(self, credit_id: int) -> models.Customer:
        """
        Get customer entity by credit ID.

        Args:
            credit_id: ID of the credit associated with the customer.

        Returns:
            The customer entity associated with the given credit ID.

        Raises:
            RecordNotFound: If no customer is associated with the given credit ID.
        """

        query = (
            self._query.from_(self._table)
            .join(self._credits)
            .on(self._table.id == self._credits.customer_id)
            .select(self._table.star)
            .where(self._credits.id == Parameter(":credit_id"))
        )

        row = database.fetch_one(query.get_sql(), {"credit_id": credit_id})
        if row:
            return row_to_record(models.Customer, row)
        raise RecordNotFound(f"No Entity for credit_id={credit_id}")

    def from_shipment(self, shipment_id: int) -> models.Customer:
        """
        Get customer entity by shipment ID.

        Args:
            shipment_id: ID of the shipment associated with the customer.

        Returns:
            The customer entity associated with the given shipment ID.

        Raises:
            RecordNotFound: If no customer is associated with the given shipment ID.
        """

        query = (
            self._query.from_(self._table)
            .join(self._shipments)
            .on(self._table.id == self._shipments.customer_id)
            .select(self._table.star)
            .where(self._shipments.id == Parameter(":shipment_id"))
        )

        row = database.fetch_one(query.get_sql(), {"shipment_id": shipment_id})
        if row:
            return row_to_record(models.Customer, row)
        raise RecordNotFound(f"No Entity for shipment_id={shipment_id}")

    def from_email(self, email: str) -> models.Customer:
        """
        Get customer entity by email address.

        Args:
            email: Email address associated with the customer.

        Returns:
            The customer entity associated with the given email address.

        Raises:
            RecordNotFound: If no customer is associated with the given email address.
        """

        query = (
            self._query.from_(self._table)
            .select(self._table.star)
            .where(self._table.email == Parameter(":email"))
        )

        row = database.fetch_one(query.get_sql(), {"email": email})
        if row:
            return row_to_record(models.Customer, row)
        raise RecordNotFound(f"No Entity for email={email}")

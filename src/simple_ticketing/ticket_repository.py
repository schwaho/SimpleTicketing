"""
Repository for persisting and retrieving ticket entities.

This module provides the persistence operations for :class:`models.Ticket`
entities. It maps between domain models and database records while delegating
database access to the database abstraction layer.
"""

from typing import List, cast
from pypika import Table, functions as fn
from pypika.dialects import SQLLiteQuery as Query
from simple_ticketing import database
from simple_ticketing import models
from simple_ticketing.repository_mapping import row_to_record, rows_to_records, named_placeholders

_tickets = Table("tickets")
_credits = Table("credits")
_ticket_credits = Table("ticket_credits")
_shipment_tickets = Table("shipment_tickets")


def insert(record: models.Ticket) -> None:
    """
    Insert a new entity.

    Args:
        record: Ticket entity to persist.
    """
    record_dict = record.as_dict()
    del record_dict["id"]

    bindings = named_placeholders(record_dict)

    query = Query.into(_tickets).columns(*bindings.keys()).insert(*bindings.values())

    database.execute(query.get_sql(), record_dict)


def update(record: models.Ticket) -> None:
    """
    Update a existing ticket entity by its ID."

    Args:
        record: Ticket entity containing the updated values.
    """
    record_dict = record.as_dict()

    bindings = named_placeholders(record_dict, exclude_id=True)

    query = Query.update(_tickets)
    for col, val in bindings.items():
        query = query.set(col, val)
    query = query.where(_tickets.id == ":id")

    database.execute(query.get_sql(), record_dict)


def get(ticket_id: int) -> models.Ticket:
    """
    Get a ticket entity by its ID.

    Args:
        ticket_id: ID of the ticket to retrieve.

    Returns:
        The ticket entity matching the given ID.

    Raises:
        RuntimeError: If no ticket exists for the given ID.
    """

    query = Query.from_(_tickets).select("*").where(_tickets.id == ":ticket_id")

    row = database.fetch_one(query.get_sql(), {"ticket_id": ticket_id})

    if row:
        return row_to_record(models.Ticket, row)

    raise RuntimeError(f"No Entity for ticket_id={ticket_id}")


def get_all() -> List[models.Ticket]:
    """
    Get all ticket entities.

    Returns:
        A list containing all ticket entities.
    """

    query = Query.from_(_tickets).select("*")

    rows = database.fetch_all(query.get_sql())

    return rows_to_records(models.Ticket, rows)


def from_credit(credit_id: int) -> models.Ticket:
    """
    Get a ticket entity by its credit ID.

    Args:
        credit_id: ID of the credit associated with the ticket.

    Returns:
        The ticket entity associated with the given credit ID.

    Raises:
        RuntimeError: If no ticket is associated with the given credit ID.
    """

    query = (
        Query.from_(_tickets)
        .join(_ticket_credits)
        .on(_tickets.id == _ticket_credits.ticket_id)
        .select(_tickets.star)
        .where(_ticket_credits.credit_id == ":credit_id")
    )

    row = database.fetch_one(query.get_sql(), {"credit_id": credit_id})
    if row:
        return row_to_record(models.Ticket, row)
    raise RuntimeError(f"No Entity for credit_id={credit_id}")


def from_shipment(shipment_id: int) -> List[models.Ticket]:
    """
    Get ticket entities by their shipment ID.

    Args:
        shipment_id: ID of the shipment associated with the tickets.

    Returns:
        A list containing the ticket entities associated with the given
        shipment ID.
    """

    query = (
        Query.from_(_tickets)
        .join(_shipment_tickets)
        .on(_tickets.id == _shipment_tickets.ticket_id)
        .select(_tickets.star)
        .where(_shipment_tickets.shipment_id == ":shipment_id")
    )
    rows = database.fetch_all(query.get_sql(), {"shipment_id": shipment_id})

    return rows_to_records(models.Ticket, rows)


def from_customer(customer_id: int) -> List[models.Ticket]:
    """
    Get ticket entities by their customer ID.

    Args:
        customer_id: ID of the customer associated with the tickets.

    Returns:
        A list containing the ticket entities belonging to the given
        customer ID.
    """

    query = Query.from_(_tickets).select("*").where(_tickets.customer_id == ":customer_id")
    rows = database.fetch_all(query.get_sql(), {"customer_id": customer_id})

    return rows_to_records(models.Ticket, rows)


def from_offer(offer_id: int) -> List[models.Ticket]:
    """
    Get ticket entities by their offer ID.

    Args:
        offer_id: ID of the offer associated with the tickets.

    Returns:
        A list containing the ticket entities associated with the given
        offer ID.
    """

    query = Query.from_(_tickets).select("*").where(_tickets.offer_id == ":offer_id")
    rows = database.fetch_all(query.get_sql(), {"offer_id": offer_id})
    return rows_to_records(models.Ticket, rows)


def total_credit_amount(ticket_id: int) -> int:
    """Get the total credit amount for a ticket.

    Args:
        ticket_id: ID of the ticket for which to calculate the total credit
            amount.

    Returns:
        The total amount of all credits associated with the ticket, or 0 if
        no credits are associated with the ticket.
    """

    query = (
        Query.from_(_credits)
        .join(_ticket_credits)
        .on(_credits.id == _ticket_credits.credit_id)
        .select(
            fn.Coalesce(fn.Sum(_credits.amount), 0).as_(  # type: ignore[no-untyped-call]
                "total_credit_amount"
            )
        )
        .where(_ticket_credits.ticket_id == ":ticket_id")
    )
    row = database.fetch_one(query.get_sql(), {"ticket_id": ticket_id})

    if row:
        total = cast(int, row.get("total_credit_amount", 0))
        return total
    return 0

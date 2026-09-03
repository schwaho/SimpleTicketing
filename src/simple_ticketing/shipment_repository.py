"""
Repository for persisting and retrieving shipment entities.

This module provides the persistence operations for :class:`models.Shipment`
entities. It maps between domain models and database records while delegating
database access to the database abstraction layer.
"""

from typing import List
from pypika import Table
from pypika.dialects import SQLLiteQuery as Query
from simple_ticketing import database
from simple_ticketing import models
from simple_ticketing.repository_mapping import row_to_record, rows_to_records, named_placeholders

_shipments = Table("shipments")
_shipment_tickets = Table("shipment_tickets")


def insert(record: models.Shipment) -> None:
    """
    Insert a new entity.

    Args:
        record: Shipment entity to persist.
    """
    record_dict = record.as_dict()
    del record_dict["id"]

    bindings = named_placeholders(record_dict)

    query = Query.into(_shipments).columns(*bindings.keys()).insert(*bindings.values())

    database.execute(query.get_sql(), record_dict)


def update(record: models.Shipment) -> None:
    """
    Update a existing shipment entity by its ID."

    Args:
        record: Shipment entity containing the updated values.
    """
    record_dict = record.as_dict()

    bindings = named_placeholders(record_dict, exclude_id=True)

    query = Query.update(_shipments)
    for col, val in bindings.items():
        query = query.set(col, val)
    query = query.where(_shipments.id == ":id")

    database.execute(query.get_sql(), record_dict)


def get(shipment_id: int) -> models.Shipment:
    """
    Get a credit entity by its ID.

    Args:
        shipment_id: ID of the shipment to retrieve.

    Returns:
        The shipment entity matching the given ID.

    Raises:
        RuntimeError: If no shipment exists for the given ID.
    """

    query = Query.from_(_shipments).select("*").where(_shipments.id == ":credit_id")

    row = database.fetch_one(query.get_sql(), {"shipment_id": shipment_id})

    if row:
        return row_to_record(models.Shipment, row)

    raise RuntimeError(f"No Entity for shipment_id={shipment_id}")


def get_all() -> List[models.Shipment]:
    """
    Get all shipment entities.

    Returns:
        A list containing all shipment entities.
    """

    query = Query.from_(_shipments).select("*")

    rows = database.fetch_all(query.get_sql())

    return rows_to_records(models.Shipment, rows)


def from_ticket(ticket_id: int) -> List[models.Shipment]:
    """
    Get shipment entities by ticket ID.

    Args:
        ticket_id: ID of the ticket associated with the shipment.

    Returns:
        A list containing the shipment entities associated with the given ticket ID.
    """

    query = (
        Query.from_(_shipments)
        .join(_shipment_tickets)
        .on(_shipments.id == _shipment_tickets.shipment_id)
        .select(_shipments.star)
        .where(_shipment_tickets.ticket_id == ":ticket_id")
    )

    rows = database.fetch_all(query.get_sql(), {"ticket_id": ticket_id})
    return rows_to_records(models.Shipment, rows)

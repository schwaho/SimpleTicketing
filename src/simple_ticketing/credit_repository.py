"""
Repository for persisting and retrieving credit entities.

This module provides the persistence operations for :class:`models.Credit`
entities. It maps between domain models and database records while delegating
database access to the database abstraction layer.
"""

from typing import List
from pypika import Table
from pypika.dialects import SQLLiteQuery as Query
from simple_ticketing import database
from simple_ticketing import models
from simple_ticketing.repository_mapping import row_to_record, rows_to_records, named_placeholders

_credits = Table("credits")
_payment_credits = Table("payment_credits")
_ticket_credits = Table("ticket_credits")


def insert(record: models.Credit) -> None:
    """
    Insert a new entity.

    Args:
        record: Credit entity to persist.
    """
    record_dict = record.as_dict()
    del record_dict["id"]

    bindings = named_placeholders(record_dict)

    query = Query.into(_credits).columns(*bindings.keys()).insert(*bindings.values())

    database.execute(query.get_sql(), record_dict)


def update(record: models.Credit) -> None:
    """
    Update a existing credit entity by its ID."

    Args:
        record: Credit entity containing the updated values.
    """
    record_dict = record.as_dict()

    bindings = named_placeholders(record_dict, exclude_id=True)

    query = Query.update(_credits)
    for col, val in bindings.items():
        query = query.set(col, val)
    query = query.where(_credits.id == ":id")

    database.execute(query.get_sql(), record_dict)


def get(credit_id: int) -> models.Credit:
    """
    Get a credit entity by its ID.

    Args:
        credit_id: ID of the credit to retrieve.

    Returns:
        The credit entity matching the given ID.

    Raises:
        RuntimeError: If no credit exists for the given ID.
    """

    query = Query.from_(_credits).select("*").where(_credits.id == ":credit_id")

    row = database.fetch_one(query.get_sql(), {"credit_id": credit_id})

    if row:
        return row_to_record(models.Credit, row)

    raise RuntimeError(f"No Entity for credit_id={credit_id}")


def get_all() -> List[models.Credit]:
    """
    Get all credit entities.

    Returns:
        A list containing all credit entities.
    """

    query = Query.from_(_credits).select("*")

    rows = database.fetch_all(query.get_sql())

    return rows_to_records(models.Credit, rows)


def from_payment(payment_id: int) -> List[models.Credit]:
    """
    Get credit entities by payment ID.

    Args:
        payment_id: ID of the payment associated with the credit.

    Returns:
        A list containing the credit entities associated with the given payment ID.
    """

    query = (
        Query.from_(_credits)
        .join(_payment_credits)
        .on(_credits.id == _payment_credits.credit_id)
        .select(_credits.star)
        .where(_payment_credits.payment_id == ":payment_id")
    )

    rows = database.fetch_all(query.get_sql(), {"payment_id": payment_id})
    return rows_to_records(models.Credit, rows)


def from_ticket(ticket_id: int) -> List[models.Credit]:
    """
    Get credit entities by ticket ID.

    Args:
        ticket_id: ID of the ticket associated with the credit.

    Returns:
        A list containing the credit entities associated with the given ticket ID.
    """

    query = (
        Query.from_(_credits)
        .join(_ticket_credits)
        .on(_credits.id == _ticket_credits.credit_id)
        .select(_credits.star)
        .where(_ticket_credits.ticket_id == ":ticket_id")
    )

    rows = database.fetch_all(query.get_sql(), {"ticket_id": ticket_id})
    return rows_to_records(models.Credit, rows)

"""
Repository for persisting and retrieving customer entities.

This module provides the persistence operations for :class:`models.Customer`
entities. It maps between domain models and database records while delegating
database access to the database abstraction layer.
"""

from typing import List
from pypika import Table
from pypika.dialects import SQLLiteQuery as Query
from simple_ticketing import database
from simple_ticketing import models
from simple_ticketing.repository_mapping import row_to_record, rows_to_records, named_placeholders

_customers = Table("customers")


def insert(record: models.Customer) -> None:
    """
    Insert a new entity.

    Args:
        record: Customer entity to persist.
    """

    record_dict = record.as_dict()
    del record_dict["id"]

    bindings = named_placeholders(record_dict)

    query = Query.into(_customers).columns(*bindings.keys()).insert(*bindings.values())

    database.execute(query.get_sql(), record_dict)


def update(record: models.Customer) -> None:
    """
    Update a existing customer entity by its ID."

    Args:
        record: Customer entity containing the updated values.
    """

    record_dict = record.as_dict()

    bindings = named_placeholders(record_dict, exclude_id=True)

    query = Query.update(_customers)
    for col, val in bindings.items():
        query = query.set(col, val)
    query = query.where(_customers.id == ":id")

    database.execute(query.get_sql(), record_dict)


def get(customer_id: int) -> models.Customer:
    """
    Get a customer entity by its ID.

    Args:
        customer_id: ID of the customer to retrieve.

    Returns:
        The customer entity matching the given ID.

    Raises:
        RuntimeError: If no customer exists for the given ID.
    """

    query = Query.from_(_customers).select("*").where(_customers.id == ":customer_id")

    row = database.fetch_one(query.get_sql(), {"customer_id": customer_id})

    if row:
        return row_to_record(models.Customer, row)

    raise RuntimeError(f"No Entity for customer_id={customer_id}")


def get_all() -> List[models.Customer]:
    """
    Get all customer entities.

    Returns:
        A list containing all customer entities.
    """

    query = Query.from_(_customers).select("*")

    rows = database.fetch_all(query.get_sql())

    return rows_to_records(models.Customer, rows)

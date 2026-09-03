"""
Repository for persisting and retrieving offer entities.

This module provides the persistence operations for :class:`models.Offer`
entities. It maps between domain models and database records while delegating
database access to the database abstraction layer.
"""

from typing import List
from pypika import Table
from pypika.dialects import SQLLiteQuery as Query
from simple_ticketing import database
from simple_ticketing import models
from simple_ticketing.repository_mapping import row_to_record, rows_to_records, named_placeholders

_offers = Table("offers")
_payment_offers = Table("payment_offers")


def insert(record: models.Offer) -> None:
    """
    Insert a new entity.

    Args:
        record: Offer entity to persist.
    """
    record_dict = record.as_dict()
    del record_dict["id"]

    bindings = named_placeholders(record_dict)

    query = Query.into(_offers).columns(*bindings.keys()).insert(*bindings.values())

    database.execute(query.get_sql(), record_dict)


def update(record: models.Offer) -> None:
    """
    Update a existing offer entity by its ID."

    Args:
        record: Offer entity containing the updated values.
    """
    record_dict = record.as_dict()

    bindings = named_placeholders(record_dict, exclude_id=True)

    query = Query.update(_offers)
    for col, val in bindings.items():
        query = query.set(col, val)
    query = query.where(_offers.id == ":id")

    database.execute(query.get_sql(), record_dict)


def get(offer_id: int) -> models.Offer:
    """
    Get a offer entity by its ID.

    Args:
        offer_id: ID of the offer to retrieve.

    Returns:
        The offer entity matching the given ID.

    Raises:
        RuntimeError: If no offer exists for the given ID.
    """

    query = Query.from_(_offers).select("*").where(_offers.id == ":offer_id")

    row = database.fetch_one(query.get_sql(), {"offer_id": offer_id})

    if row:
        return row_to_record(models.Offer, row)

    raise RuntimeError(f"No Entity for offer_id={offer_id}")


def get_all() -> List[models.Offer]:
    """
    Get all offer entities.

    Returns:
        A list containing all offer entities.
    """

    query = Query.from_(_offers).select("*")

    rows = database.fetch_all(query.get_sql())

    return rows_to_records(models.Offer, rows)


def from_customer(customer_id: int) -> List[models.Offer]:
    """
    Get offer entities by customer ID.

    Args:
        customer_id: ID of the customer associated with the offer.

    Returns:
        A list containing the offer entities associated with the given customer ID.
    """

    query = Query.from_(_offers).select("*").where(_offers.customer_id == ":customer_id")

    rows = database.fetch_all(query.get_sql(), {"customer_id": customer_id})
    return rows_to_records(models.Offer, rows)


def from_payment(payment_id: int) -> List[models.Offer]:
    """
    Get offer entities by payment ID.

    Args:
        payment_id: ID of the payment associated with the offer.

    Returns:
        A list containing the offer entities associated with the given payment ID.
    """

    query = (
        Query.from_(_offers)
        .join(_payment_offers)
        .on(_offers.id == _payment_offers.offer_id)
        .select(_offers.star)
        .where(_offers.payment_id == ":payment_id")
    )

    rows = database.fetch_all(query.get_sql(), {"payment_id": payment_id})
    return rows_to_records(models.Offer, rows)

"""
Repository for persisting and retrieving payment entities.

This module provides the persistence operations for :class:`models.Payment`
entities. It maps between domain models and database records while delegating
database access to the database abstraction layer.
"""

from typing import List
from pypika import Table
from pypika.dialects import SQLLiteQuery as Query
from simple_ticketing import database
from simple_ticketing import models
from simple_ticketing.repository_mapping import row_to_record, rows_to_records, named_placeholders

_payments = Table("payments")
_payment_offers = Table("payment_offers")
_payment_credits = Table("payment_credits")


def insert(record: models.Payment) -> None:
    """
    Insert a new entity.

    Args:
        record: Payment entity to persist.
    """
    record_dict = record.as_dict()
    del record_dict["id"]

    bindings = named_placeholders(record_dict)

    query = Query.into(_payments).columns(*bindings.keys()).insert(*bindings.values())

    database.execute(query.get_sql(), record_dict)


def update(record: models.Payment) -> None:
    """
    Update a existing payment entity by its ID."

    Args:
        record: Payment entity containing the updated values.
    """
    record_dict = record.as_dict()

    bindings = named_placeholders(record_dict, exclude_id=True)

    query = Query.update(_payments)
    for col, val in bindings.items():
        query = query.set(col, val)
    query = query.where(_payments.id == ":id")

    database.execute(query.get_sql(), record_dict)


def get(payment_id: int) -> models.Payment:
    """
    Get a payment entity by its ID.

    Args:
        payment_id: ID of the payment to retrieve.

    Returns:
        The payment entity matching the given ID.

    Raises:
        RuntimeError: If no payment exists for the given ID.
    """

    query = Query.from_(_payments).select("*").where(_payments.id == ":payment_id")

    row = database.fetch_one(query.get_sql(), {"payment_id": payment_id})

    if row:
        return row_to_record(models.Payment, row)

    raise RuntimeError(f"No Entity for payment_id={payment_id}")


def get_all() -> List[models.Payment]:
    """
    Get all payment entities.

    Returns:
        A list containing all payment entities.
    """

    query = Query.from_(_payments).select("*")

    rows = database.fetch_all(query.get_sql())

    return rows_to_records(models.Payment, rows)


def from_customer(customer_id: int) -> List[models.Payment]:
    """
    Get payment entities by customer ID.

    Args:
        customer_id: ID of the customer associated with the payment.

    Returns:
        A list containing the payment entities associated with the given customer ID.
    """

    query = Query.from_(_payments).select("*").where(_payments.customer_id == ":customer_id")

    rows = database.fetch_all(query.get_sql(), {"customer_id": customer_id})
    return rows_to_records(models.Payment, rows)


def from_offer(offer_id: int) -> List[models.Payment]:
    """
    Get payment entities by offer ID.

    Args:
        offer_id: ID of the offer associated with the payment.

    Returns:
        A list containing the payment entities associated with the given offer ID.
    """

    query = (
        Query.from_(_payments)
        .join(_payment_offers)
        .on(_payments.id == _payment_offers.payment_id)
        .select(_payments.star)
        .where(_payment_offers.offer_id == ":offer_id")
    )

    rows = database.fetch_all(query.get_sql(), {"offer_id": offer_id})
    return rows_to_records(models.Payment, rows)


def from_credit(credit_id: int) -> List[models.Payment]:
    """
    Get payment entities by credit ID.

    Args:
        credit_id: ID of the credit associated with the payment.

    Returns:
        A list containing the payment entities associated with the given credit ID.
    """

    query = (
        Query.from_(_payments)
        .join(_payment_credits)
        .on(_payments.id == _payment_credits.payment_id)
        .select(_payments.star)
        .where(_payment_credits.credit_id == ":credit_id")
    )

    rows = database.fetch_all(query.get_sql(), {"credit_id": credit_id})
    return rows_to_records(models.Payment, rows)

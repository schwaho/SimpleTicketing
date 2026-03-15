"""
SQLite table schema definitions.

This module provides helper functions for creating application tables.
Each table is defined by a dedicated function that specifies its columns
and delegates SQL generation to ``create_table``.

The module only ensures that tables exist using ``CREATE TABLE IF NOT EXISTS``.
It does not perform schema validation, migrations, or enforce business logic.
"""

import logging
from typing import Mapping
from simple_ticketing.database import execute

logger = logging.getLogger(__name__)


def create_all_tables() -> None:
    """
    Create all required application tables if they do not already exist.

    This function initializes the database schema by invoking the
    individual table creation helpers defined in this module.
    """
    create_tickets_table()
    create_customers_table()
    create_offers_table()
    create_payments_table()
    create_credits_table()
    create_shipments_table()

    create_payment_credits_table()
    create_payment_offers_table()
    create_shipment_tickets_table()
    create_ticket_credits_table()


def create_table(
    *,
    table_name: str,
    columns: Mapping[str, str],
) -> None:
    """
    Creates a SQLite table if it does not already exist.

    The function generates and executes a ``CREATE TABLE IF NOT EXISTS`` statement
    based solely on the provided column definitions using the database execution layer.
    No constraints, migrations, or schema validation are applied.
    The database is treated as a passive storage layer without embedded business logic.

    Args:
        table_name: Name of the table to be created.
        columns: Mapping of column names to their SQLite column definitions
            (e.g. ``{"id": "INTEGER PRIMARY KEY", "created_at": "DATETIME"}``).
    """
    logger.debug(
        "Creating table '%s' with %d columns.",
        table_name,
        len(columns),
    )

    columns_sql = ",\n    ".join(f"{name} {definition}" for name, definition in columns.items())

    sql = f"""
    CREATE TABLE IF NOT EXISTS {table_name} (
        {columns_sql}
    )
    """

    logger.debug(
        "Executing SQL for table '%s':\n%s",
        table_name,
        sql.strip(),
    )

    execute(sql)
    logger.debug("Table '%s' verified/created.", table_name)


def create_tickets_table() -> None:
    """Create the 'tickets' table if it does not exist."""
    create_table(
        table_name="tickets",
        columns={
            "id": "INTEGER PRIMARY KEY",
            "ticket_code": "TEXT NOT NULL UNIQUE",
            "seat_type": "TEXT NOT NULL",
            "target_amount": "INTEGER NOT NULL",
            "customer_id": "INTEGER NOT NULL",
            "offer_id": "INTEGER NOT NULL",
            "check_in_at": "DATETIME",
            "cancelled_at": "DATETIME",
            "created_at": "DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP",
        },
    )


def create_customers_table() -> None:
    """Create the 'customers' table if it does not exist."""
    create_table(
        table_name="customers",
        columns={
            "id": "INTEGER PRIMARY KEY",
            "name": "TEXT NOT NULL",
            "email": "TEXT NOT NULL UNIQUE",
            "created_at": "DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP",
        },
    )


def create_offers_table() -> None:
    """Create the 'offers' table if it does not exist."""
    create_table(
        table_name="offers",
        columns={
            "id": "INTEGER PRIMARY KEY",
            "offer_code": "TEXT NOT NULL UNIQUE",
            "customer_id": "INTEGER NOT NULL",
            "ticket_count": "INTEGER NOT NULL",
            "ticket_price": "INTEGER NOT NULL",
            "valid_until": "DATETIME",
            "created_at": "DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP",
        },
    )


def create_payments_table() -> None:
    """Create the 'payments' table if it does not exist."""
    create_table(
        table_name="payments",
        columns={
            "id": "INTEGER PRIMARY KEY",
            "customer_id": "INTEGER NOT NULL",
            "amount": "INTEGER NOT NULL",
            "payment_ref": "TEXT",
            "created_at": "DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP",
        },
    )


def create_payment_offers_table() -> None:
    """Create the 'payment_offers' table if it does not exist."""
    create_table(
        table_name="payment_offers",
        columns={
            "id": "INTEGER PRIMARY KEY",
            "payment_id": "INTEGER NOT NULL",
            "offer_id": "INTEGER NOT NULL",
        },
    )


def create_credits_table() -> None:
    """Create the 'credits' table if it does not exist."""
    create_table(
        table_name="credits",
        columns={
            "id": "INTEGER PRIMARY KEY",
            "customer_id": "INTEGER NOT NULL",
            "amount": "INTEGER NOT NULL",
            "reason": "TEXT",
            "created_at": "DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP",
        },
    )


def create_payment_credits_table() -> None:
    """Create the 'payment_credits' table if it does not exist."""
    create_table(
        table_name="payment_credits",
        columns={
            "id": "INTEGER PRIMARY KEY",
            "payment_id": "INTEGER NOT NULL",
            "credit_id": "INTEGER NOT NULL",
        },
    )


def create_ticket_credits_table() -> None:
    """Create the 'ticket_credits' table if it does not exist."""
    create_table(
        table_name="ticket_credits",
        columns={
            "id": "INTEGER PRIMARY KEY",
            "ticket_id": "INTEGER NOT NULL",
            "credit_id": "INTEGER NOT NULL",
        },
    )


def create_shipments_table() -> None:
    """Create the 'shipments' table if it does not exist."""
    create_table(
        table_name="shipments",
        columns={
            "id": "INTEGER PRIMARY KEY",
            "customer_id": "INTEGER NOT NULL",
            "sent_at": "DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP",
        },
    )


def create_shipment_tickets_table() -> None:
    """Create the 'shipment_tickets' table if it does not exist."""
    create_table(
        table_name="shipment_tickets",
        columns={
            "id": "INTEGER PRIMARY KEY",
            "shipment_id": "INTEGER NOT NULL",
            "ticket_id": "INTEGER NOT NULL",
        },
    )

"""
Unit tests for the `simple_ticketing.database` module.
"""

import sqlite3
from typing import Dict, Any, Tuple
from unittest.mock import patch, MagicMock
import pytest
from simple_ticketing.database import (
    db_get_connection,
    execute_query,
    db_fetch_tickets,
    db_commit_ticket,
    db_init,
    db_clear,
)


def test_db_get_connection() -> None:
    """
    Tests db_get_connection() to ensure a valid SQLite connection is returned.

    - Mocks sqlite3.connect to return a MagicMock connection.
    - Asserts that the connection is established and has the correct row_factory.
    - Simulates a DatabaseError and ensures it is properly raised.
    """
    mock_conn = MagicMock()
    mock_conn.row_factory = sqlite3.Row

    with patch("sqlite3.connect", return_value=mock_conn):
        conn = db_get_connection()
        assert conn == mock_conn
        assert conn.row_factory == sqlite3.Row

    with patch("sqlite3.connect", side_effect=sqlite3.DatabaseError("Connection failed")):
        with pytest.raises(sqlite3.DatabaseError, match="Connection failed"):
            db_get_connection()


def test_execute_query_fetch() -> None:
    """
    Tests execute_query() in fetch mode.

    - Mocks db_get_connection() and cursor to simulate fetching data.
    - Ensures the function returns a list of dictionaries.
    - Simulates an OperationalError and verifies it is raised.
    """
    mock_conn = MagicMock()
    mock_cursor = MagicMock()

    mock_conn.cursor.return_value = mock_cursor

    mock_cursor.fetchall.return_value = [
        {"id": 1, "name": "Alice"},
        {"id": 2, "name": "Bob"},
    ]

    with patch("simple_ticketing.database.db_get_connection", return_value=mock_conn):
        result = execute_query("SELECT * FROM users", fetch=True)
        assert result == [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]
        mock_cursor.execute.assert_called_once_with("SELECT * FROM users", ())

    with (
        patch("simple_ticketing.database.db_get_connection", return_value=mock_conn),
        patch.object(mock_cursor, "execute", side_effect=sqlite3.OperationalError("SQL error")),
    ):
        with pytest.raises(sqlite3.OperationalError, match="SQL error"):
            execute_query("SELECT * FROM users", fetch=True)


def test_execute_query_commit() -> None:
    """
    Tests execute_query() in commit mode.

    - Mocks db_get_connection() and ensures commit is called.
    - Simulates an IntegrityError and verifies it is raised.
    """
    mock_conn = MagicMock()
    mock_cursor = MagicMock()

    mock_conn.cursor.return_value = mock_cursor

    with patch("simple_ticketing.database.db_get_connection", return_value=mock_conn):
        execute_query("INSERT INTO users (name) VALUES (?)", ("Alice",), fetch=False)
        mock_cursor.execute.assert_called_once_with(
            "INSERT INTO users (name) VALUES (?)", ("Alice",)
        )
        mock_conn.commit.assert_called_once()

    with (
        patch("simple_ticketing.database.db_get_connection", return_value=mock_conn),
        patch.object(
            mock_cursor, "execute", side_effect=sqlite3.IntegrityError("Constraint failed")
        ),
    ):
        with pytest.raises(sqlite3.IntegrityError, match="Constraint failed"):
            execute_query("INSERT INTO users (name) VALUES (?)", ("Alice",), fetch=False)


def test_execute_query_prevent_sql_injection() -> None:
    """
    Ensures execute_query() does not allow SQL injection.
    """
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor

    with patch("simple_ticketing.database.db_get_connection", return_value=mock_conn):
        execute_query("SELECT * FROM users WHERE name = ?", ("' OR 1=1 --",), fetch=True)
        mock_cursor.execute.assert_called_once_with(
            "SELECT * FROM users WHERE name = ?", ("' OR 1=1 --",)
        )


def test_db_fetch_tickets_no_filters() -> None:
    """
    Tests db_fetch_tickets() without filters.

    - Mocks execute_query() to return a list of ticket dictionaries.
    - Ensures the function calls execute_query() correctly.
    """
    mock_tickets = [
        {"id": 1, "name": "Alice", "seat_type": "VIP"},
        {"id": 2, "name": "Bob", "seat_type": "Regular"},
    ]

    with patch("simple_ticketing.database.execute_query", return_value=mock_tickets) as mock_exec:
        result = db_fetch_tickets()
        assert result == mock_tickets
        mock_exec.assert_called_once_with("SELECT * FROM tickets", (), fetch=True)


def test_db_fetch_tickets_with_filters() -> None:
    """
    Tests db_fetch_tickets() with valid filters.

    - Mocks execute_query() to return filtered ticket results.
    - Ensures query formation is correct.
    """
    mock_tickets = [{"id": 1, "name": "Alice", "seat_type": "VIP"}]

    with patch("simple_ticketing.database.execute_query", return_value=mock_tickets) as mock_exec:
        result = db_fetch_tickets(filters={"seat_type": "VIP"})
        assert result == mock_tickets
        mock_exec.assert_called_once_with(
            "SELECT * FROM tickets WHERE seat_type = ?", ("VIP",), fetch=True
        )


def test_db_fetch_tickets_invalid_filter() -> None:
    """
    Tests db_fetch_tickets() with an invalid column in filters.

    - Ensures ValueError is raised for invalid column names.
    """
    with pytest.raises(ValueError, match="Invalid column name in filter: invalid_column"):
        db_fetch_tickets(filters={"invalid_column": "VIP"})


def test_db_fetch_tickets_invalid_order_by() -> None:
    """
    Tests db_fetch_tickets() with an invalid column in order_by.

    - Ensures ValueError is raised for invalid column names.
    """
    with pytest.raises(ValueError, match="Invalid column name in order_by: invalid_column"):
        db_fetch_tickets(order_by=["invalid_column"])


def test_db_fetch_tickets_empty_result() -> None:
    """
    Tests db_fetch_tickets() when no tickets exist.

    - Ensures function handles empty database correctly.
    """
    with patch("simple_ticketing.database.execute_query", return_value=[]) as mock_exec:
        result = db_fetch_tickets()
        assert result == []  # Sollte eine leere Liste zurückgeben, nicht None
        mock_exec.assert_called_once_with("SELECT * FROM tickets", (), fetch=True)


def test_db_fetch_tickets_database_error() -> None:
    """
    Tests db_fetch_tickets() when a database error occurs.

    - Mocks execute_query() to raise a DatabaseError.
    - Ensures the function handles the error and returns None.
    """
    with patch(
        "simple_ticketing.database.execute_query",
        side_effect=sqlite3.DatabaseError("DB error"),
    ):
        with pytest.raises(RuntimeError) as exc_info:
            db_fetch_tickets()

        assert "Database Error: DB error" in str(exc_info.value)


@pytest.mark.parametrize(
    "operation, data, conditions, expected_query, expected_params",
    [
        (
            "INSERT",
            {"name": "Alice", "seat_type": "VIP"},
            None,
            "INSERT INTO tickets (name, seat_type) VALUES (?, ?)",
            ("Alice", "VIP"),
        ),
        (
            "UPDATE",
            {"seat_type": "VIP"},
            {"id": 1},
            "UPDATE tickets SET seat_type = ? WHERE id = ?",
            ("VIP", 1),
        ),
        (
            "DELETE",
            None,
            {"id": 1},
            "DELETE FROM tickets WHERE id = ?",
            (1,),
        ),
    ],
)
def test_db_commit_ticket_success(
    operation: str,
    data: Dict[Any, Any],
    conditions: Dict[Any, Any],
    expected_query: str,
    expected_params: Tuple[Any, Any],
) -> None:
    """
    Tests db_commit_ticket() for successful INSERT, UPDATE, and DELETE operations.

    - Verifies correct SQL query generation and parameters.
    - Ensures no exception is raised on success.
    - Uses parameterization to test multiple operations in a single, unified test.
    """
    with patch("simple_ticketing.database.execute_query") as mock_exec:
        mock_exec.return_value = None

        db_commit_ticket(operation, data=data, conditions=conditions)
        mock_exec.assert_called_once_with(expected_query, expected_params, fetch=False)


@pytest.mark.parametrize(
    "operation, data, conditions, expected_exception, expected_msg",
    [
        ("WRONG_OP", {}, {}, ValueError, "Invalid operation: WRONG_OP"),
        ("INSERT", {}, {}, ValueError, "INSERT operation requires data."),
        ("UPDATE", {}, {"id": 1}, ValueError, "UPDATE operation requires data."),
        (
            "UPDATE",
            {"name": "Alice"},
            {},
            ValueError,
            "UPDATE operation requires a WHERE condition.",
        ),
        ("DELETE", {}, {}, ValueError, "DELETE operation requires a WHERE condition."),
        ("INSERT", {"invalid_column": "value"}, {}, ValueError, "Invalid column name"),
        ("DELETE", {}, {"invalid_column": "val"}, ValueError, "Invalid column name"),
    ],
)
def test_db_commit_ticket_exceptions(
    operation: str,
    data: Dict[Any, Any],
    conditions: Dict[Any, Any],
    expected_exception: Any,
    expected_msg: str,
) -> None:
    """
    Tests that db_commit_ticket raises appropriate exceptions for invalid input parameters.

    This parametrized test covers various error cases including:
    - Invalid operation types.
    - Missing required 'data' for INSERT and UPDATE operations.
    - Missing required 'conditions' for UPDATE and DELETE operations.
    - Invalid column names in 'data' or 'conditions'.
    """
    with pytest.raises(expected_exception) as exc_info:
        db_commit_ticket(operation, data, conditions)

    assert expected_msg in str(exc_info.value)


def test_db_commit_ticket_database_error() -> None:
    """
    Tests db_commit_ticket() when a database error occurs.

    - Mocks execute_query() to raise a DatabaseError.
    - Ensures the function handles the error and returns False.
    """
    with patch(
        "simple_ticketing.database.execute_query",
        side_effect=sqlite3.DatabaseError("DB error"),
    ):
        with pytest.raises(RuntimeError):
            db_commit_ticket("INSERT", data={"name": "Alice"})


def test_db_init() -> None:
    """
    Tests db_init() to ensure database initialization runs correctly.

    - Mocks db_get_connection() and create_tickets_table().
    - Ensures the database connection and cursor are used properly.
    - Ensures the commit method is called to apply changes.
    """
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor

    with (
        patch("simple_ticketing.database.db_get_connection", return_value=mock_conn),
        patch("simple_ticketing.database.create_tickets_table") as mock_create_table,
    ):

        db_init()

        # Check that connection and cursor were created
        mock_conn.cursor.assert_called_once()

        # Ensure create_tickets_table() was called correctly
        mock_create_table.assert_called_once_with(mock_cursor)

        # Ensure commit and close are called
        mock_conn.commit.assert_called_once()
        mock_conn.close.assert_called_once()


def test_db_clear() -> None:
    """
    Tests db_clear() to ensure all table contents are deleted while retaining the structure.

    - Mocks db_get_connection() and get_table_names().
    - Ensures DELETE statements are executed for each table.
    - Ensures commit and close are properly called.
    """
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor

    mock_tables = ["tickets", "users", "events"]

    with (
        patch("simple_ticketing.database.db_get_connection", return_value=mock_conn),
        patch("simple_ticketing.database.get_table_names", return_value=mock_tables),
    ):

        db_clear()

        # Ensure get_table_names() was called
        mock_cursor.execute.assert_any_call('DELETE FROM "tickets";')
        mock_cursor.execute.assert_any_call('DELETE FROM "users";')
        mock_cursor.execute.assert_any_call('DELETE FROM "events";')

        # Ensure commit and close are called
        mock_conn.commit.assert_called_once()
        mock_conn.close.assert_called_once()


def test_db_clear_database_error() -> None:
    """
    Tests db_clear() when a database error occurs.

    - Mocks db_get_connection() and forces an exception on execute().
    - Ensures the function does not crash but properly handles errors.
    """
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor

    mock_cursor.execute.side_effect = sqlite3.DatabaseError("DB error")

    with (
        patch("simple_ticketing.database.db_get_connection", return_value=mock_conn),
        patch("simple_ticketing.database.get_table_names", return_value=["tickets"]),
    ):

        db_clear()  # Should not raise an exception despite the error

        # Ensure execute was attempted but errored
        mock_cursor.execute.assert_called_once_with('DELETE FROM "tickets";')

        # Ensure commit and close are still called
        mock_conn.commit.assert_called_once()
        mock_conn.close.assert_called_once()

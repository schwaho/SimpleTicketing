"""
This module provides a set of utility functions for managing an SQLite database
used for ticket management. It includes functions to establish database connections,
execute queries, initialize database schema, and reset database contents.

Features:
- Establishes and manages connections to the SQLite database.
- Executes SQL queries, including both retrieval (SELECT) and modification (INSERT, UPDATE, DELETE).
- Initializes the database by creating necessary tables if they do not exist.
- Provides helper functions for fetching, committing, and clearing ticket records.
"""

import os
import logging
import sqlite3
from contextlib import contextmanager
from contextvars import ContextVar
from typing import List, Tuple, Any, Dict, Optional, Iterator, Union

logger = logging.getLogger(__name__)

COLUMN_DEFINITIONS = {
    "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
    "name": "TEXT NOT NULL",
    "email": "TEXT NOT NULL",
    "seat_type": "TEXT NOT NULL",
    "ticket_code": "TEXT UNIQUE NOT NULL",
    "created_at": "DATETIME DEFAULT CURRENT_TIMESTAMP",
    "paid_at": "DATETIME DEFAULT NULL",
    "delivered_at": "DATETIME DEFAULT NULL",
    "check_in_at": "DATETIME DEFAULT NULL",
    "hidden": "BOOLEAN DEFAULT FALSE",
}

_current_connection: ContextVar[Optional[sqlite3.Connection]] = ContextVar(
    "current_db_connection",
    default=None,
)


def open_connection(db_path: str) -> None:
    """
    Open a SQLite database connection and store it in the thread-local context.

    Args:
        db_path: Path to the SQLite database file.

    Raises:
        sqlite3.Error: If the connection cannot be established.
    """
    conn = sqlite3.connect(
        db_path,
        isolation_level=None,
    )
    conn.row_factory = sqlite3.Row
    _current_connection.set(conn)


def get_connection() -> sqlite3.Connection:
    """
    Retrieve the current SQLite database connection from the thread-local context.

    Returns:
        sqlite3.Connection: The active database connection.

    Raises:
        RuntimeError: If no connection has been initialized.
    """
    conn = _current_connection.get()
    if conn is None:
        raise RuntimeError("Database connection not initialized")
    return conn


def close_connection() -> None:
    """
    Close the current SQLite database connection and clear the thread-local context.

    Does nothing if no connection is currently open.
    """
    conn = _current_connection.get()
    if conn is not None:
        conn.close()
        _current_connection.set(None)


@contextmanager
def transaction() -> Iterator[None]:
    """
    Execute multiple database operations atomically.

    All statements executed within this context are part of a single
    database transaction. If an exception is raised, the transaction
    is rolled back. Otherwise, it is committed.

    Raises:
        sqlite3.DatabaseError: If committing or rolling back fails.
    """
    conn = get_connection()

    try:
        logger.debug("BEGIN TRANSACTION")
        conn.execute("BEGIN")

        yield

    except sqlite3.DatabaseError as e:
        logger.debug("ROLLBACK TRANSACTION")
        conn.rollback()
        raise e

    logger.debug("COMMIT TRANSACTION")
    conn.commit()


def execute(sql: str, params: Optional[Union[Tuple[Any, ...], Dict[str, Any]]] = None) -> None:
    """Execute a single SQL statement without returning a result.

    This function is the lowest-level execution primitive. It is responsible
    for parameter binding, execution, error handling, and logging. It must not
    encode any domain knowledge or assumptions about the queried data.

    Args:
        sql: The SQL statement to execute.
        params: Optional positional or named parameters for the SQL statement.

    Raises:
        sqlite3.DatabaseError: If execution fails for any reason.
    """
    conn = get_connection()
    try:
        if params is not None:
            logger.debug("Executing SQL: %s with params: %s", sql, params)
            conn.execute(sql, params)
        else:
            logger.debug("Executing SQL: %s", sql)
            conn.execute(sql)
    except sqlite3.DatabaseError:
        logger.exception("Database execution failed.")
        raise


def execute_many(sql: str, params: List[Union[Tuple[Any, ...], Dict[str, Any]]]) -> None:
    """Execute the same SQL statement multiple times with different parameters.

    Intended for batch inserts or updates. This function does not implement
    any domain-specific batching logic.

    Args:
        sql: The SQL statement to execute.
        params: A list of parameter sets (positional or named) to apply to the SQL statement.

    Raises:
        sqlite3.DatabaseError: If execution fails for any reason.
    """
    if not params:
        logger.debug("execute_many called with empty params list.")
        return

    conn = get_connection()
    try:
        logger.debug("Executing SQL many times: %s with %d parameter sets", sql, len(params))
        conn.executemany(sql, params)
    except sqlite3.DatabaseError:
        logger.exception("Database batch execution failed.")
        raise


def fetch_one(
    sql: str, params: Optional[Union[Tuple[Any, ...], Dict[str, Any]]] = None
) -> Optional[Dict[str, Any]]:
    """Execute a SQL query and return a single row.

    If the query yields no result, None is returned. If multiple rows are
    returned by the query, only the first row is returned.

    Args:
        sql: The SQL SELECT statement to execute.
        params: Optional positional or named parameters for the SQL statement.

    Returns:
        A single row represented as a mapping, or None if no row was found.

    Raises:
        sqlite3.DatabaseError: If execution fails for any reason.
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        logger.debug("Executing SQL (fetch_one): %s with params: %s", sql, params)
        if params:
            cursor.execute(sql, params)
        else:
            cursor.execute(sql)
        row = cursor.fetchone()
        if row is None:
            return None
        return dict(row)
    except sqlite3.DatabaseError:
        logger.exception("Database query failed (fetch_one).")
        raise
    finally:
        cursor.close()


def fetch_all(
    sql: str, params: Optional[Union[Tuple[Any, ...], Dict[str, Any]]] = None
) -> List[Dict[str, Any]]:
    """Execute a SQL query and return all resulting rows.

    The database layer does not interpret or post-process results. Ordering,
    grouping, and semantic meaning are the responsibility of the caller.

    Args:
        sql: The SQL SELECT statement to execute.
        params: Optional positional or named parameters for the SQL statement.

    Returns:
        A list of rows represented as mappings. The list may be empty.

    Raises:
        sqlite3.DatabaseError: If execution fails for any reason.
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        logger.debug("Executing SQL (fetch_all): %s with params: %s", sql, params)
        if params:
            cursor.execute(sql, params)
        else:
            cursor.execute(sql)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.DatabaseError:
        logger.exception("Database query failed (fetch_all).")
        raise
    finally:
        cursor.close()


def db_get_connection() -> sqlite3.Connection:
    """
    Establishes a connection to the SQLite database.

    Returns:
        sqlite3.Connection: A connection object to the database, with rows represented
        as dictionaries.

    Raises:
        sqlite3.DatabaseError: If the connection to the database cannot be established.
    """
    database = os.path.join("instance", "data", "tickets.db")

    try:
        conn = sqlite3.connect(database)
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.DatabaseError as e:
        logger.error("Database connection failed: %s", e)
        raise


def execute_query(
    query: str, params: Tuple[Any, ...] = (), fetch: bool = False
) -> Optional[List[Dict[str, Any]]]:
    """
    Executes a SQL query on the database with error handling and logging.

    Args:
        query (str): The SQL query to execute. Use parameterized queries to
            prevent SQL injection.
        params (Tuple[Any, ...], optional): The parameters to bind to the query.
            Defaults to an empty tuple.
        fetch (bool, optional): If True, fetches and returns the results of the query.
            If False, commits changes to the database. Defaults to False.

    Returns:
        Optional[List[Dict[str, Any]]]:
            - If `fetch` is True, returns a list of dictionaries representing the rows.
            - If `fetch` is False, returns None.

    Raises:
        sqlite3.OperationalError: If there is a problem with the database operation.
        sqlite3.IntegrityError: If there is a constraint violation (e.g., unique key).
    """
    conn = None
    try:
        conn = db_get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)

        if fetch:
            result = [dict(row) for row in cursor.fetchall()]
            logger.debug("Query executed successfully: %s with params %s", query, params)
            return result

        conn.commit()
        logger.debug("Query executed and committed: %s with params %s", query, params)
        return None

    except sqlite3.OperationalError as e:
        logger.error("Database operation error: %s | Params: %s | Error: %s", query, params, e)
        raise

    except sqlite3.IntegrityError as e:
        logger.error("Integrity constraint failed: %s | Params: %s | Error: %s", query, params, e)
        raise

    finally:
        if conn:
            conn.close()


def db_fetch_tickets(
    filters: Optional[Dict[str, Any]] = None, order_by: Optional[List[str]] = None
) -> Optional[List[Dict[str, Any]]]:
    """
    Executes a SQL SELECT query with optional filtering and retrieves results
    as a list of dictionaries.

    Args:
        filters (Optional[Dict[str, Any]]): A dictionary where keys are column names
                                            and values are filter conditions.
        order_by (Optional[List[str]]): A list of column names to order the results in
                                        ascending order.

    Returns:
        Optional[List[Dict[str, Any]]]: A list of rows matching the query as dictionaries,
                                        or None on error.

    Raises:
        ValueError: If an invalid column name is used in filters.
        RuntimeError: If a database error occurs during execution.
    """
    query = "SELECT * FROM tickets"
    params = []

    if filters:
        conditions = []
        for column, value in filters.items():
            if column not in COLUMN_DEFINITIONS:
                logger.error("Invalid column name in filter: %s", column)
                raise ValueError(f"Invalid column name in filter: {column}")

            conditions.append(f"{column} = ?")
            params.append(value)

        query += " WHERE " + " AND ".join(conditions)

    if order_by:
        for column in order_by:
            if column not in COLUMN_DEFINITIONS:
                logger.error("Invalid column name in order_by: %s", column)
                raise ValueError(f"Invalid column name in order_by: {column}")
        query += " ORDER BY " + ", ".join(order_by)

    try:
        results = execute_query(query, tuple(params), fetch=True)
        logger.debug("Tickets fetched successfully: %s with params %s", query, params)
        return results
    except sqlite3.DatabaseError as e:
        logger.error("Database error in db_fetch_tickets: %s", str(e))
        raise RuntimeError(f"Database Error: {e}") from e


def db_commit_ticket(
    operation: str,
    data: Optional[Dict[str, Any]] = None,
    conditions: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Performs a validated database modification (INSERT, UPDATE, DELETE) on the 'tickets' table.

    This function constructs and executes a parameterized SQL statement based on the specified
    operation and input data. It performs validation on column names and ensures the required
    inputs are provided depending on the operation type.

    Args:
        operation (str): The type of database operation to perform.
                         Must be one of: "INSERT", "UPDATE", or "DELETE".
        data (Optional[Dict[str, Any]]): The column-value pairs to insert or update.
                                         Required for "INSERT" and "UPDATE".
        conditions (Optional[Dict[str, Any]]): The conditions used in the WHERE clause for
                                               "UPDATE" and "DELETE" operations.
                                               Required for these operation types.

    Raises:
        ValueError: If the operation type is invalid, or required data/conditions are missing
                    or contain invalid column names.
        RuntimeError: If a database error occurs during execution.
    """
    data = data or {}
    conditions = conditions or {}
    operation = operation.strip().upper()

    if operation not in {"INSERT", "UPDATE", "DELETE"}:
        logger.error("Invalid operation: %s", operation)
        raise ValueError(f"Invalid operation: {operation}")

    if operation in {"INSERT", "UPDATE"}:
        if not data:
            logger.error("%s operation requires data.", operation)
            raise ValueError(f"{operation} operation requires data.")
        validate_columns(data)

    if operation in {"UPDATE", "DELETE"}:
        if not conditions:
            logger.error("%s operation requires a WHERE condition.", operation)
            raise ValueError(f"{operation} operation requires a WHERE condition.")
        validate_columns(conditions)

    query = ""
    params: tuple[Any, ...] = ()

    try:
        if operation == "INSERT":
            columns_clause, params = prepare_sql_columns(data, True)
            column_names = ", ".join(data.keys())
            query = f"INSERT INTO tickets ({column_names}) VALUES ({columns_clause})"

        elif operation == "UPDATE":
            set_clause, params = prepare_sql_columns(data, False)
            where_clause = " AND ".join([f"{column} = ?" for column in conditions.keys()])
            query = f"UPDATE tickets SET {set_clause} WHERE {where_clause}"
            params += tuple(conditions.values())

        elif operation == "DELETE":
            where_clause = " AND ".join([f"{col} = ?" for col in conditions.keys()])
            query = f"DELETE FROM tickets WHERE {where_clause}"
            params = tuple(conditions.values())

        logger.debug("Executing Query: %s with params %s", query, params)
        execute_query(query, params, fetch=False)
        logger.info(
            "Database modification committed successfully: %s with params %s",
            query,
            params,
        )

    except (sqlite3.OperationalError, sqlite3.DatabaseError) as e:
        logger.error("Database error in db_commit_ticket: %s", str(e))
        raise RuntimeError(f"Database Error: {e}") from e


def db_init() -> None:
    """
    Initializes the SQLite database for tickets.
    This function ensures the database is prepared for operations
    but does not reset any existing data.

    Raises:
        sqlite3.DatabaseError: If there is an issue initializing the database.
        sqlite3.OperationalError: If there is a problem creating the table.
    """
    conn = None
    try:
        conn = db_get_connection()
        cursor = conn.cursor()
        create_tickets_table(cursor)
        conn.commit()
        logger.info("Database initialized successfully. Tickets table is ready.")
    finally:
        if conn:
            conn.close()


def create_tickets_table(cursor: sqlite3.Cursor) -> None:
    """
    Creates the 'tickets' table in the database if it does not already exist.

    This function dynamically generates the table schema based on COLUMN_DEFINITIONS
    and ensures that the 'tickets' table is available to store ticket details such as
    name, email, seat type, and other metadata.

    Raises:
        sqlite3.OperationalError: If an error occurs during SQL execution.
    """
    try:
        column_definitions_sql = ",\n    ".join(
            f"{column} {definition}" for column, definition in COLUMN_DEFINITIONS.items()
        )

        sql_statement = f"""
            CREATE TABLE IF NOT EXISTS tickets (
                {column_definitions_sql}
            )
        """

        cursor.execute(sql_statement)
        logger.info("Tickets table verified/created successfully.")

    except sqlite3.OperationalError as e:
        logger.error("Failed to create tickets table: %s", e)
        raise


def db_clear() -> None:
    """
    Deletes the contents of all tables in an SQLite database
    while retaining the table structure and other metadata.

    Raises:
        sqlite3.DatabaseError: If there is an issue retrieving table names or
                                executing DELETE statements.
        sqlite3.OperationalError: If the deletion fails due to database constraints or locks.
    """
    conn = None
    try:
        conn = db_get_connection()
        tables = get_table_names(conn)
        cursor = conn.cursor()

        for table_name in tables:
            if table_name != "sqlite_sequence":
                try:
                    cursor.execute(f'DELETE FROM "{table_name}";')
                except sqlite3.DatabaseError as e:
                    logger.error("Failed to clear table %s: %s", table_name, str(e))
                    continue

        conn.commit()
        logger.info("All tables cleared successfully: %s", tables)
    except sqlite3.DatabaseError as e:
        logger.error("Database error during db_clear: %s", str(e))
    finally:
        if conn:
            conn.close()


def get_table_names(conn: sqlite3.Connection) -> List[str]:
    """
    Retrieves the names of all tables in the connected SQLite database.

    Args:
        conn (sqlite3.Connection): An active SQLite database connection.

    Returns:
        List[str]: A list of table names present in the database.

    Raises:
        sqlite3.DatabaseError: If the query execution fails.
    """
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        logger.debug("Retrieved table names: %s", tables)
        return tables
    except sqlite3.DatabaseError as e:
        logger.error("Failed to retrieve table names: %s", e)
        raise


def validate_columns(data: Dict[str, Any]) -> None:
    """
    Validates that all keys in the given dictionary are valid column names.

    Args:
        data (Dict[str, Any]): Dictionary containing column names as keys.

    Raises:
        ValueError: If any key is not a valid column name.
    """
    valid_columns = COLUMN_DEFINITIONS.keys()

    for column in data.keys():
        if column not in valid_columns:
            logger.error("Invalid column name in data: %s", column)
            raise ValueError(f"Invalid column name in data: {column}")


def prepare_sql_columns(
    data: Dict[str, Any], for_insert: bool = False
) -> Tuple[str, Tuple[Any, ...]]:
    """
    Prepares column names and values for an SQL INSERT or UPDATE statement.

    - SQL functions (e.g., "CURRENT_TIMESTAMP") are inserted directly.
    - Regular values are replaced with placeholders (?) and returned as parameters.

    Args:
        data (Dict[str, Any]): The columns and values to be set.
        for_insert (bool): True for INSERT query, False for UPDATE query.

    Returns:
        Tuple[str, List[Any]]:
            - SQL SET/VALUES clause as a string
            - List of corresponding parameters (for execute_query)
    """
    allowed_sql_functions = {
        "CURRENT_TIMESTAMP",
        "NOW()",
        "DATE()",
        "TIME()",
        "UUID()",
        "SYSDATE()",
    }

    sql_function_fields = {
        column: value
        for column, value in data.items()
        if isinstance(value, str) and value.upper() in allowed_sql_functions
    }

    standard_fields = {
        column: value for column, value in data.items() if column not in sql_function_fields
    }

    if for_insert:
        sql_clause = ", ".join(["?" for _ in standard_fields.keys()])
    else:
        # for UPDATE
        set_clause_standard = [f"{column} = ?" for column in standard_fields.keys()]
        set_clause_sql_functions = [
            f"{column} = {sql_function_fields[column]}" for column in sql_function_fields.keys()
        ]
        sql_clause = ", ".join(set_clause_standard + set_clause_sql_functions)

    parameters = tuple(standard_fields.values())

    return sql_clause, parameters

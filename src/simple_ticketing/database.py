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
from typing import List, Tuple, Any, Dict, Optional

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

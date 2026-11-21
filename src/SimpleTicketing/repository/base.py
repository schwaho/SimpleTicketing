"""Base classes for data and relation repositories."""

from typing import List, Generic, TypeVar, cast
from pypika import Table, Field, Parameter
from SimpleTicketing import database
from SimpleTicketing.models import BaseDomainRecord  # pylint: disable=unused-import
from SimpleTicketing.repository.mapping import row_to_record, rows_to_records, named_parameter
from SimpleTicketing.repository.query import SQLiteReturningQuery, SQLiteReturningQueryBuilder

T = TypeVar("T", bound="BaseDomainRecord")
U = TypeVar("U", bound="BaseDomainRecord")


class RecordNotFound(Exception):
    """Exception raised when a requested database record does not exist."""


class DataRepository(Generic[T]):
    """Base repository for managing individual data records."""

    _table: Table
    model: type[T]
    _query: type[SQLiteReturningQuery] = SQLiteReturningQuery

    def __init__(self, table_name: str, model: type[T]):
        self._table = Table(table_name)
        self.model = model

    def insert(self, record: T) -> T:
        """
        Insert a new entity into the database.

        Args:
            record: Domain record to persist.

        Returns:
            The persisted domain record, including generated database fields.
        """
        record_dict = record.as_dict()
        record_dict.pop("id", None)
        record_dict.pop("created_at", None)

        bindings = named_parameter(record_dict)

        query = cast(
            SQLiteReturningQueryBuilder,
            self._query.into(self._table).columns(*bindings.keys()).insert(*bindings.values()),
        )
        query = query.returning("*")

        row = database.execute_returning(query.get_sql(), record_dict)
        return row_to_record(self.model, row)

    def insert_many(self, records: List[T]) -> List[T]:
        """
        Insert multiple entities into the database.

        Args:
            records: List of Domain records to persist.

        Returns:
            List of the persisted domain records, including generated database fields.
        """
        if not records:
            return []
        record_dicts = [r.as_dict() for r in records]
        for d in record_dicts:
            d.pop("id", None)
            d.pop("created_at", None)
        bindings = named_parameter(record_dicts[0])
        query = cast(
            SQLiteReturningQueryBuilder,
            self._query.into(self._table).columns(*bindings.keys()).insert(*bindings.values()),
        )
        query = query.returning("*")

        with database.transaction():
            rows = database.execute_returning_many(query.get_sql(), record_dicts)
        return rows_to_records(self.model, rows)

    def update(self, record: T) -> T:
        """
        Update multiple existing entities in the database.

        The entities are identified by their IDs. Their creation timestamps
        are not modified.

        Args:
            record: Domain record containing the updated values.

        Returns:
            The updated domain record as persisted in the database.
        """
        record_dict = record.as_dict()
        record_dict.pop("created_at", None)

        bindings = named_parameter(record_dict, exclude_id=True)
        query = self._query.update(self._table)
        for col, val in bindings.items():
            query = query.set(col, val)
        query = cast(SQLiteReturningQueryBuilder, query.where(self._table.id == Parameter(":id")))
        query = query.returning("*")

        row = database.execute_returning(query.get_sql(), record_dict)
        return row_to_record(self.model, row)

    def update_many(self, records: List[T]) -> List[T]:
        """
        Update existing entities in the database.

        The entities are identified by its ID. The creation timestamps
        are not modified.

        Args:
            records: List Domain records containing the updated values.

        Returns:
            List of the updated domain records as persisted in the database.
        """
        if not records:
            return []
        record_dicts = [r.as_dict() for r in records]
        for d in record_dicts:
            d.pop("created_at", None)

        bindings = named_parameter(record_dicts[0], exclude_id=True)
        query = self._query.update(self._table)
        for col, val in bindings.items():
            query = query.set(col, val)
        query = cast(SQLiteReturningQueryBuilder, query.where(self._table.id == Parameter(":id")))
        query = query.returning("*")

        with database.transaction():
            rows = database.execute_returning_many(query.get_sql(), record_dicts)
        return rows_to_records(self.model, rows)

    def get(self, id: int) -> T:  # pylint: disable=redefined-builtin
        """
        Retrieve an entity by its ID.

        Args:
            id: ID of the entity to retrieve.

        Returns:
            The domain record matching the given ID.

        Raises:
            RecordNotFound: If no entity with the given ID exists.
        """
        query = self._query.from_(self._table).select("*").where(self._table.id == Parameter(":id"))

        row = database.fetch_one(query.get_sql(), {"id": id})
        if row is None:
            raise RecordNotFound(f"{self.model.__name__} with id {id} not found")

        return row_to_record(self.model, row)

    def get_all(self) -> List[T]:
        """
        Retrieve all entities from the database.

        Returns:
            A list of all persisted domain records.
        """

        query = self._query.from_(self._table).select("*")

        rows = database.fetch_all(query.get_sql())

        return rows_to_records(self.model, rows)


class RelationRepository(Generic[T, U]):  # pylint: disable=too-few-public-methods
    """Base repository for managing relations between data records."""

    _table: Table
    _left_column: Field
    _right_column: Field
    _query: type[SQLiteReturningQuery] = SQLiteReturningQuery

    def __init__(self, table_name: str, left_column_name: str, right_column_name: str):
        self._table = Table(table_name)
        self._left_column = Field(left_column_name)
        self._right_column = Field(right_column_name)

    def link(self, left: T, right: U) -> None:
        """
        Create a link between two entities.

        Args:
            left: Domain record representing the left entity.
            right: Domain record representing the right entity.
        """
        query = (
            self._query.into(self._table)
            .columns(self._left_column, self._right_column)
            .insert(Parameter(":left_id"), Parameter(":right_id"))
        )

        database.execute(
            query.get_sql(),
            {
                "left_id": left.id,
                "right_id": right.id,
            },
        )

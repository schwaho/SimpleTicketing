from typing import List, Generic, TypeVar, cast
from pypika import Table, Field, Parameter
from simple_ticketing import database
from simple_ticketing.models import BaseDomainRecord
from simple_ticketing.repository.mapping import row_to_record, rows_to_records, named_parameter
from simple_ticketing.repository.query import SQLiteReturningQuery, SQLiteReturningQueryBuilder

T = TypeVar("T", bound="BaseDomainRecord")
U = TypeVar("U", bound="BaseDomainRecord")


class RecordNotFound(Exception):
    pass


class DataRepository(Generic[T]):
    _table: Table
    model: type[T]
    _query: type[SQLiteReturningQuery] = SQLiteReturningQuery

    def __init__(self, table_name: str, model: type[T]):
        self._table = Table(table_name)
        self.model = model

    def insert(self, record: T) -> T:
        """
        Insert a new entity.

        Args:
            model: Domain model entity to persist.
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
        Update a existing entity by its ID."

        Args:
            record: Entity containing the updated values.
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

    def get(self, id: int) -> T:
        """
        Get a entity by its ID.

        Args:
            id: ID of the entity to retrieve.

        Returns:
            The entity matching the given ID.

        Raises:
            RecordNotFound: If ID does not exist
        """

        query = self._query.from_(self._table).select("*").where(self._table.id == Parameter(":id"))

        row = database.fetch_one(query.get_sql(), {"id": id})
        if row is None:
            raise RecordNotFound(f"{self.model.__name__} with id {id} not found")

        return row_to_record(self.model, row)

    def get_all(self) -> List[T]:
        """
        Get all entities.

        Returns:
            A list containing all entities.
        """

        query = self._query.from_(self._table).select("*")

        rows = database.fetch_all(query.get_sql())

        return rows_to_records(self.model, rows)


class RelationRepository(Generic[T, U]):
    _table: Table
    _left_column: Field
    _right_column: Field
    _query: type[SQLiteReturningQuery] = SQLiteReturningQuery

    def __init__(self, table_name: str, left_column_name: str, right_column_name: str):
        self._table = Table(table_name)
        self._left_column = Field(left_column_name)
        self._right_column = Field(right_column_name)

    def link(self, left: T, right: U) -> None:
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

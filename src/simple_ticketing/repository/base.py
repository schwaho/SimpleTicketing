from typing import List, Generic, TypeVar
from pypika import Table, Field
from pypika.dialects import SQLLiteQuery as Query
from simple_ticketing import database
from simple_ticketing.models import BaseDomainRecord
from simple_ticketing.repository_mapping import row_to_record, rows_to_records, named_placeholders

T = TypeVar("T", bound="BaseDomainRecord")
U = TypeVar("U", bound="BaseDomainRecord")


class RecordNotFound(Exception):
    pass


class DataRepository(Generic[T]):
    _table: Table
    model: type[T]

    def __init__(self, table_name: str, model: type[T]):
        self._table = Table(table_name)
        self.model = model

    def insert(self, record: T) -> None:
        """
        Insert a new entity.

        Args:
            model: Domain model entity to persist.
        """
        record_dict = record.as_dict()
        record_dict.pop("id", None)

        bindings = named_placeholders(record_dict)

        query = Query.into(self._table).columns(*bindings.keys()).insert(*bindings.values())

        database.execute(query.get_sql(), record_dict)

    def update(self, record: T) -> None:
        """
        Update a existing entity by its ID."

        Args:
            record: Entity containing the updated values.
        """
        record_dict = record.as_dict()

        bindings = named_placeholders(record_dict, exclude_id=True)

        query = Query.update(self._table)
        for col, val in bindings.items():
            query = query.set(col, val)
        query = query.where(self._table.id == ":id")

        database.execute(query.get_sql(), record_dict)

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

        query = Query.from_(self._table).select("*").where(self._table.id == ":id")

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

        query = Query.from_(self._table).select("*")

        rows = database.fetch_all(query.get_sql())

        return rows_to_records(self.model, rows)


class RelationRepository(Generic[T, U]):
    _table: Table
    _left_column: Field
    _right_column: Field

    def __init__(self, table_name: str, left_column_name: str, right_column_name: str):
        self._table = Table(table_name)
        self._left_column = Field(left_column_name)
        self._right_column = Field(right_column_name)

    def link(self, left: T, right: U) -> None:
        query = (
            Query.into(self._table)
            .columns(self._left_column, self._right_column)
            .insert(":left_id", ":right_id")
        )

        database.execute(
            query.get_sql(),
            {
                "left_id": left.id,
                "right_id": right.id,
            },
        )

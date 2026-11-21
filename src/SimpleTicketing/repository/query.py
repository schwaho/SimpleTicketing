"""SQLite query builder extensions supporting the RETURNING clause."""

from typing import List, Union, Any
from pypika import Field
from pypika.terms import Star
from pypika.utils import builder
from pypika.dialects import SQLLiteQuery, SQLLiteQueryBuilder


class SQLiteReturningQueryBuilder(SQLLiteQueryBuilder):
    """SQLite query builder adding RETURNING clause support.

    Mirrors pypika's own PostgreSQLQueryBuilder.returning() implementation
    (same @builder copy-on-write pattern, same get_sql()/_returning_sql()
    structure), applied to the SQLite dialect. This is a local extension
    until pypika ships native RETURNING support for SQLite;
    see https://github.com/kayak/pypika/issues/625.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._returns: List[Union[Field, Star]] = []
        self._return_star = False

    @builder
    def returning(self, *terms: Union[str, Field]) -> None:
        """
        Add columns to the RETURNING clause.

        Accepts column names, Field instances, or the wildcard ``*``.
        Once the wildcard is added, subsequent column specifications
        are ignored.

        Args:
            *terms: Column names or field expressions to return.
        """
        for term in terms:
            if isinstance(term, str) and term == "*":
                self._returns = [Star()]
                self._return_star = True
            elif not self._return_star:
                field = Field(term) if isinstance(term, str) else term
                self._returns.append(field)

    def _returning_sql(self, **kwargs: Any) -> str:
        """
        Build the SQL fragment for the RETURNING clause.

        Args:
            **kwargs: SQL generation options passed to field expressions.

        Returns:
            The SQL representation of the RETURNING clause.
        """
        return f" RETURNING {','.join(term.get_sql(**kwargs) for term in self._returns)}"

    def get_sql(self, *args: Any, **kwargs: Any) -> str:
        """
        Generate the SQL query including the RETURNING clause.

        Args:
            *args: Positional arguments passed to the parent SQL generator.
            **kwargs: Keyword arguments passed to the parent SQL generator.

        Returns:
            The generated SQL query, optionally extended with a RETURNING clause.
        """
        querystring = super().get_sql(*args, **kwargs)
        if querystring and self._returns:
            kwargs.setdefault("with_alias", True)
            querystring += self._returning_sql(**kwargs)
        return querystring


class SQLiteReturningQuery(SQLLiteQuery):
    """Query factory producing SQLiteReturningQueryBuilder instances."""

    @classmethod
    def _builder(cls, **kwargs: Any) -> SQLiteReturningQueryBuilder:
        """Create a SQLite query builder instance.

        Args:
            **kwargs: Keyword arguments passed to the query builder.

        Returns:
            An initialized SQLiteReturningQueryBuilder.
        """
        return SQLiteReturningQueryBuilder(**kwargs)

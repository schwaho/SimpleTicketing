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
        for term in terms:
            if isinstance(term, str) and term == "*":
                self._returns = [Star()]
                self._return_star = True
            elif not self._return_star:
                field = Field(term) if isinstance(term, str) else term
                self._returns.append(field)

    def _returning_sql(self, **kwargs: Any) -> str:
        return " RETURNING {returning}".format(
            returning=",".join(term.get_sql(**kwargs) for term in self._returns)
        )

    def get_sql(self, *args: Any, **kwargs: Any) -> str:
        querystring = super().get_sql(*args, **kwargs)
        if querystring and self._returns:
            kwargs.setdefault("with_alias", True)
            querystring += self._returning_sql(**kwargs)
        return querystring


class SQLiteReturningQuery(SQLLiteQuery):
    """Query factory producing SQLiteReturningQueryBuilder instances."""

    @classmethod
    def _builder(cls, **kwargs: Any) -> SQLiteReturningQueryBuilder:
        return SQLiteReturningQueryBuilder(**kwargs)

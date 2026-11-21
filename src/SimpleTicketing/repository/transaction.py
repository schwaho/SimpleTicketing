"""
Provide the transaction context for atomic repository operations.
"""

from contextlib import contextmanager
from typing import Generator
from SimpleTicketing import database


@contextmanager
def transaction() -> Generator[None, None, None]:
    """
    Execute multiple repository operations atomically.

    All operations executed within this context are part of a single
    database transaction. If an exception is raised, the transaction
    is rolled back. Otherwise, it is committed.

    This function provides the persistence abstraction used by the
    context layer and delegates transaction handling to the database
    layer.
    """
    with database.transaction():
        yield

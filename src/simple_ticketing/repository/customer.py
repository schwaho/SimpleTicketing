"""
Repository for persisting and retrieving customer entities.

This module provides the persistence operations for :class:`models.Customer`
entities. It maps between domain models and database records while delegating
database access to the database abstraction layer.
"""

from simple_ticketing import models
from simple_ticketing.repository.base import DataRepository


class CustomerRepository(DataRepository[models.Customer]):
    def __init__(self):
        super().__init__("customers", models.Customer)

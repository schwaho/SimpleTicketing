"""
This modul provides the mapp from database row into domain records
"""

from dataclasses import fields, is_dataclass
from datetime import datetime
from typing import List, Any, Dict, Type, TypeVar, cast, get_args, get_origin

T = TypeVar("T")
NoneType = type(None)


def _is_optional(t: type[Any]) -> bool:
    """Return True if the type annotation is Optional."""
    return get_origin(t) is not None and NoneType in get_args(t)


def _base_type(t: type[Any]) -> type[Any]:
    """Extract base type from Optional[T]."""
    if _is_optional(t):
        return cast(type[Any], next(arg for arg in get_args(t) if arg is not NoneType))
    return t


def _convert_value(name: str, value: Any, annotation: Any) -> Any:
    """Convert database value to expected Python type."""
    if value is None:
        if _is_optional(annotation):
            return None
        raise TypeError(f"Field '{name}' is not Optional but received NULL")

    target_type = _base_type(annotation)

    # DATETIME conversion
    if target_type is datetime and isinstance(value, str):
        return datetime.fromisoformat(value)

    # simple runtime check
    if isinstance(target_type, type) and not isinstance(value, target_type):
        raise TypeError(
            f"Field '{name}' expected {target_type.__name__}, " f"got {type(value).__name__}"
        )

    return value


def row_to_record(cls: Type[T], row: Dict[str, Any]) -> T:
    """
    Convert a database row dict into a DomainRecord dataclass.

    Args:
        cls: Target dataclass type.
        row: Database row mapping.

    Returns:
        Instance of the dataclass.

    Raises:
        TypeError: If cls is not a dataclass or types mismatch.
        KeyError: If required fields are missing.
        ValueError: If unexpected fields are present.
    """
    if not is_dataclass(cls):
        raise TypeError(f"{cls} must be a dataclass")

    dataclass_fields = {f.name: f for f in fields(cls)}

    unknown_fields = set(row) ^ set(dataclass_fields)
    if unknown_fields:
        raise ValueError(f"Unexpected fields: {unknown_fields}")

    kwargs: dict[str, Any] = {}

    for name, field in dataclass_fields.items():
        if name not in row:
            raise KeyError(f"Missing column '{name}' in query result")

        value = row[name]
        converted = _convert_value(name, value, field.type)

        kwargs[name] = converted

    return cls(**kwargs)


def rows_to_records(
    cls: Type[T],
    rows: List[Dict[str, Any]],
) -> List[T]:
    """
    Convert multiple database rows into dataclass records.

    Args:
        cls: Target dataclass type.
        rows: List of database row mapping.

    Returns:
        List of instance of the dataclass.

    Raises:
        TypeError: If cls is not a dataclass or types mismatch.
        KeyError: If required fields are missing.
        ValueError: If unexpected fields are present.
    """
    return [row_to_record(cls, row) for row in rows]


def named_placeholders(
    data: Dict[str, Any],
    exclude_id: bool = False,
) -> Dict[str, str]:
    """Create a mapping of column names to named SQL placeholders.

    This helper converts a dictionary of column-value pairs into a mapping
    where each key is associated with a named placeholder (e.g. ``:column``).
    The result can be used to construct parametrized SQL queries (e.g. INSERT,
    UPDATE) together with database drivers such as SQLite.

    Example:
        >>> named_placeholders({"id": 1, "name": "Hans"})
        {'id': ':id', 'name': ':name'}

    Args:
        data: Dictionary mapping column names to their corresponding values.
        exclude_id: If true key 'id' is ignored.

    Returns:
        Dictionary mapping each column name to its named SQL placeholder.
    """
    return {k: f":{k}" for k in data if not (exclude_id and k == "id")}

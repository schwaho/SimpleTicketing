"""
This module provides functions for managing tickets in a database.
It includes CRUD operations such as creating, retrieving, updating, and deleting tickets.

Each function utilizes logging and error handling to ensure robust and traceable
database interactions.

Features:
---------
- Creation, retrieval, updating, and deletion of tickets.
- Listing of all visible and hidden tickets.
- Retrieval of a ticket by:
  - its ticket code
  - its ID
  - an email address
- Verification of whether a ticket exists and is not hidden.
- Deletion of a ticket by its ID.
- Marking a ticket as:
  - checked in
  - delivered
  - hidden
  - unhidden (made visible)

All functions include logging for:
- Successful operations (`logger.info(...)`)
- Warnings when tickets are not found (`logger.warning(...)`)
- Error cases (`logger.error(...)`)
"""

import logging
import uuid
from typing import List, Dict, Any, Optional, Tuple, cast
from simple_ticketing.database import db_fetch_tickets, db_commit_ticket
from simple_ticketing.ticket_image_generator import (
    create_qr_code,
    create_ticket_image,
    save_ticket_image,
)
from simple_ticketing.ticket_pdf_generator import create_ticket_pdf
from simple_ticketing.utils import (
    load_config,
    validate_config,
    is_none_or_empty,
    utc_to_local,
    get_qr_code_path,
    get_ticket_pdf_path,
    get_ticket_img_path,
    check_ticket_pdf_path,
    check_ticket_img_path,
    delete_file,
)

logger = logging.getLogger(__name__)


def create_ticket(name: str, email: str, seat_type: str, ticket_no: int) -> Dict[str, Any]:
    """
    Creates a new ticket in the database with the specified details and generates
    the associated QR code and ticket image.

    Args:
        name (str): The name of the ticket holder.
        email (str): The email address of the ticket holder.
        seat_type (str): The type of seat for the ticket.
        ticket_no (int): The passed ticket number.

    Returns:
        Dict[str, Any]: The ticket details

    Raises:
        RuntimeError: If any step in the ticket creation process fails,
                      including database insertion, QR code creation,
                      ticket image generation, or saving the image.
    """
    ticket_code = create_ticket_code(email.partition("@")[0], ticket_no)

    try:
        db_commit_ticket(
            "INSERT",
            data={
                "name": name,
                "email": email,
                "seat_type": seat_type,
                "ticket_code": ticket_code,
            },
        )

    except RuntimeError as e:
        logger.error("Database error while creating ticket.")
        raise RuntimeError(f"Database error while creating ticket: {e}") from e

    try:
        create_qr_code(ticket_code, get_qr_code_path(ticket_code))

    except (
        TypeError,
        ValueError,
        FileNotFoundError,
        RuntimeError,
        IOError,
        KeyError,
    ) as e:
        logger.error("Fail to create QR Code")
        raise RuntimeError(f"Fail to create QR Code: {e}") from e

    try:
        ticket_img = create_ticket_image(seat_type, ticket_code)

    except (
        FileNotFoundError,
        KeyError,
    ) as e:
        logger.error("Fail to draw ticket image")
        raise RuntimeError(f"Fail to draw ticket image: {e}") from e

    try:
        save_ticket_image(ticket_img, ticket_code)

    except (
        RuntimeError,
        IOError,
    ) as e:
        logger.error("Fail to save ticket image")
        raise RuntimeError(f"Fail to save ticket image: {e}") from e

    ticket = get_ticket_by_ticket_code(ticket_code)
    if not ticket:
        raise RuntimeError("Fail to read-back ticket from database.")

    logger.info(
        "Ticket successfully created: Name=%s, Email=%s, SeatType=%s, TicketCode=%s",
        name,
        email,
        seat_type,
        ticket_code,
    )
    return ticket


def create_tickets(name: str, email: str, seat_type: str, count: int) -> List[Dict[str, Any]]:
    """
    Creates multiple tickets for a given user and seat type, and generates a combined PDF
    containing all the ticket images.

    Args:
        name (str): The name of the ticket holder.
        email (str): The email address of the ticket holder.
        seat_type (str): The type of seat for all tickets.
        count (int): The number of tickets to create.

    Returns:
        List[Dict[str, Any]]: A list of dictionaries containing ticket 'id' and 'ticket_code'
                              for each successfully created ticket.

    Raises:
        RuntimeError: If the creation of any individual ticket fails, or if generating
                      the combined ticket PDF fails due to file, value, or I/O errors.
    """
    tickets_created = []
    ticket_codes = []
    for ticket_no in range(count):
        try:
            ticket = create_ticket(name, email, seat_type, ticket_no)
        except RuntimeError as e:
            raise e

        if ticket is not None:
            tickets_created.append(
                {
                    "id": ticket["id"],
                    "ticket_code": ticket["ticket_code"],
                }
            )
            ticket_codes.append(ticket["ticket_code"])

    try:
        create_ticket_pdf(ticket_codes, get_ticket_pdf_path(ticket_codes[0]))
    except (FileNotFoundError, KeyError, ValueError, IOError) as e:
        raise RuntimeError(e) from e

    return tickets_created


def delete_ticket_data(ticket: Dict[str, Any]) -> None:
    """
    Deletes all files associated with a ticket.

    This function attempts to delete the QR code image, ticket image, and PDF file
    associated with the given ticket. If any of the files are not found, they are ignored.
    A RuntimeError during deletion will be raised.

    Args:
        ticket (Dict[str, Any]): A dictionary containing ticket information,
            expected to include the key 'ticket_code'.

    Raises:
        ValueError: If 'ticket_code' is missing from the ticket dictionary.
        RuntimeError: If an error occurs during file deletion (excluding file not found).
    """
    ticket_code = ticket.get("ticket_code")
    if not ticket_code:
        raise ValueError("Ticket does not contain 'ticket_code'.")

    for path_func in [get_qr_code_path, get_ticket_img_path, get_ticket_pdf_path]:
        try:
            delete_file(path_func(ticket_code))
        except FileNotFoundError:
            pass


def list_tickets() -> Optional[List[Dict[str, Any]]]:
    """
    Retrieve all visible tickets from the database.

    Returns:
        list: A list of all tickets where the 'hidden' flag is set to 0.
        []: If no tickets are found.
        None: If a database error occurs.
    """
    return get_tickets({"hidden": 0})


def list_hidden_tickets() -> Optional[List[Dict[str, Any]]]:
    """
    Retrieve all hidden tickets from the database.

    Returns:
        list: A list of all tickets where the 'hidden' flag is set to 1.
        []: If no hidden tickets are found.
        None: If a database error occurs.
    """
    return get_tickets({"hidden": 1})


def get_ticket_by_ticket_code(ticket_code: str) -> Optional[Dict[str, Any]]:
    """
    Check if a ticket exists in the database by its code.

    Args:
        ticket_code (str): The unique code of the ticket.

    Returns:
        Dict[str, Any] or None: The ticket details if found
        None: If no ticket is found or if a database error occurs.
    """
    result = get_tickets({"ticket_code": ticket_code})
    if isinstance(result, list) and result:
        return result[0]
    return None


def get_ticket_by_id(ticket_id: int) -> Optional[Dict[str, Any]]:
    """
    Check if a ticket exists in the database by its ID.

    Args:
        ticket_id (int): The unique ID of the ticket.

    Returns:
        Dict[str, Any]: The ticket details if found.
        None: If no ticket is found or if a database error occurs.
    """
    result = get_tickets({"id": ticket_id})
    if isinstance(result, list) and result:
        return result[0]
    return None


def get_tickets_by_email(email: str) -> Optional[List[Dict[str, Any]]]:
    """
    Get all visible tickets related to an email address.

    Args:
        email (str): Customer's email address.

    Returns:
        list: A list of all tickets related to the given email address.
        []: If no tickets are found.
        None: If a database error occurs.
    """
    return get_tickets({"email": email, "hidden": 0})


def verify_ticket(ticket_code: str) -> Optional[Dict[str, Any]]:
    """
    Verify the existence and validity of a ticket by its code.

    Args:
        ticket_code (str): The unique code of the ticket.

    Returns:
        Dict[str, Any]: The ticket details if found and not hidden.
        None: Otherwise.
    """
    result = get_tickets({"ticket_code": ticket_code, "hidden": 0})
    if isinstance(result, list) and result:
        return result[0]
    return None


def check_in(ticket_code: str) -> Optional[bool]:
    """
    Mark a ticket as checked in by updating the check-in timestamp.

    Args:
        ticket_code (str): The unique code of the ticket.

    Returns:
        bool: True if the check-in was successful. False if no ticket was found.
        None: If a database error occurs.
    """
    return update_ticket(ticket_code, {"check_in_at": "CURRENT_TIMESTAMP"})


def mark_paid(ticket_code: str) -> Optional[bool]:
    """
    Mark a ticket as paid by updating the 'paid_at' timestamp.

    Args:
        ticket_code (str): The unique code of the ticket.

    Returns:
        bool: True if the update was successful; False if no ticket was found.
        None: If a database error occurs.
    """
    return update_ticket(ticket_code, {"paid_at": "CURRENT_TIMESTAMP"})


def hide_ticket(ticket_code: str) -> Optional[bool]:
    """
    Mark a ticket as hidden in the database.

    Args:
        ticket_code (str): The unique code of the ticket.

    Returns:
        bool: True if the update was successful. False if no ticket was found.
        None: If a database error occurs.
    """
    return update_ticket(ticket_code, {"hidden": 1})


def unhide_ticket(ticket_code: str) -> Optional[bool]:
    """
    Restore a previously hidden ticket to be visible in the database.

    Args:
        ticket_code (str): The unique code of the ticket.

    Returns:
        bool: True if the update was successful. False if no ticket was found.
        None: If a database error occurs.
    """
    return update_ticket(ticket_code, {"hidden": 0})


def delete_ticket_by_id(ticket_id: int) -> bool:
    """
    Delete a ticket in the database by its ID.

    Args:
        ticket_id (int): The unique ID of the ticket.

    Returns:
        bool: True if the ticket was deleted successfully, False otherwise.
    """
    existing_ticket = get_ticket_by_id(ticket_id)
    if existing_ticket is None:
        logger.warning("Attempted to delete non-existing ticket with ID: %d", ticket_id)
        return False

    try:
        db_commit_ticket("DELETE", conditions={"id": ticket_id})
    except RuntimeError:
        logger.error("Database error while deleting ticket ID %d from database", ticket_id)
        return False

    try:
        delete_ticket_data(existing_ticket)
    except RuntimeError:
        logger.error("Error while deleting ticket files of ticket ID %d", ticket_id)
        return False

    logger.info("Ticket deleted successfully: ID=%d", ticket_id)
    return True


def get_tickets(
    filter_dict: Optional[Dict[str, Any]], order_by: Optional[List[str]] = None
) -> Optional[List[Dict[str, Any]]]:
    """
    Retrieve tickets based on filter conditions.

    Args:
        filter_dict (Dict[str, Any]): Dictionary of conditions to filter tickets.
        order_by (Optional[List[str]]): A list of keys to order the tickets in
                                        ascending order.

    Returns:
        List[Dict[str, Any]]: Retrieved tickets if found.
        None: If a database error occurs.
    """
    try:
        results = db_fetch_tickets(filter_dict, order_by)
    except RuntimeError:
        logger.error(
            "Database error while retrieving tickets with filter: %s and order: %s",
            filter_dict,
            order_by,
        )
        return None

    if results:
        logger.info("Retrieved %d tickets with filter: %s", len(results), filter_dict)
        for ticket in results:
            ticket = convert_timestamps_to_local(ticket)
        return results

    logger.info("No tickets found with filter: %s", filter_dict)
    return []


def update_ticket(ticket_code: str, update_fields: Dict[str, Any]) -> Optional[bool]:
    """
    Update a ticket's attributes in the database.

    Args:
        ticket_code (str): The unique code of the ticket.
        update_fields (Dict[str, Any]): Fields to update with new values.

    Returns:
        bool: True if the update was successful, False if the ticket wasn't found.
        None: If a database error occurs.
    """
    existing_ticket = get_ticket_by_ticket_code(ticket_code)
    if existing_ticket is None:
        logger.warning("Attempted to update a non-existing ticket: %s", ticket_code)
        return False

    try:
        db_commit_ticket("UPDATE", update_fields, {"ticket_code": ticket_code})
    except RuntimeError:
        logger.error("Database error while updating ticket %s", ticket_code)
        return None

    logger.info("Ticket updated successfully: %s", ticket_code)
    return True


def prepare_ticket_assets_for_email(email: str) -> Tuple[str, List[str], str]:
    """Prepares ticket assets (images and PDF) for sending via email.

    Retrieves ticket information associated with the given email address,
    verifies payment status, and collects the paths to the related ticket
    images and PDF file.

    Args:
        email (str): The email address associated with the ticket(s).

    Returns:
        Optional[Tuple[str, List[str], str]]: A tuple containing:
            - name (str): The name of the ticket holder.
            - ticket_img_paths (List[str]): A list of image file paths for the tickets.
            - pdf_path (str): The file path of the ticket PDF.

    Raises:
        ValueError: If no tickets are found for the email or if tickets are not marked as paid.
        RuntimeError: If the PDF or any ticket image file is missing.
    """
    tickets = get_tickets({"email": email, "hidden": 0}, ["ticket_code"])
    if tickets is None:
        raise ValueError(f"No ticketes found for email: {email}")

    if tickets[0].get("paid_at") is None:
        raise ValueError("Tickets not jet marked as paid")

    name = tickets[0].get("name", "")
    ticket_code = tickets[0].get("ticket_code", "")

    pdf_path = check_ticket_pdf_path(ticket_code)
    if pdf_path is None:
        raise RuntimeError(f"No ticket PDF found for ticket code: {ticket_code}")

    ticket_img_paths = []
    for ticket in tickets:
        ticket_img_path = check_ticket_img_path(cast(str, ticket.get("ticket_code")))
        if ticket_img_path is None:
            raise RuntimeError(f"No ticket image found for ticket code: {ticket_code}")
        ticket_img_paths.append(ticket_img_path)

    return (
        name,
        ticket_img_paths,
        pdf_path,
    )


def mark_tickets_as_delivered(email: str) -> None:
    """
    Marks all tickets associated with a given email address as delivered.

    Retrieves all tickets linked to the provided email and updates each ticket
    by setting its 'delivered_at' field to the current timestamp. Raises an
    error if no tickets are found for the email.

    Args:
        email (str): The email address associated with the tickets.

    Raises:
        ValueError: If no tickets are found for the given email.
    """
    tickets = get_tickets({"email": email, "hidden": 0})
    if tickets is None:
        raise ValueError(f"No ticketes found for email: {email}")

    for ticket in tickets:
        update_ticket(ticket.get("ticket_code", ""), {"delivered_at": "CURRENT_TIMESTAMP"})


def create_ticket_code(prefix: str, ticket_no: int) -> str:
    """
    Generates a unique ticket code consisting of a prefix,
    a ticket number, and a random UUID part.

    The code has the format: “<prefix>-<ticket_no>-<random>”,
    where:
        - prefix: the first 6 characters (or less, if shorter) of the passed string,
        - ticket_no: the passed ticket number,
        - random: the first 8 characters of a generated UUID (hexadecimal).

    Args:
        prefix (str): The string prefix used to identify the code.
        ticket_no (int): The unique ticket number.

    Returns:
        str: The generated ticket code.
    """

    return f"{prefix[:6].lower()}-{ticket_no}-{uuid.uuid4().hex[:8]}"


def convert_timestamps_to_local(ticket: Dict[str, Any]) -> Dict[str, Any]:
    """
    This function converts the time information in a ticket's timestamps to the local time zone.

    Args:
        ticket (Dict): Dict containing all fields of a single ticket.

    Returns:
        Dict[str, Any]: Dict with convertet timestamps.
    """

    localization_conf = load_config("app.yaml", "localization")
    validate_config(localization_conf, ["time_zone", "time_format"])
    time_zone = localization_conf["time_zone"]
    time_format = localization_conf["time_format"]

    created_at = ticket["created_at"]
    paid_at = ticket["paid_at"]
    delivered_at = ticket["delivered_at"]
    check_in_at = ticket["check_in_at"]

    if not is_none_or_empty(created_at):
        ticket["created_at"] = utc_to_local(ticket["created_at"], time_zone, time_format)
    if not is_none_or_empty(paid_at):
        ticket["paid_at"] = utc_to_local(ticket["paid_at"], time_zone, time_format)
    if not is_none_or_empty(delivered_at):
        ticket["delivered_at"] = utc_to_local(ticket["delivered_at"], time_zone, time_format)
    if not is_none_or_empty(check_in_at):
        ticket["check_in_at"] = utc_to_local(ticket["check_in_at"], time_zone, time_format)

    return ticket


def get_seat_types() -> List[str]:
    """
    Retrieves the seat types from the event configuration.

    Returns:
        List[str]: The configured seat types.

    Raises:
        FileNotFoundError: If the event configuration could not be loaded.
        KeyError: If the 'event' or 'seat_types' key is missing or invalid.
        TypeError: If type of 'seat_types' value is not List[str] or str.
    """
    event_config = load_config("event.yaml", "event")
    validate_config(event_config, ["seat_types"])
    seat_types = event_config["seat_types"]
    if seat_types and isinstance(seat_types, list):
        if all(isinstance(s, str) for s in seat_types):
            return cast(List[str], seat_types)
        raise TypeError("Expected all elements in 'seat_types' to be strings")
    if isinstance(seat_types, str):
        return [seat_types]
    raise TypeError("Expected 'seat_types' to be a list of strings or a string")


def get_default_seat_type() -> str:
    """
    Retrieves the default seat type from the event configuration.

    Returns:
        str: The configured default seat type.

    Raises:
        FileNotFoundError: If the event configuration could not be loaded.
        KeyError: If the 'event' or 'seat_types' key is missing or invalid.
        TypeError: If type of 'seat_types' value is not List[str] or str.
    """
    return get_seat_types()[0]

"""
API Routes for the Ticketing System.

This module provides the API endpoints for interacting with tickets, including
creating, retrieving, updating, deleting, verifying, hiding, and sending tickets.

Routes:
    Ticket Management:
        - POST /create_ticket: Create a new ticket.
        - GET /ticket/<id>: Retrieve a ticket by ID.
        - DELETE /ticket/<id>: Delete a ticket by ID.
        - PATCH /ticket/<id>: Update a ticket by ID.
        - GET /ticket_code/<ticket_code>: Retrieve a ticket by ticket code.
        - DELETE /ticket_code/<ticket_code>: Delete a ticket by ticket code.
        - PATCH /ticket_code/<ticket_code>: Update a ticket by ticket_code.
        - GET /tickets: List all tickets.
        - GET /hidden_tickets: List all hidden tickets.
        - POST /mark_paid: Mark tickets as paid by email
        - GET /export_ticket/<ticket_code>: Return rendered Ticket (PNG Image)

    Ticket Validation & Check-In:
        - POST /check_in_ticket: Check-in an existing ticket.
        - GET /verify_ticket/<ticket_code>: Verify a ticket by its code.

    Ticket Visibility:
        - POST /hide_ticket/<ticket_code>: Hide a ticket.
        - POST /unhide_ticket/<ticket_code>: Unhide a ticket.

    Ticket Misc:
        - GET /seat_types: Return a list of valid seat types for a ticket.

    Email Operations:
        - POST /send_test_mail: Send a test email.
        - POST /send_ticket_mail: Send purchased tickets via email.

    Misc:
        - GET /version: Returns project version.
"""

from typing import Union, Tuple, Dict, List, Any, Optional
import importlib.metadata
from flask import Blueprint, request, jsonify, Response, Request, send_file
from flask_mail import BadHeaderError
from simple_ticketing.utils import (
    validate_email,
    check_ticket_img_path,
    is_none_or_empty,
    remove_none_from_dict,
)
from simple_ticketing.email_operations import send_simple_mail, send_tickets
from simple_ticketing.ticket_operations import (
    list_tickets as get_all_tickets_from_db,
    list_hidden_tickets as list_hidden_tickets_in_db,
    create_tickets as create_tickets_data,
    update_ticket as update_ticket_in_db,
    mark_paid as mark_paid_in_db,
    check_in as check_in_ticket_in_db,
    get_ticket_by_ticket_code as get_ticket_by_ticket_code_from_db,
    get_ticket_by_id as get_ticket_by_id_from_db,
    get_tickets_by_email as get_tickets_by_email_from_db,
    delete_ticket_by_id as delete_ticket_w_files_by_id,
    verify_ticket as verify_tickets_in_db,
    hide_ticket as hide_ticket_in_db,
    unhide_ticket as unhide_ticket_in_db,
    prepare_ticket_assets_for_email,
    mark_tickets_as_delivered,
    get_seat_types,
    get_default_seat_type,
)

api = Blueprint("api", __name__)


def get_request_data(
    req: Request,
    required_fields: List[str],
    optional_fields: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Retrieves and validates JSON request data, supporting required and optional fields.
    Only allows and returns explicitly defined required and optional fields.

    Args:
        req (Request): The Flask request object.
        required_fields (List[str]): List of required field names.
        optional_fields (Dict[str, Any]): Dictionary of optional fields with default values.

    Returns:
        Dict[str, Any]: The extracted data as a dictionary.

    Raises:
        ValueError: If JSON is missing, required fields are missing, or unexpected fields
                    are present.
    """
    raw_data = req.get_json(silent=True)
    if raw_data is None:
        raise ValueError("Invalid JSON request")

    data: Dict[str, Any] = raw_data

    missing_fields = [
        field for field in required_fields if field not in data or is_none_or_empty(data[field])
    ]
    if missing_fields:
        raise ValueError(f"Missing required fields: {', '.join(sorted(missing_fields))}")

    if optional_fields is not None:
        for field, default_value in optional_fields.items():
            if is_none_or_empty(data.get(field)):
                data[field] = default_value

    allowed_fields = set(required_fields) | set(optional_fields or {})

    unexpected_fields = set(data.keys()) - allowed_fields
    if unexpected_fields:
        raise ValueError(f"Unexpected fields in request: {', '.join(sorted(unexpected_fields))}")

    return data


def api_response(
    message: Union[str, Dict[str, Any], List[Dict[str, Any]]], status_code: int
) -> Response:
    """
    Generates a standardized JSON API response.

    This function creates a consistent response format for both success and error messages,
    ensuring uniform API responses across the application.

    Args:
        message (Union[str, dict, list]): The message to be returned in the response.
                                    If a string, it will be wrapped in a JSON object.
        status_code (int): The HTTP status code for the response.

    Returns:
        Response: A Flask JSON response with the given status code
    """
    if isinstance(message, str):
        message = {"message": message}
    response = jsonify(message)
    response.status_code = status_code
    return response


def validate_ticket_creation_request(req: Request) -> Tuple[bool, Dict[str, Any]]:
    """
    This function checks whether the given request contains valid data for ticket creation.
    It ensures required fields are present, applies default values to optional fields,
    and validates data types and values.

    Args:
        req (Request): The incoming HTTP request containing ticket details.

    Returns:
        Tuple[bool, Dict[str, Any]]:
            - A boolean indicating whether the request is valid.
            - A dictionary containing either the validated data (if valid) or an error message.

    """

    try:
        default_seat_type = get_default_seat_type()
    except (FileNotFoundError, KeyError) as e:
        return False, {"error": str(e)}

    try:
        json_data = get_request_data(
            req,
            required_fields=["name", "email"],
            optional_fields={"seat_type": default_seat_type, "count": 1},
        )

        email = json_data["email"]
        count = json_data["count"]

        try:
            count = int(count)
        except (ValueError, TypeError):
            return False, {"error": "Invalid count value"}
        if count < 1:
            return False, {"error": "Count must be a positive integer"}

    except ValueError as e:
        return False, {"error": str(e)}

    if not validate_email(email):
        return False, {"error": "Invalid Email"}

    return True, json_data


def patch_ticket(ticket: dict[str, Any], req: Request) -> Response:
    """
    Patches the given ticket with data from the request payload.

    This function extracts data from the incoming HTTP request, validates
    and filters the fields to be updated, and attempts to update the
    ticket in the database. If successful, it returns the updated ticket data.
    Otherwise, it returns an appropriate error response.

    Args:
        ticket (dict): The original valid ticket data.
        req (Request): The incoming HTTP request containing ticket details.

    Returns:
        Response: A Flask Response object containing JSON data and an HTTP status code.

    """
    try:
        data = get_request_data(req, [], {"name": None, "email": None, "seat_type": None})
    except ValueError as e:
        return api_response({"error": f"{e}"}, 400)
    clear_data = remove_none_from_dict(data)
    if not clear_data:
        return api_response({"error": "No valid fields provided to update"}, 400)

    if "email" in clear_data:
        if not validate_email(clear_data["email"]):
            return api_response({"error": f"Email {clear_data['email']} not valid"}, 400)
    if not update_ticket_in_db(ticket["ticket_code"], clear_data):
        return api_response(
            {"error": f"Failed to update ticket #{ticket['id']} ({ticket['ticket_code']})"},
            500,
        )
    patched_ticket = get_ticket_by_ticket_code_from_db(ticket["ticket_code"])
    if not patched_ticket:
        return api_response(
            {
                "error": "Failed to received patched ticket "
                f"#{ticket['id']} ({ticket['ticket_code']})"
            },
            500,
        )

    return api_response(patched_ticket, 200)


def delete_ticket(ticket: Dict[str, Any]) -> Response:
    """
    Deletes a ticket from the database along with its associated images (ticket image and QR code).

    Args:
        ticket (Dict[str, Any]): The ticket to be deleted. Must contain 'id' and
        'ticket_code'.

    Returns:
        Response: API response with status and message.
    """

    if not delete_ticket_w_files_by_id(ticket["id"]):
        return api_response(
            {"error": f"Failed to delete Ticket #{ticket['id']} ({ticket['ticket_code']})"},
            500,
        )

    return api_response(f"Ticket #{ticket['id']} ({ticket['ticket_code']}) deleted", 200)


@api.route("/create_ticket", methods=["POST"])
def create_ticket() -> Response:
    """
    Creates a new ticket and returns a JSON response.

    This endpoint processes a JSON request to create one or multiple tickets.
    It generates a unique ticket code, a QR code, a ticket image, and a PDF file.

    Returns:
        Response: A JSON response indicating the ticket creation status:
            - `201 Created`: Tickets were successfully created.
            - `400 Bad Request`: Invalid JSON request or missing required fields (name, email).
            - `400 Bad Request`: Provided email is invalid.
    """
    flag, result = validate_ticket_creation_request(request)
    if not flag:
        return api_response(result, 400)

    name = result["name"]
    email = result["email"]
    seat_type = result["seat_type"]
    count = result["count"]

    try:
        tickets_created = create_tickets_data(name, email, seat_type, count)
    except RuntimeError as e:
        return api_response({"error": str(e)}, 500)

    return api_response({"message": f"{count} ticket(s) created", "tickets": tickets_created}, 201)


@api.route("/ticket_id/<int:ticket_id>", methods=["GET"])
def get_ticket_by_id(ticket_id: int) -> Response:
    """
    Retrieves a ticket by its unique ID.

    This endpoint fetches a ticket's details from the database based on the provided ticket ID.

    Args:
        ticket_id (int): The ID of the ticket to retrieve.

    Returns:
        Response: A JSON response containing the ticket details or an error message.
            - `200 OK`: The ticket was found and returned.
            - `404 Not Found`: No ticket exists for the provided ID.
    """

    ticket = get_ticket_by_id_from_db(ticket_id)
    if ticket:
        return api_response(ticket, 200)
    return api_response({"error": f"Ticket #{ticket_id} not found"}, 404)


@api.route("/ticket_id/<int:ticket_id>", methods=["DELETE"])
def delete_ticket_by_id(ticket_id: int) -> Response:
    """
    Deletes a ticket by its unique ID.

    This endpoint removes a ticket from the database based on the provided ticket ID.
    If the ticket exists, its associated QR code file is also deleted.

    Args:
        ticket_id (int): The ID of the ticket to delete.

    Returns:
        Response: A JSON response indicating the deletion status:
            - `200 OK` if the ticket was successfully deleted.
            - `404 Not Found` if the ticket does not exist.
    """

    ticket = get_ticket_by_id_from_db(ticket_id)
    if not ticket:
        return api_response({"error": f"Ticket #{ticket_id} not found"}, 404)
    return delete_ticket(ticket)


@api.route("/ticket_id/<int:ticket_id>", methods=["PATCH"])
def patch_ticket_by_id(ticket_id: int) -> Response:
    """
    Partially updates fields of a ticket by its unique ID.

    This endpoint allows partial updates to ticket details, such as name, email, or seat type.

    Args:
        ticket_id (int): The ID of the ticket to be updated.

    Returns:
        Response: A JSON response indicating the outcome.
            - `200 OK`: Ticket was successfully updated.
            - `400 Bad Request`: Invalid data provided (e.g., bad email format).
            - `404 Not Found`: No ticket found with the given ID.
    """

    ticket = get_ticket_by_id_from_db(ticket_id)
    if not ticket:
        return api_response({"error": f"Ticket #{ticket_id} not found"}, 404)
    return patch_ticket(ticket, request)


@api.route("/ticket_code/<ticket_code>", methods=["GET"])
def get_ticket_by_code(ticket_code: str) -> Response:
    """
    Retrieves a ticket by its unique ticket code.

    This endpoint fetches a ticket's details from the database based on the provided ticket code.

    Args:
        ticket_code (str): The ticket code of the ticket to retrieve.

    Returns:
        Response: A JSON response containing the ticket details or an error message.
            - `200 OK`: The ticket was found and returned.
            - `404 Not Found`: No ticket exists for the provided ticket code.
    """

    ticket = get_ticket_by_ticket_code_from_db(ticket_code)
    if ticket:
        return api_response(ticket, 200)
    return api_response({"error": f"Ticket code {ticket_code} not found"}, 404)


@api.route("/ticket_code/<ticket_code>", methods=["DELETE"])
def delete_ticket_by_code(ticket_code: str) -> Response:
    """
    Deletes a ticket by its unique ticket code.

    This endpoint removes a ticket from the database based on the provided ticket code.
    If the ticket exists, its associated QR code file is also deleted.

    Args:
        ticket_code (str): The ticket code of the ticket to delete.

    Returns:
        Response: A JSON response indicating the deletion status:
            - `200 OK` if the ticket was successfully deleted.
            - `404 Not Found` if the ticket does not exist.
    """
    ticket = get_ticket_by_ticket_code_from_db(ticket_code)
    if not ticket:
        return api_response({"error": f"Ticket {ticket_code} not found"}, 404)
    return delete_ticket(ticket)


@api.route("/ticket_code/<ticket_code>", methods=["PATCH"])
def patch_ticket_by_code(ticket_code: str) -> Response:
    """
    Partially updates fields of a ticket by its unique ticket code.

    This endpoint allows partial updates to ticket details, such as name, email, or seat type.

    Args:
        ticket_code (str): The ticket code of the ticket to be updated.

    Returns:
        Response: A JSON response indicating the outcome.
            - `200 OK`: Ticket was successfully updated.
            - `400 Bad Request`: Invalid data provided (e.g., bad email format).
            - `404 Not Found`: No ticket found with the given ID.
    """

    ticket = get_ticket_by_ticket_code_from_db(ticket_code)
    if not ticket:
        return api_response({"error": f"Ticket with ticket code: {ticket_code} not found"}, 404)
    return patch_ticket(ticket, request)


@api.route("/tickets", methods=["GET"])
def list_tickets() -> Response:
    """
    Retrieves all available tickets.

    This endpoint fetches all tickets from the database. If tickets exist, they are returned as
    a JSON list. If no tickets are found, an error response is returned.

    Returns:
        Response: A JSON response indicating the retrieval status.
            - `200 OK` Returns a list of all available tickets.
            - `500 Internal Server Error` if a database error has occurred.
    """

    tickets = get_all_tickets_from_db()
    if tickets is not None:
        return api_response([dict(ticket) for ticket in tickets], 200)
    return api_response({"error": "A database error has occurred."}, 500)


@api.route("/hidden_tickets", methods=["GET"])
def list_hidden_tickets() -> Response:
    """
    Retrieves a list of all hidden tickets.

    This endpoint fetches all tickets that have been marked as hidden in the database
    and returns them as a JSON list.

    Returns:
        Response: A JSON response indicating the retrieval status.
            - `200 OK`: Returns a list of all hidden tickets.
            - `500 Internal Server Error` if a database error has occurred.
    """
    tickets = list_hidden_tickets_in_db()
    if tickets is not None:
        return api_response([dict(ticket) for ticket in tickets], 200)
    return api_response({"error": "A database error has occurred."}, 500)


@api.route("/check_in_ticket", methods=["POST"])
def check_in_ticket() -> Response:
    """
    Validates and checks in a ticket based on its unique code.

    This endpoint processes a JSON request containing a ticket code, verifies if the ticket exists,
    and checks it in if it has not been used before.

    Returns:
        Response: A JSON response indicating the check-in status:
            - `200 OK` if the ticket is valid and successfully checked in.
            - `400 Bad Request` if the ticket code is invalid.
            - `409 Conflict` if the ticket has already been used.
            - `500 Internal Server Error` if a database error has occurred.
    """
    try:
        data = get_request_data(request, ["ticket_code"])
        ticket_code = data["ticket_code"]
    except ValueError as e:
        return api_response({"error": str(e)}, 400)

    ticket = get_ticket_by_ticket_code_from_db(ticket_code)

    if ticket:
        if ticket["check_in_at"] is not None:
            return api_response({"error": "Ticket has already been used"}, 409)
        if ticket["hidden"] != 0:
            return api_response({"error": "Ticket is hidden"}, 409)
        if not check_in_ticket_in_db(ticket_code):
            return api_response({"error": "A database error has occurred."}, 500)
        return api_response("Ticket valid", 200)
    return api_response({"error": "Invalid ticket"}, 400)


@api.route("/verify_ticket/<ticket_code>", methods=["GET"])
def verify_ticket(ticket_code: str) -> Response:
    """
    Verifies the validity of a ticket using its unique code.

    This endpoint checks if the provided ticket code exists in the database and
    returns the verification status.

    Args:
        ticket_code (str): The unique code of the ticket to verify.

    Returns:
        Response: A JSON response indicating the verification status:
            - `200 OK` if the ticket is valid.
            - `404 Not Found` if the ticket does not exist.
            - `500 Internal Server Error` if a database error has occurred.
    """
    ticket = verify_tickets_in_db(ticket_code)

    if ticket is None:
        return api_response({"error": "A database error has occurred."}, 500)
    if not ticket:
        return api_response({"error": "Ticket not found."}, 404)

    return api_response("Ticket valid", 200)


@api.route("/hide_ticket/<ticket_code>", methods=["POST"])
def hide_ticket(ticket_code: str) -> Response:
    """
    Hides a ticket by marking it as hidden in the database.

    This endpoint updates the status of a ticket so that it is considered hidden.

    Args:
        ticket_code (str): The unique code of the ticket to hide.

    Returns:
        Response: A JSON response indicating the hide status:
            - `200 OK` if the ticket was successfully hidden.
            - `404 Not Found` if the ticket does not exist.
            - `500 Internal Server Error` if a database error has occurred.
    """
    result = hide_ticket_in_db(ticket_code)

    if result is None:
        return api_response({"error": "A database error has occurred."}, 500)
    if not result:
        return api_response({"error": "Ticket not found."}, 404)

    return api_response("Ticket successfully hidden.", 200)


@api.route("/unhide_ticket/<ticket_code>", methods=["POST"])
def unhide_ticket(ticket_code: str) -> Response:
    """
    Unhides a previously hidden ticket.

    This endpoint updates the status of a ticket so that it is no longer considered hidden.

    Args:
        ticket_code (str): The unique code of the ticket to unhide.

    Returns:
        Response: A JSON response indicating the unhide status:
            - `200 OK` if the ticket was successfully unhidden.
            - `404 Not Found` if the ticket does not exist.
            - `500 Internal Server Error` if a database error has occurred.
    """
    result = unhide_ticket_in_db(ticket_code)

    if result is None:
        return api_response({"error": "A database error has occurred."}, 500)
    if not result:
        return api_response({"error": "Ticket not found."}, 404)

    return api_response("Ticket successfully unhidden.", 200)


@api.route("/mark_paid", methods=["POST"])
def mark_paid() -> Response:
    """
    Marking all ticket with a given e-mail address as paid by setting timestamp in the database.

    Returns:
        Response: A JSON response indicating the hide status:
            - `200 OK` if the ticket was successfully mark paid.
            - `404 Not Found` if the ticket does not exist.
            - `500 Internal Server Error` if a database error has occurred.
    """
    try:
        data = get_request_data(request, ["email"])
        email = data["email"]
    except ValueError as e:
        return api_response({"error": str(e)}, 400)

    tickets = get_tickets_by_email_from_db(email)
    if tickets is None:
        return api_response({"error": "A database error has occurred."}, 500)
    if not tickets:
        return api_response({"error": f"No Ticket not found with e-mail: {email}."}, 404)

    for ticket in tickets:
        result = mark_paid_in_db(ticket["ticket_code"])

        if result is None:
            return api_response({"error": "A database error has occurred."}, 500)

    return api_response("Ticket(s) successfully marked paid.", 200)


@api.route("/export_ticket/<ticket_code>", methods=["GET"])
def export_ticket(ticket_code: str) -> Response:
    """
    Export a ticket as an image file.

    Args:
        ticket_code (str): The code of the ticket to export.

    Returns:
        Flask response with:
            - `200 OK` the ticket image file
            - `404 Not Found` if the ticket or ticket image does not exist.
    """
    if not get_ticket_by_ticket_code_from_db(ticket_code):
        return api_response({"error": "Ticket not found."}, 404)

    ticket_img_path = check_ticket_img_path(ticket_code)
    if not ticket_img_path:
        return api_response({"error": "No ticket image found"}, 404)

    return send_file(
        ticket_img_path,
        mimetype="image/png",
        as_attachment=True,
        download_name=f"ticket_{ticket_code}.png",
    )


@api.route("/seat_types", methods=["GET"])
def get_seat_types_api() -> Response:
    """
    Return a list of valid seat types for a ticket.

    Returns:
        JSON response with:
            - `200 OK` List of valid seat types
            - `500 Internal Server Error` if seat types can not parsed from config
    """

    try:
        seat_types = get_seat_types()
        return api_response({"seat_types": seat_types}, 200)
    except (FileNotFoundError, KeyError, TypeError) as e:
        return api_response({"error": str(e)}, 500)


@api.route("send_test_mail", methods=["POST"])
def send_test_mail() -> Response:
    """
    Sends a test email to a specified recipient.

    This endpoint processes a JSON request containing an email address
    and sends a simple test email to verify email functionality.

    Returns:
        Response: A JSON response indicating the email sending status:
            - `200 OK` if the email was sent successfully.
            - `400 Bad Request` if the email field is missing or invalid.
            - `500 Internal Server Error` if the email could not be sent.
    """
    try:
        data = get_request_data(request, ["email"])
        recipient = data["email"]

        if not validate_email(recipient):
            return api_response({"error": "Invalid email address"}, 400)

        send_simple_mail(
            recipient,
            subject="Simple Ticketing Test Mail",
            body="This is a test email sent by Simple Ticketing.",
        )

        return api_response("Email has been sent successfully", 200)

    except ValueError as e:
        return api_response({"error": str(e)}, 400)

    except BadHeaderError:
        return api_response({"error": "Email could not be sent"}, 500)


@api.route("send_ticket_mail", methods=["POST"])
def send_ticket_mail() -> Response:
    """
    Sends purchased tickets via email to the specified recipient.

    This endpoint processes a JSON request containing an email address, retrieves all tickets
    associated with that email, generates the necessary ticket files, and sends them via email.

    Returns:
        Response: A JSON response indicating the email sending status:
            - `200 OK` if the tickets were successfully sent.
            - `400 Bad Request` if the email field is missing or invalid.
            - `500 Internal Server Error`: An error occurred while preparing the tickets,
              sending the email, or marking the tickets as delivered.
    """
    try:
        data = get_request_data(request, ["email"])
        email = data["email"]
    except ValueError as e:
        return api_response({"error": str(e)}, 400)

    try:
        name, ticket_img_paths, pdf_path = prepare_ticket_assets_for_email(email)
    except (ValueError, RuntimeError) as e:
        return api_response(str(e), 500)

    try:
        send_tickets(email, name, ticket_img_paths, pdf_path)
    except BadHeaderError:
        return api_response({"error": "Email has not been sent"}, 500)

    try:
        mark_tickets_as_delivered(email)
    except ValueError as e:
        return api_response(str(e), 500)

    return api_response("Email has been sent successfully", 200)


@api.route("/version")
def get_version() -> Response:
    """
    Return the current project version.

    Returns:
        Response: A JSON response containing the current project version or error message
            - `200 OK` current project version
            - `500 Internal Server Error`: Project version cannot be determined.
                                           Package may not be installed
    """
    try:
        version = importlib.metadata.version("SimpleTicketing")
        return api_response({"version": version}, 200)
    except importlib.metadata.PackageNotFoundError:
        return api_response({"error": "Project version not found"}, 500)

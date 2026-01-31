"""
Frontend routes for ticketing system.

This module provides the Frontend endpoints to connect the User to the API.

Routes:
-------
- GET /: Landing Page
- GET /create_ticket: Ticket creation form
- GET /list_tickets: Overview of unhidden tickets
- GET /list_hidden_tickets: Overview of hidden tickets
- GET /check_in: QR-Code scanner for Check-In Staff
- GET /qr_codes/<ticket_code>: Return Ticket-Code as QR-Code
- GET /export_ticket/<ticket_code>: Return rendered Ticket (PNG Image)
- POST /hide_ticket/<ticket_code>: Hide a Ticket
- POST /unhide_ticket/<ticket_code>: Unhide a Ticket
- POST /mark_paid/<email>: Mark all tickets identified by email as paid
- POST /send_ticket/<email>: Send all ticket identified by email
"""

import os
from typing import Union, Tuple, cast, Optional, Any, Dict
import requests
from flask import (
    Blueprint,
    render_template,
    send_file,
    redirect,
    url_for,
    Response,
    current_app,
)

frontend = Blueprint("frontend", __name__)
API_BASE_URL = "https://localhost:5000/api/"
REQUEST_TIMEOUT = 60


def render_error_page(message: str, code: int) -> str:
    """Renders a generic error page with a custom message and HTTP status code.

    Args:
        message (str): The error message to display.
        code (int): The HTTP status code.

    Returns:
        str: The rendered error page.
    """
    return render_template("error.html", message=message, code=code)


def handle_api_response(response: Response, success_redirect: str) -> Union[Response, str]:
    """Handles API responses and determines the appropriate action.

    If the response status code is within the 2xx range, the function redirects
    to the specified success route. Otherwise, it renders an error page with
    the error message from the API response (if available).

    Args:
        response: The HTTP response object from the API request.
        success_redirect (str): The name of the Flask route to redirect to on success.

    Returns:
        Union[Response, str]: A redirect response for successful requests,
        or an error page with the API's error message and status code.
    """
    if 200 <= response.status_code < 300:
        return cast(Response, redirect(url_for(success_redirect)))

    error_message = "An unknown error has occurred."

    error_data = {}
    if hasattr(response, "json") and callable(response.json):
        try:
            error_data = response.json()
            if isinstance(error_data, dict) and "error" in error_data:
                error_message = error_data["error"]
        except ValueError:
            pass  # Keep the default error message if the response is not valid JSON

    return render_error_page(error_message, response.status_code)


def handle_api_response_with_data(
    response: Response,
    template_name: str,
    context: Optional[Dict[str, Any]],
    success_key: str = "data",
) -> str:
    """
    Handles an API response and renders a template with data on success.

    Args:
        response (Response): The HTTP response from the API.
        template_name (str): Name of the template to render on success.
        context (dict, optional): Additional context variables to pass to the template.
        success_key (str): Key under which the API data will be available in the template.

    Returns:
        str: Rendered template or error page.
    """
    context = context or {}
    error_message = "An unknown error has occurred."

    if hasattr(response, "json") and callable(response.json):
        if 200 <= response.status_code < 300:
            try:
                api_data = response.json()
            except ValueError:
                api_data = {}

            context[success_key] = api_data
            return render_template(template_name, **context)

        error_data = {}
        try:
            error_data = response.json()
            if isinstance(error_data, dict) and "error" in error_data:
                error_message = error_data["error"]
        except ValueError:
            pass  # Keep the default error message if the response is not valid JSON

    return render_error_page(error_message, response.status_code)


@frontend.app_errorhandler(400)
def handle_400(_: Exception) -> str:
    """Handles HTTP 400 errors (Bad Request)."""
    return render_error_page("Bad Request – The request was invalid.", 400)


@frontend.app_errorhandler(401)
def handle_401(_: Exception) -> str:
    """Handles HTTP 401 errors (Unauthorized)."""
    return render_error_page("Unauthorized – You do not have permission.", 401)


@frontend.app_errorhandler(403)
def handle_403(_: Exception) -> str:
    """Handles HTTP 403 errors (Forbidden)."""
    return render_error_page("Forbidden – Access is not allowed.", 403)


@frontend.app_errorhandler(404)
def handle_404(_: Exception) -> str:
    """Handles HTTP 404 errors (Not Found)."""
    return render_error_page("Not Found – The requested page does not exist.", 404)


@frontend.app_errorhandler(405)
def handle_405(_: Exception) -> str:
    """Handles HTTP 405 errors (Method Not Allowed)."""
    return render_error_page("Method Not Allowed – The request contains a invalid method.", 405)


@frontend.app_errorhandler(500)
def handle_500(_: Exception) -> str:
    """Handles HTTP 500 errors (Internal Server Error)."""
    return render_error_page("Internal Server Error – An unexpected error occurred.", 500)


@frontend.route("/", methods=["GET"])
def index() -> str:
    """
    Render the landing page of the application.
    """
    return render_template("index.html")


@frontend.route("/create_ticket", methods=["GET"])
def create_ticket_page() -> str:
    """
    Render the page for ticket creation.
    """
    return render_template("create_ticket.html")


@frontend.route("/list_tickets", methods=["GET"])
def list_tickets_page() -> str:
    """
    Render a page listing all tickets.
    """
    try:
        response = requests.get(
            f"{API_BASE_URL}tickets",
            timeout=REQUEST_TIMEOUT,
            verify=os.path.join(current_app.instance_path, "ca.pem"),
        )
    except requests.exceptions.RequestException as e:
        return render_error_page(f"API Error: {e}", 500)
    return handle_api_response_with_data(
        cast(Response, response), "list_tickets.html", None, "tickets"
    )


@frontend.route("/list_hidden_tickets", methods=["GET"])
def list_hidden_tickets_page() -> str:
    """
    Render a page listing all hidden tickets.
    """
    try:
        response = requests.get(
            f"{API_BASE_URL}hidden_tickets",
            timeout=REQUEST_TIMEOUT,
            verify=os.path.join(current_app.instance_path, "ca.pem"),
        )
    except requests.exceptions.RequestException as e:
        return render_error_page(f"API Error: {e}", 500)
    return handle_api_response_with_data(
        cast(Response, response), "hidden_tickets.html", None, "tickets"
    )


@frontend.route("/check_in", methods=["GET"])
def check_in_page() -> str:
    """
    Render the check-in page for ticket validation.
    """
    return render_template("check_in.html")


@frontend.route("/qr_codes/<ticket_code>", methods=["GET"])
def get_qr_code(ticket_code: str) -> Union[Response, Tuple[str, int]]:
    """
    Serve the QR code image for the given ticket code.
    Args:
        ticket_code (str): The code of the ticket to retrieve the QR code for.
    Returns:
        Flask response with the QR code image or a 404 error if not found.
    """
    qr_path = os.path.join(current_app.config["QR_PATH"], f"{ticket_code}.png")
    if os.path.exists(qr_path):
        return send_file(qr_path, mimetype="image/png")
    return (
        "QR code not found",
        404,
    )


@frontend.route("/export_ticket/<ticket_code>", methods=["GET"])
def export_ticket(ticket_code: str) -> Union[Response, str]:
    """
    Fetches a ticket image from the backend API and returns it as a downloadable PNG file.

    Args:
        ticket_code (str): The code of the ticket to be exported.

    Returns:
        Response: A Flask response containing the ticket image with appropriate headers,
        or a rendered HTML error page if an error occurs during retrieval.
    """
    try:
        response = requests.get(
            f"{API_BASE_URL}export_ticket/{ticket_code}",
            timeout=REQUEST_TIMEOUT,
            verify=os.path.join(current_app.instance_path, "ca.pem"),
        )
    except requests.exceptions.RequestException as e:
        return render_error_page(f"API Error: {e}", 500)
    if response.status_code != 200:
        error_data = {}
        if hasattr(response, "json") and callable(response.json):
            try:
                error_data = response.json()
                if isinstance(error_data, dict) and "error" in error_data:
                    error_message = error_data["error"]
                    return render_error_page(error_message, response.status_code)
            except ValueError:
                pass  # Keep the default error message if the response is not valid JSON

    return Response(
        response.content,
        mimetype="image/png",
        headers={"Content-Disposition": f"attachment; filename=ticket_{ticket_code}.png"},
    )


@frontend.route("/hide_ticket/<ticket_code>", methods=["POST"])
def hide_ticket(ticket_code: str) -> Union[Response, str]:
    """
    Hide a ticket via the API and redirect.
    """
    try:
        response = requests.post(
            f"{API_BASE_URL}hide_ticket/{ticket_code}",
            timeout=REQUEST_TIMEOUT,
            verify=os.path.join(current_app.instance_path, "ca.pem"),
        )
    except requests.exceptions.RequestException as e:
        return render_error_page(f"API Error: {e}", 500)
    return handle_api_response(cast(Response, response), "frontend.list_tickets_page")


@frontend.route("/unhide_ticket/<ticket_code>", methods=["POST"])
def unhide_ticket(ticket_code: str) -> Union[Response, str]:
    """
    Unhide a ticket via the API and redirect.
    """
    try:
        response = requests.post(
            f"{API_BASE_URL}unhide_ticket/{ticket_code}",
            timeout=REQUEST_TIMEOUT,
            verify=os.path.join(current_app.instance_path, "ca.pem"),
        )
    except requests.exceptions.RequestException as e:
        return render_error_page(f"API Error: {e}", 500)
    return handle_api_response(cast(Response, response), "frontend.list_hidden_tickets_page")


@frontend.route("/mark_paid/<email>", methods=["POST"])
def mark_paid(email: str) -> Union[Response, str]:
    """
    Marks all tickets associated with the given email address as paid via the backend API.

    Sends a POST request to the API and redirects to the ticket list page.
    On API failure, a corresponding error page or message is shown.
    """
    data = {"email": email}
    try:
        response = requests.post(
            f"{API_BASE_URL}mark_paid",
            json=data,
            timeout=REQUEST_TIMEOUT,
            verify=os.path.join(current_app.instance_path, "ca.pem"),
        )
    except requests.exceptions.RequestException as e:
        return render_error_page(f"API Error: {e}", 500)
    return handle_api_response(cast(Response, response), "frontend.list_tickets_page")


@frontend.route("/send_ticket/<email>", methods=["POST"])
def send_tickets(email: str) -> Union[Response, str]:
    """
    Sends all tickets linked to the given email address by calling the backend API.

    On success, redirects to the ticket list page. If the API request fails,
    an error page is displayed.
    """
    data = {"email": email}
    try:
        response = requests.post(
            f"{API_BASE_URL}send_ticket_mail",
            json=data,
            timeout=REQUEST_TIMEOUT,
            verify=os.path.join(current_app.instance_path, "ca.pem"),
        )
    except requests.exceptions.RequestException as e:
        return render_error_page(f"API Error: {e}", 500)
    return handle_api_response(cast(Response, response), "frontend.list_tickets_page")

"""
This module provides a set of functions to send event tickets by e-mail
"""

import logging
import os
from typing import List
from smtplib import SMTPException
from flask import Flask, render_template
from flask_mail import Message, BadHeaderError
from bs4 import BeautifulSoup
import yaml
from .extensions import mail
from .utils import load_mail_config, get_file_name

logger = logging.getLogger(__name__)


def init_flask_mail(app: Flask) -> None:
    """
    Initialize Flask-Mail configuration for sending emails.

    Args:
        app (Flask): Flask application instance.

    Raises:
        RuntimeError: If mail configuration cannot be loaded or applied.
        ValueError: If a configuration value is invalid.
    """
    try:
        mail_config = load_mail_config()
    except (FileNotFoundError, KeyError, ValueError, yaml.YAMLError) as e:
        raise RuntimeError(f"Failed to load mail configuration: {e}") from e

    try:
        app.config.update(
            MAIL_SERVER=mail_config["mail_server"],
            MAIL_PORT=mail_config["mail_port"],
            MAIL_USE_TLS=mail_config.get("mail_use_tls", False),
            MAIL_USE_SSL=mail_config.get("mail_use_ssl", False),
            MAIL_USERNAME=mail_config["mail_username"],
            MAIL_PASSWORD=mail_config["mail_password"],
            MAIL_DEFAULT_SENDER=(
                f"{mail_config['mail_sender_name']} " f"<{mail_config['mail_sender_email']}>"
            ),
        )
        logger.info("Email configuration successfully applied.")
    except ValueError as e:
        raise ValueError(f"Invalid mail configuration value: {e}") from e


def send_simple_mail(recipient: str, subject: str, body: str) -> None:
    """
    Sends a simple text email.

    Args:
        recipient (str): Recipient email address (must already be validated).
        subject (str): Email subject.
        body (str): Email text content.

    Raises:
        ValueError: If subject or body is empty.
        BadHeaderError: If there is an issue with the email headers.
        ConnectionRefusedError: If the mail server is unreachable.
        SMTPException: If an SMTP error occurs while sending the email.
    """
    if not subject.strip() or not body.strip():
        raise ValueError("Subject and body must not be empty.")

    try:
        msg = Message(subject=subject.strip(), recipients=[recipient.strip()])
        msg.body = body.strip()
        mail.send(msg)
        logger.info("Email without ticket(s) sent successfully.")
    except (BadHeaderError, ConnectionRefusedError, SMTPException) as e:
        raise RuntimeError(f"Failed to send email to {recipient}: {e}") from e


def send_tickets(recipient: str, name: str, ticket_img_paths: List[str], pdf_path: str) -> None:
    """
    Sends an email with ticket images embedded and a PDF attachment.

    Args:
        recipient (str): Recipient email address (must already be validated).
        name (str): Name of the recipient.
        ticket_img_paths (List[str]): List of ticket image paths to embed in the email.
        pdf_path (str): Path to the ticket PDF to attach.

    Raises:
        ValueError: If required parameters are empty.
        FileNotFoundError: If a ticket image or PDF file does not exist.
        RuntimeError: If the email could not be sent.
    """
    msg = Message(subject="Your Tickets", recipients=[recipient.strip()])

    ticket_img_filenames = []
    try:
        for ticket_img_path in ticket_img_paths:
            if not os.path.isfile(ticket_img_path):
                raise FileNotFoundError(f"Ticket image file not found: {ticket_img_path}")

            with open(ticket_img_path, "rb") as ticket_img:
                ticket_img_filename = get_file_name(ticket_img_path)
                ticket_img_filenames.append(ticket_img_filename)
                msg.attach(
                    ticket_img_filename,
                    "image/png",
                    ticket_img.read(),
                    headers={"Content-ID": f"<{ticket_img_filename}>"},
                )

        if not os.path.isfile(pdf_path):
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        with open(pdf_path, "rb") as pdf_file:
            msg.attach(get_file_name(pdf_path), "application/pdf", pdf_file.read())

    except FileNotFoundError as e:
        raise FileNotFoundError(f"Attachment file missing: {e}") from e

    msg.html = render_template(
        "ticket_email.html", name=name, ticket_img_filenames=ticket_img_filenames
    )

    try:
        soup = BeautifulSoup(msg.html, "html.parser")
        html_sections = soup.find_all(
            None, class_=["greeting", "intro-text", "instructions", "closing-message"]
        )
        msg.body = "\n".join(section.get_text().strip() for section in html_sections if section)

    except (TypeError, AttributeError, ValueError) as e:
        raise RuntimeError(f"Failed to generate plaintext email body: {e}") from e

    try:
        mail.send(msg)
        logger.info("Email with ticket(s) sent successfully.")
    except (BadHeaderError, ConnectionRefusedError, SMTPException) as e:
        raise RuntimeError(f"Failed to send email to {recipient}: {e}") from e

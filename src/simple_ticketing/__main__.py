"""
This module initializes the Flask application and runs the main server.
"""

import os
import logging
import ssl
from sys import argv, stderr, stdout
from typing import Optional
from pathlib import Path
import importlib.metadata
import importlib.resources
from logging.handlers import TimedRotatingFileHandler
import colorlog
from flask import Flask
from simple_ticketing.extensions import mail
from simple_ticketing.email_operations import init_flask_mail
import simple_ticketing.cli as typer_module
from simple_ticketing.api_routes import api
from simple_ticketing.frontend_routes import frontend

__version__ = importlib.metadata.version("SimpleTicketing")

logger = logging.getLogger(__name__)


def setup_logging(
    log_file: Optional[str] = None,
    flask_level: int = logging.DEBUG,
    simple_ticketing_level: int = logging.DEBUG,
) -> None:
    """
    Set up logging configuration for the application.

    Args:
        log_file (Optional[str]): Path to the log file. If None, default is 'app.log'.
        flask_level (int): Logging level for Flask.
        simple_ticketing_level (int): Logging level for simple_ticketing.
    """
    log_file = log_file or os.path.join("instance", "SimpleTicketing.log")

    # Log format
    log_format = "%(asctime)s - %(levelname)s - %(name)s:%(lineno)d - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    # Console handler with color
    console_handler = logging.StreamHandler(stdout)
    console_formatter = colorlog.ColoredFormatter(
        "%(log_color)s%(asctime)s - %(levelname)s - %(name)s:%(lineno)d - %(message)s",
        datefmt=date_format,
        log_colors={
            "DEBUG": "cyan",
            "INFO": "green",
            "WARNING": "yellow",
            "ERROR": "red",
            "CRITICAL": "bold_red",
        },
    )
    console_handler.setFormatter(console_formatter)

    # File handler with daily rotation
    file_handler = TimedRotatingFileHandler(
        log_file, when="midnight", interval=1, backupCount=7, encoding="utf-8"
    )
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter(log_format, datefmt=date_format)
    file_handler.setFormatter(file_formatter)

    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    # Flask and simple_ticketing use the same logging config
    logging.getLogger("werkzeug").setLevel(flask_level)
    logging.getLogger("simple_ticketing").setLevel(simple_ticketing_level)

    # Error handling in logging
    try:
        logger.info("Logging initialized successfully.")
    except (OSError, IOError) as e:
        print(f"Logging initialization failed due to file error: {e}", file=stderr)
    except ValueError as e:
        print(
            f"Logging initialization failed due to configuration error: {e}",
            file=stderr,
        )
    except AttributeError as e:
        print(f"Unexpected error during logging initialization: {e}", file=stderr)


def create_app() -> Flask:
    """
    Initializes and configures the Flask application for the ticketing system.

    This function sets up the Flask application by registering the necessary
    routes and configurations.

    Returns:
        Flask: The configured Flask application instance.
    """
    templates_path = str(importlib.resources.files("simple_ticketing").joinpath("templates"))
    static_path = str(importlib.resources.files("simple_ticketing").joinpath("static"))
    instance_path = str(os.path.join(Path.cwd(), "instance"))

    logger.info("Initialize Flask")
    logger.info("Working directory: %s", instance_path)
    ticketing = Flask(
        __name__,
        template_folder=templates_path,
        static_folder=static_path,
        instance_path=instance_path,
    )
    ticketing.config["APP_VERSION"] = __version__
    ticketing.config["QR_PATH"] = os.path.join(instance_path, "data", "qr_codes")
    ticketing.config["TICKET_IMAGE_PATH"] = os.path.join(instance_path, "data", "tickets")
    ticketing.config["TICKET_PDF_PATH"] = os.path.join(instance_path, "data", "pdf")
    ticketing.config["TMP_PATH"] = os.path.join(instance_path, "data", "tmp")
    ticketing.config["FONTS_PATH"] = os.path.join(static_path, "fonts", "3rd_party")
    logger.info("Flask has been initialized.")

    # Initialize Flask Mail
    logger.info("Initialize Flask-Mail")
    init_flask_mail(ticketing)
    mail.init_app(ticketing)
    logger.info("Flask-Mail has been initialized.")

    # Register Blueprints
    logger.info("Register Flask Blueprints")
    logger.info("Register API")
    ticketing.register_blueprint(api, url_prefix="/api")
    logger.info("Register Frontend")
    ticketing.register_blueprint(frontend)
    logger.info("Flask Blueprints have been registered.")

    return ticketing


def get_ssl_context() -> ssl.SSLContext:
    """
    Sets up SSL context for HTTPS with CA verification.

    Returns:
        ssl.SSLContext: Configured SSL context.
    """
    logger.info("Setup SSL context")
    cert_path = os.getenv("SSL_CERT_PATH", os.path.join("instance", "cert.pem"))
    logger.debug("Certificate path: %s", cert_path)
    key_path = os.getenv("SSL_KEY_PATH", os.path.join("instance", "key.pem"))
    logger.debug("Key path: %s", key_path)
    ca_path = os.getenv("SSL_CA_PATH", os.path.join("instance", "ca.pem"))
    logger.debug("CA-Certificate path: %s", ca_path)

    context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    context.load_cert_chain(certfile=cert_path, keyfile=key_path)
    context.load_verify_locations(cafile=ca_path)
    context.verify_mode = ssl.CERT_OPTIONAL  # Change to CERT_REQUIRED if needed
    logger.info("SSL context has been setup.")
    return context


def main() -> None:
    """Main function to start the Flask application."""
    setup_logging()

    if len(argv) == 1:
        application = create_app()
        ssl_context = get_ssl_context()
        debug_mode = os.getenv("FLASK_DEBUG", "True").lower() in ["true", "1"]

        application.run(host="0.0.0.0", port=5000, debug=debug_mode, ssl_context=ssl_context)
    else:
        typer_module.app()


if __name__ == "__main__":
    main()

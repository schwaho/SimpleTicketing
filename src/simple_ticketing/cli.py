"""
This module provides argument parsing functions at start-up
"""

import os
import logging
import shutil
from importlib import resources
import typer as typer_module
from simple_ticketing.database import db_init, db_clear
from simple_ticketing.cert import create_ca, create_signed_certificate

app = typer_module.Typer()

logger = logging.getLogger(__name__)


def confirm_execution(skip_confirmation: bool, message: str) -> bool:
    """
    Helper function to confirm the execution of a command.
    If `skip_confirmation` is True, skips the confirmation step.
    """
    if skip_confirmation:
        return True

    confirmation = input(f"{message} (y/n): ").strip().lower()
    return confirmation == "y"


def safe_remove(path: str) -> None:
    """Safely removes a file, a symbolic link or a folder content."""
    if os.path.isfile(path) or os.path.islink(path):
        os.unlink(path)
    elif os.path.isdir(path):
        for sub_element in os.listdir(path):
            safe_remove(os.path.join(path, sub_element))


def copy_examples(instance_dir: str) -> None:
    """Copy example config files into instance directory"""
    with resources.as_file(resources.files("simple_ticketing").joinpath("examples")) as examples:

        if not examples.is_dir():
            logger.warning("Examples directory does not exist in package.")
            return

        for item in examples.iterdir():
            dst = os.path.join(instance_dir, item.name)

            if item.is_dir():
                shutil.copytree(item, dst, dirs_exist_ok=True)
            else:
                shutil.copy2(item, dst)


@app.command()
def init() -> None:
    """
    Sets up the directory structure and init the database.
    """

    instance_dir = os.path.join("instance")
    data_dir = os.path.join(instance_dir, "data")
    structur = ["qr_codes", "tickets", "pdf", "tmp"]

    if not os.path.exists(data_dir):
        for path in structur:
            new_dir = os.path.join(data_dir, path)
            os.makedirs(new_dir, exist_ok=True)
            logger.debug("Create dir: %s", new_dir)
        logger.info("Directory structure has been created.")

        copy_examples(instance_dir)

        db_init()
        logger.info("Database has been created.")

        ca_cert, ca_key = create_ca()
        create_signed_certificate(ca_cert, ca_key)
        logger.info("SSL-Certificates have been created.")

        logger.info("Init-Command executed!")
    else:
        logger.info("There is nothing to do.")


@app.command()
def clear(y: bool = typer_module.Option(False, "--yes", "-y", help="Skip confirmation")) -> None:
    """
    Clears all ticket data. Skips confirmation with -y.
    """
    data_dir = os.path.join("instance", "data")
    db_path = os.path.join(data_dir, "tickets.db")

    if confirm_execution(y, "Are you sure you want to clear data?"):
        if os.path.exists(data_dir):
            for element in os.listdir(data_dir):
                element_path = os.path.join(data_dir, element)
                if element_path != db_path:
                    safe_remove(element_path)
                    logger.debug("Deleted: %s", element_path)
            logger.info("All ticket files have been deleted.")

            db_clear()
            logger.info("Database has been cleared.")

            logger.info("Clear-Command executed!")
        else:
            logger.info("There is nothing to do.")
    else:
        logger.info("Clear-Command aborted.")


@app.command()
def reset(y: bool = typer_module.Option(False, "--yes", "-y", help="Skip confirmation")) -> None:
    """
    Delete ticket data and the database. Requires init to be rerun. Skips confirmation with -y.
    """
    instance_dir = "instance"
    data_dir = os.path.join(instance_dir, "data")
    files_to_delete = [
        "ca.pem",
        "ca-key.pem",  # CA Certificate & Key
        "cert.pem",
        "key.pem",  # Server Certificate & Key
        "app.yaml",
        "email.yaml",
        "event.yaml",
        "ticket_layout.yaml",
        "event_img.jpg",
    ]

    if confirm_execution(y, "Are you sure you want to prune data?"):
        for file in files_to_delete:
            file_path = os.path.join(instance_dir, file)
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.debug("Deleted: %s", file_path)
        logger.info("SSL-Certificates, configuration and misc files have been deleted.")

        if os.path.exists(data_dir):
            for element in os.listdir(data_dir):
                element_path = os.path.join(data_dir, element)
                if os.path.isfile(element_path) or os.path.islink(element_path):
                    os.unlink(element_path)
                    logger.debug("Deleted (file): %s", element_path)
                elif os.path.isdir(element_path):
                    shutil.rmtree(element_path)  # Remove dir and content
                    logger.debug("Deleted (dir): %s", element_path)
            os.rmdir(data_dir)  # Remove dir if empty
            logger.debug("Deleted (dir): %s", data_dir)

            logger.info("All ticket files have been deleted.")
            logger.info("Database has been deleted.")
            logger.info("Reset-Command executed!")
        else:
            logger.info("There is nothing to do.")
    else:
        logger.info("Reset-Command aborted.")


if __name__ == "__main__":
    app()

"""
This module provides functions for generating ticket images with QR codes.
It processes configuration files, loads fonts and images, and draws
texts as well as a QR code onto the ticket. Additionally, it provides
functions for saving the generated ticket images.

Main Features:
- Creates and saves a QR code for a ticket.
- Loads the necessary fonts for ticket creation.
- Determines the size of a text with a specific font.
- Draws ticket texts, including seat information.
- Adds an event image to the ticket.
- Draws the QR code onto the ticket.
- Creates a complete ticket image with text, event image, and QR code.
- Saves the generated ticket image as a PNG file.
"""

import io
import os
import logging
from typing import Tuple, Union, Dict, Any
import qrcode
import qrcode.exceptions
from PIL import Image, ImageDraw, ImageFont
from flask import current_app
from simple_ticketing.utils import load_config, validate_config

logger = logging.getLogger(__name__)
FontType = Union[ImageFont.FreeTypeFont, ImageFont.ImageFont]


def create_qr_code(ticket_code: str, qr_path: str) -> str:
    """
    Create and save the ticket code in a QR-Code

    Args:
        ticket_code (str): Ticket code to be saved in the QR Code
        qr_path (str): Path the QR Code to be stored

    Returns:
        str: Path to the QR Code

    Raises:
        TypeError: If `ticket_code` is not a string.
        ValueError: If `ticket_code` is an empty string or
                    if `error_correction` value is invalid.
        FileNotFoundError: If the QR code configuration file is not found.
        KeyError: If any required key is missing in the configuration.
        RuntimeError: If the ticket code data exceeds the QR code's capacity.
        IOError: If an error occurs while saving the QR code image.
    """
    if not isinstance(ticket_code, str):
        logger.error("Invalid ticket code type: %s", type(ticket_code))
        raise TypeError("ticket_code must be a string.")
    if not ticket_code.strip():
        logger.error("Empty ticket code provided.")
        raise ValueError("ticket_code must not be empty.")

    logger.debug("Loading QR code configuration...")
    try:
        qr_config = load_config("ticket_layout.yaml", "qr_code")
        validate_config(
            qr_config,
            [
                "version",
                "error_correction",
                "box_size",
                "border",
                "fill_color",
                "back_color",
            ],
        )
    except (FileNotFoundError, KeyError) as e:
        logger.critical("Failed to load QR code configuration.")
        raise type(e) from e

    logger.debug("Creating QR code for ticket: %s", ticket_code)
    try:
        qr = qrcode.QRCode(
            version=qr_config["version"],
            error_correction=getattr(
                qrcode.constants, f"ERROR_CORRECT_{qr_config['error_correction']}"
            ),
            box_size=qr_config["box_size"],
            border=qr_config["border"],
        )
        qr.add_data(ticket_code)
        qr.make(fit=True)
        qr_img = qr.make_image(
            fill_color=qr_config["fill_color"], back_color=qr_config["back_color"]
        )
    except AttributeError as e:
        logger.critical("Invalid Value of key 'error_correction'.")
        raise ValueError(
            "Invalid Value of key 'error_correction'. Valid values are: 'L', 'M', 'Q', 'H'."
        ) from e
    except qrcode.exceptions.DataOverflowError as e:
        logger.critical("QR Code generation failed")
        raise RuntimeError(f"QR Code generation failed: {e}") from e

    try:
        with open(qr_path, "wb") as f:
            qr_img.save(f)
            logger.info("QR code saved successfully: %s", qr_path)
    except OSError as e:
        logger.critical("Error while saving QR code.")
        raise IOError(f"Error while saving QR-Code '{qr_path}': {e}") from e
    return qr_path


def load_fonts(
    font_title: str,
    font_title_size: int,
    font_text: str,
    font_text_size: int,
    font_misc_size: int,
) -> Tuple[
    FontType,
    FontType,
    FontType,
]:
    """
    Loads the required fonts for ticket generation.

    Args:
        font_title (str): Name of the title font file.
        font_title_size (int): Font size for the title.
        font_text (str): Name of the text font file.
        font_text_size (int): Font size for the main text.
        font_misc_size (int): Font size for miscellaneous text.

    Returns:
        tuple: Loaded fonts for title, text, and miscellaneous use.
    """

    def load_font(font_name: str, size: int) -> FontType:
        try:
            logger.debug("Loading font: %s, size: %d", font_name, size)
            return ImageFont.truetype(
                os.path.join(current_app.config["FONTS_PATH"], font_name), size
            )
        except IOError:
            logger.warning("Font not found: %s, using default font.", font_name)
            return ImageFont.load_default()

    return (
        load_font(font_title, font_title_size),
        load_font(font_text, font_text_size),
        load_font(font_text, font_misc_size),
    )


def textsize(text: str, font: FontType) -> Tuple[float, float]:
    """
    Return the Size of a Text

    Args:
        text (str): Text as String
        font (FontType): Font object

    Returns:
        tuple: text_width, text_height
    """
    logger.debug("Calculating text size for: '%s' with font: %s", text, font)

    img = Image.new("RGB", (200, 200), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    text_bbox = draw.textbbox((0, 0), text, font=font)

    text_width, text_height = text_bbox[2] - text_bbox[0], text_bbox[3] - text_bbox[1]
    logger.debug("Calculated text size: width=%d, height=%d", text_width, text_height)
    return text_width, text_height


def draw_ticket_text(
    draw: ImageDraw.ImageDraw,
    fonts: Tuple[FontType, FontType, FontType],
    seat: str,
) -> float:
    """
    Draws text elements on the ticket image.

    Args:
        draw (ImageDraw.ImageDraw): Drawing context for the ticket image.
        fonts (tuple): Loaded fonts (title, text, misc).
        seat (str): Seat type or designation.

    Returns:
        float: Y-position for the next ticket element.

    Raises:
        FileNotFoundError: If the YAML configuration file is not found.
        KeyError: If a required key is not present in the configuration file.
    """
    logger.debug("Drawing ticket text for seat: %s", seat)

    try:
        event_config = load_config("event.yaml", "event")
        validate_config(
            event_config,
            ["event_title", "ticket_line1", "ticket_line2", "ticket_seat_line"],
        )
        ticket_config = load_config("ticket_layout.yaml", "ticket_export")
        validate_config(ticket_config, ["img_width", "text_color"])
    except (FileNotFoundError, KeyError) as e:
        logger.critical("Failed to load configuration.")
        raise type(e) from e

    fonts_dict = {"title": fonts[0], "text": fonts[1], "misc": fonts[2]}
    ticket_style = {
        "text_color": tuple(ticket_config["text_color"]),
        "border": ticket_config["border"],
        "line_spacing": ticket_config["line_spacing"],
    }

    logger.debug("Drawing event title: %s", event_config["event_title"])
    title_width, title_height = textsize(event_config["event_title"], fonts_dict["title"])
    draw.text(
        ((ticket_config["img_width"] - title_width) / 2, ticket_style["border"]),
        event_config["event_title"],
        fill=ticket_style["text_color"],
        font=fonts_dict["title"],
    )

    y_offset = float(ticket_style["border"] + 2 * title_height + ticket_style["line_spacing"])

    text_lines = [
        event_config["ticket_line1"],
        event_config["ticket_line2"],
        f"{event_config['ticket_seat_line']} {seat}",
    ]

    logger.debug("Drawing additional ticket text lines.")

    for line in text_lines:
        _, line_height = textsize(line, fonts_dict["text"])
        draw.text(
            (ticket_style["border"], y_offset),
            line,
            fill=ticket_style["text_color"],
            font=fonts_dict["text"],
        )
        y_offset += float(line_height + ticket_style["line_spacing"])

    logger.info("Ticket text drawn successfully. Next element Y-position: %f", y_offset)
    return y_offset


def draw_event_img(
    img: Image.Image,
    draw: ImageDraw.ImageDraw,
    fonts: Tuple[FontType, FontType, FontType],
    y_offset: float,
) -> None:
    """
    Adds an event image to the ticket.

    Args:
        img (Image.Image): The ticket image.
        draw (ImageDraw.ImageDraw): Drawing context for the ticket image.
        fonts (tuple): Loaded fonts (title, text, misc).
        y_offset (float): Offset for the event image on the ticket.

    Raises:
        FileNotFoundError: If the YAML configuration file is not found.
        KeyError: If a required key is not present in the configuration file.
        RuntimeError: If loading or processing of the event image fails.
    """
    logger.debug("Adding event image to the ticket at Y-offset: %f", y_offset)

    try:
        ticket_config = load_config("ticket_layout.yaml", "ticket_export")
        validate_config(ticket_config, ["img_width", "img_height", "border", "text_color"])
    except (FileNotFoundError, KeyError) as e:
        logger.critical("Failed to load configuration.")
        raise type(e) from e

    ticket_style = {
        "width": ticket_config["img_width"],
        "height": ticket_config["img_height"],
        "border": ticket_config["border"],
        "text_color": tuple(ticket_config["text_color"]),
    }

    max_dimensions = (
        ticket_style["width"] - 2 * ticket_style["border"],
        ticket_style["height"] - 2 * ticket_style["border"],
    )

    try:
        event_img_path = os.path.join(current_app.instance_path, "event_img.jpg")
        logger.debug("Loading event image from: %s", event_img_path)

        event_img = Image.open(event_img_path).convert("RGB")
        event_img.thumbnail(max_dimensions)

        img.paste(event_img, (ticket_style["border"], int(y_offset)))
        logger.info("Event image successfully added to the ticket.")

    except FileNotFoundError:
        logger.warning(
            "Event image file not found: %s. Drawing placeholder instead.",
            event_img_path,
        )
        draw_missing_image_message(
            draw,
            ticket_style,
            {"title": fonts[0], "text": fonts[1], "misc": fonts[2]},
            y_offset,
        )

    except OSError as e:
        logger.critical("Error while loading or processing the event image: %s", e)
        raise RuntimeError(f"Failed to load event image: {e}") from e


def draw_missing_image_message(
    draw: ImageDraw.ImageDraw,
    ticket_style: Dict[str, Any],
    fonts_dict: Dict[str, FontType],
    y_offset: float,
) -> None:
    """
    Draws a "missing image" message on the ticket.

    Args:
        draw (ImageDraw.ImageDraw): Drawing context for the ticket image.
        ticket_style (dict): Contains width, height, border, text_color for the ticket.
        fonts_dict (dict): Contains title, text, and misc fonts.
        y_offset (float): The Y-position where the message should be drawn.
    """
    logger.warning("Event image missing. Displaying placeholder message.")

    message = "event_img.jpg missing"

    text_size = textsize(message, fonts_dict["misc"])  # Calculate size of the message
    text_x = (ticket_style["width"] - text_size[0]) / 2  # Center the text

    draw.text(
        (text_x, y_offset),
        message,
        fill=ticket_style["text_color"],
        font=fonts_dict["misc"],
    )
    logger.info("Placeholder text drawn at Y-offset: %f", y_offset)


def draw_qr_code(
    img: Image.Image,
    draw: ImageDraw.ImageDraw,
    fonts: Tuple[FontType, FontType, FontType],
    ticket_code: str,
) -> None:
    """
    Adds a QR code to the bottom of the ticket image.

    Args:
        img (Image.Image): The ticket image.
        draw (ImageDraw.ImageDraw): Drawing context for the ticket image.
        fonts (tuple): Loaded fonts (title, text, misc).
        ticket_code (str): Unique code for the ticket.

    Raises:
        FileNotFoundError: If the YAML configuration file or QR-Code is not found.
        KeyError: If a required key is not present in the configuration file.
        RuntimeError: If loading or processing QR code image fails.
    """
    logger.debug("Adding QR code for ticket: %s", ticket_code)

    try:
        ticket_config = load_config("ticket_layout.yaml", "ticket_export")
        validate_config(ticket_config, ["img_width", "img_height", "line_spacing", "text_color"])
    except (FileNotFoundError, KeyError) as e:
        logger.critical("Failed to load configuration.")
        raise type(e) from e

    ticket_style = {
        "width": ticket_config["img_width"],
        "height": ticket_config["img_height"],
        "line_spacing": ticket_config["line_spacing"],
        "text_color": tuple(ticket_config["text_color"]),
    }
    fonts_dict = {"title": fonts[0], "text": fonts[1], "misc": fonts[2]}
    qr_path = os.path.join(current_app.config["QR_PATH"], f"{ticket_code}.png")

    try:
        logger.debug("Loading QR code image from: %s", qr_path)
        qr_img = Image.open(qr_path).resize((ticket_style["width"], ticket_style["width"]))

        img.paste(qr_img, (0, ticket_style["height"] - ticket_style["width"]))
        logger.info("QR code added successfully for ticket: %s", ticket_code)

    except FileNotFoundError:
        logger.warning(
            "QR code image not found for ticket: %s. Displaying placeholder message.",
            ticket_code,
        )
        draw_missing_qr_code_message(draw, ticket_style, fonts_dict, "QR-Code is missing.")

    except OSError as e:
        logger.critical(
            "Error while loading or processing QR code image for ticket: %s",
            ticket_code,
        )
        raise RuntimeError(f"Failed to load QR code image: {e}") from e

    draw_ticket_code(draw, ticket_style, fonts_dict, ticket_code)
    logger.info("Ticket code drawn successfully for ticket: %s", ticket_code)


def draw_missing_qr_code_message(
    draw: ImageDraw.ImageDraw,
    ticket_style: Dict[str, Any],
    fonts_dict: Dict[str, FontType],
    message: str,
) -> None:
    """
    Draws a "missing QR code" message at the bottom of the ticket.

    Args:
        draw (ImageDraw.Draw): Drawing context for the ticket image.
        ticket_style (dict): Contains width, height, line_spacing, text_color for the ticket.
        fonts_dict (dict): Contains title, text, and misc fonts.
        message (str): The message to display when the QR code is missing.
    """
    logger.warning("QR code missing. Displaying placeholder message: '%s'", message)

    text_size = textsize(message, fonts_dict["misc"])
    text_x = (ticket_style["width"] - text_size[0]) / 2  # Center the text

    draw.text(
        (text_x, ticket_style["height"] - 3 * ticket_style["line_spacing"]),
        message,
        fill=ticket_style["text_color"],
        font=fonts_dict["misc"],
    )
    logger.info("Placeholder text for missing QR code drawn successfully.")


def draw_ticket_code(
    draw: ImageDraw.ImageDraw,
    ticket_style: Dict[str, Any],
    fonts_dict: Dict[str, FontType],
    ticket_code: str,
) -> None:
    """
    Draws the ticket code below the QR code.

    Args:
        draw (ImageDraw.Draw): Drawing context for the ticket image.
        ticket_style (dict): Contains width, height, line_spacing, text_color for the ticket.
        fonts_dict (dict): Contains title, text, and misc fonts.
        ticket_code (str): The unique ticket code to display.
    """
    logger.debug("Drawing ticket code: %s", ticket_code)

    text_size = textsize(ticket_code, fonts_dict["misc"])
    text_x = (ticket_style["width"] - text_size[0]) / 2  # Center the text
    text_y = ticket_style["height"] - ticket_style["width"]

    draw.text(
        (text_x, text_y),
        ticket_code,
        fill=ticket_style["text_color"],
        font=fonts_dict["misc"],
    )

    logger.info("Ticket code drawn at position: (%.2f, %.2f)", text_x, text_y)


def create_ticket_image(seat: str, ticket_code: str) -> io.BytesIO:
    """
    Creates a ticket image with text and a QR code.

    Args:
        seat (str): Seat (e.g. number) or designation.
        ticket_code (str): Unique ticket code.

    Returns:
        io.BytesIO: A byte stream containing the generated ticket image.

    Raises:
        FileNotFoundError: If the YAML configuration file is not found.
        KeyError: If a required key is not present in the configuration file.
    """
    logger.info("Generating ticket image for seat: %s, ticket code: %s", seat, ticket_code)

    try:
        ticket_config = load_config("ticket_layout.yaml", "ticket_export")
        validate_config(
            ticket_config,
            [
                "img_width",
                "img_height",
                "background_color",
                "font_title",
                "font_title_size",
                "font_text",
                "font_text_size",
                "font_misc_size",
            ],
        )
    except (FileNotFoundError, KeyError) as e:
        logger.critical("Failed to load or validate ticket configuration.")
        raise type(e) from e

    img_width, img_height = ticket_config["img_width"], ticket_config["img_height"]
    background_color = tuple(ticket_config["background_color"])
    img = Image.new("RGB", (img_width, img_height), background_color)
    draw = ImageDraw.Draw(img)
    logger.debug("Ticket image canvas created with size: (%d, %d)", img_width, img_height)

    fonts = load_fonts(
        ticket_config["font_title"],
        ticket_config["font_title_size"],
        ticket_config["font_text"],
        ticket_config["font_text_size"],
        ticket_config["font_misc_size"],
    )
    logger.debug("Fonts loaded successfully.")

    y_offset = draw_ticket_text(draw, fonts, seat)
    draw_event_img(img, draw, fonts, y_offset)
    draw_qr_code(img, draw, fonts, ticket_code)

    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format="PNG")
    img_byte_arr.seek(0)
    logger.info("Ticket image generated successfully for ticket code: %s", ticket_code)

    return img_byte_arr


def save_ticket_image(img_byte_arr: io.BytesIO, ticket_code: str) -> str:
    """
    Save a Ticket image as PNG file.

    Args:
        img_byte_arr (io.BytesIO): A byte stream containing the generated ticket image.
        ticket_code (str): Ticket code of the ticket.

    Returns:
        str: Path to the saved ticket image.

    Raises:
        RuntimeError: If an error occurs during processing, such as
            - Failed to open image stream.
            - Failed to save ticket image.
    """
    logger.debug("Saving ticket image for ticket code: %s", ticket_code)

    img_byte_arr.seek(0)

    try:
        image = Image.open(img_byte_arr)
    except OSError as e:
        logger.critical("Failed to open image stream for ticket code: %s", ticket_code)
        raise RuntimeError(f"Cannot open image stream: {e}") from e

    path = os.path.join(current_app.config["TICKET_IMAGE_PATH"], f"{ticket_code}.png")

    try:
        image.save(path, format="PNG")
        logger.info("Ticket image saved successfully: %s", path)
    except OSError as e:
        logger.critical("Failed to save ticket image: %s", path)
        raise RuntimeError(f"Error saving ticket image: {e}") from e

    img_byte_arr.seek(0)

    return path

"""
This module provides functions for generating customized ticket PDFs for events.

Main Features:
- Calculation of cell sizes for the ticket layout in the PDF.
- Loading and validating PDF properties from a configuration file.
- Processing and scaling ticket images to fit optimally within the layout.
- Placing tickets in a grid on the PDF page.
- Creating a multi-page PDF if more tickets need to be accommodated.
"""

import os
import logging
from typing import Tuple, Union, Dict, List, cast
from reportlab.lib import pagesizes
from reportlab.pdfgen import canvas
from PIL import Image
from flask import current_app
from simple_ticketing.utils import load_config, validate_config

logger = logging.getLogger(__name__)


def calculate_cell_dimensions(
    page_width: float, page_height: float, border: float, rows: int, cols: int
) -> Tuple[float, float]:
    """
    Calculate the dimensions of cells on a PDF page based on the page size, border and grid.

    Args:
        page_width (float): The total width of the page (pixel).
        page_height (float): The total height of the page (pixel).
        border (float): The border size around the page (pixel).
        rows (int): The number of rows in the grid.
        cols (int): The number of columns in the grid.

    Returns:
        tuple (float): Cell width, Cell height

    Raises:
        TypeError: If any of the parameter types are invalid, such as:
            - `page_width` or `page_height` is not an `int` or `float`.
            - `border` is not an `int` or `float`.
            - `rows` or `cols` is not an `int`.
        ValueError:  If any of the parameter values are invalid, such as:
            - `rows` or `cols` is less than or equal to 0.
            - `border` is negative.
            - `page_width` or `page_height` is not greater than twice the border.
    """
    if not isinstance(page_width, (int, float)) or not isinstance(page_height, (int, float)):
        logger.critical(
            "Invalid type for page dimensions: page_width=%s, page_height=%s",
            type(page_width),
            type(page_height),
        )
        raise TypeError("page_width and page_height must be numbers (int or float).")

    if not isinstance(border, (int, float)):
        logger.critical("Invalid type for border: %s", type(border))
        raise TypeError("border must be a number (int or float).")

    if not isinstance(rows, int) or not isinstance(cols, int):
        logger.critical(
            "Invalid type for grid dimensions: rows=%s, cols=%s", type(rows), type(cols)
        )
        raise TypeError("rows and cols must be integers.")

    if rows <= 0 or cols <= 0:
        logger.critical(
            "Invalid grid dimensions: rows=%d, cols=%d. Must be greater than 0.",
            rows,
            cols,
        )
        raise ValueError("Rows and columns must be greater than 0.")

    if border < 0:
        logger.critical("Invalid border value: %.2f. Border cannot be negative.", border)
        raise ValueError("Border size cannot be negative.")

    if page_width <= 2 * border or page_height <= 2 * border:
        logger.critical(
            "Page size is too small for the given border: page_width=%.2f, page_height=%.2f, "
            "border=%.2f",
            page_width,
            page_height,
            border,
        )
        raise ValueError("Page size must be larger than twice the border.")

    logger.debug(
        "Calculating cell dimensions: page_width=%.2f, page_height=%.2f, border=%.2f, "
        "rows=%d, cols=%d",
        page_width,
        page_height,
        border,
        rows,
        cols,
    )

    pa_width = page_width - 2 * border
    pa_height = page_height - 2 * border
    cell_width, cell_height = pa_width / cols, pa_height / rows

    logger.info(
        "Cell dimensions calculated successfully: width=%.2f, height=%.2f",
        cell_width,
        cell_height,
    )
    return cell_width, cell_height


def get_pdf_properties() -> Dict[str, Union[float, int, str]]:
    """
    Reads the configuration from a YAML file (expected to be named "pdf_export"),
    validates the configuration, and computes the cell width and height for a grid layout
    on a specified page size.

    Returns:
        dict: A dictionary containing the following keys:
            - cell_width (float): The width of each cell.
            - cell_height (float): The height of each cell.
            - border (float): The border size around the page.
            - page_width (float): The total width of the page.
            - page_height (float): The total height of the page.
            - page_size_name (str): The name of the page size (e.g., "A4", "letter").
            - rows (int): The number of rows in the grid.
            - cols (int): The number of columns in the grid.

    Raises:
        FileNotFoundError: If the configuration file ("pdf_export") does not exist.
        KeyError: If any required keys ("page_size_name", "border", "rows", "cols") are missing
            in the configuration.
        ValueError: If any of the configuration values are invalid, such as:
            - Unknown page size.
            - Non-numeric or negative values for "border", "rows", or "cols".
            - "rows" or "cols" being zero.
            - Page size being too small to accommodate the specified border.
    """
    logger.debug("Loading and validating PDF export configuration.")

    try:
        pdf_export_config = load_config("ticket_layout.yaml", "pdf_export")
        required_keys = ["page_size_name", "border", "rows", "cols"]
        validate_config(pdf_export_config, required_keys)
    except (FileNotFoundError, KeyError) as e:
        logger.critical("Failed to load or validate PDF export configuration.")
        raise type(e) from e

    page_size_name = pdf_export_config["page_size_name"]

    if hasattr(pagesizes, page_size_name):
        page_width, page_height = getattr(pagesizes, page_size_name)
    else:
        logger.critical("Unknown page size: %s. Supported sizes: 'A4', 'letter'.", page_size_name)
        raise ValueError(f"Unknown page size: {page_size_name}. Try 'A4' or 'letter'.")

    border = pdf_export_config["border"]
    rows, cols = pdf_export_config["rows"], pdf_export_config["cols"]

    cell_width, cell_height = calculate_cell_dimensions(page_width, page_height, border, rows, cols)

    logger.info(
        "PDF properties successfully loaded: page_size=%s, border=%.2f, rows=%d, cols=%d",
        page_size_name,
        border,
        rows,
        cols,
    )

    return {
        "cell_width": cell_width,
        "cell_height": cell_height,
        "border": border,
        "page_width": page_width,
        "page_height": page_height,
        "page_size_name": page_size_name,
        "rows": rows,
        "cols": cols,
    }


def process_image(
    image_path: str,
    cell_dimensions: Tuple[Union[float, int], Union[float, int]],
    temp_path: str,
) -> Tuple[float, float]:
    """
    Process an image to fit within the specified cell dimensions.

    This function rotates and calculates the scaling of an image if necessary to ensure
    it fits optimally within the given cell dimensions while maintaining its aspect ratio.
    It also saves the processed image temporarily.

    Args:
        image_path (str): The file path to the input image.
        cell_dimensions (Tuple[Union[float, int], Union[float, int]]): The target cell dimensions
            with width and height (both float or int).
        temp_path (str): The file path where the processed temporary image will be saved.

    Returns:
        tuple: A tuple (scaled_width, scaled_height) representing the width and height
            of the scaled image in pixels.

    Raises:
        FileNotFoundError: If the specified image_path does not exist.
        IOError: If the image cannot be opened or saved due to an I/O issue.
    """
    logger.debug(
        "Processing image: %s for cell dimensions: %s, saving to: %s",
        image_path,
        cell_dimensions,
        temp_path,
    )

    if not os.path.exists(image_path):
        logger.critical("Image file not found: %s", image_path)
        raise FileNotFoundError(f"Image file not found: {image_path}")

    try:
        with Image.open(image_path) as img_file:
            img = img_file.copy()
        img_width, img_height = img.size
        cell_width, cell_height = cell_dimensions

        logger.debug("Original image size: width=%d, height=%d", img_width, img_height)

        # Rotate image if necessary
        if (img_width / img_height) < (cell_width / cell_height):
            img = img.rotate(90, expand=True)
            img_width, img_height = img.size
            logger.info(
                "Rotated image for better fit: new size width=%d, height=%d",
                img_width,
                img_height,
            )

        # Calculate scaling
        scale = min(cell_width / img_width, cell_height / img_height)
        scaled_width = img_width * scale
        scaled_height = img_height * scale

        logger.debug(
            "Scaling image: scale factor=%.2f, new size: width=%.2f, height=%.2f",
            scale,
            scaled_width,
            scaled_height,
        )

        # Save temporary image
        img.save(temp_path)
        logger.info("Processed image saved to: %s", temp_path)

        return scaled_width, scaled_height

    except OSError as e:
        logger.critical("Error processing image: %s", e)
        raise IOError(f"Failed to open or save image: {e}") from e


def draw_ticket_on_canvas(
    c: canvas.Canvas,
    image_path: str,
    cell_dimensions: Tuple[Union[float, int], Union[float, int]],
    position: Tuple[Union[float, int], Union[float, int]],
    temp_image_path: str,
) -> None:
    """
    Draws a single ticket image on the PDF canvas, centered within a specified cell.

    Parameters:
        c (canvas.Canvas): The PDF canvas on which the image will be drawn.
        image_path (str): The file path to the source image to be drawn.
        cell_dimensions (Tuple[Union[float, int], Union[float, int]]): The cell width and height.
        position (Tuple[Union[float, int], Union[float, int]]): The (x, y) coordinates of the
                                                                 bottom-left corner of the cell.
        temp_image_path (str): The temporary file path where the processed image
                                is saved before being drawn.

    Details:
        - The function scales the image to fit within the specified cell dimensions while
           maintaining its aspect ratio.
        - The image is centered within the cell based on its scaled dimensions.
        - After the image is drawn, the temporary file specified by `temp_image_path` is removed.

    Raises:
        FileNotFoundError: If `image_path` does not exist.
        IOError: If an error occurs while processing or drawing the image.
    """
    logger.debug(
        "Drawing ticket on PDF canvas: %s at position %s with cell dimensions %s",
        image_path,
        position,
        cell_dimensions,
    )

    if not os.path.exists(image_path):
        logger.critical("Image file not found: %s", image_path)
        raise FileNotFoundError(f"Image file not found: {image_path}")

    try:
        scaled_width, scaled_height = process_image(image_path, cell_dimensions, temp_image_path)
        logger.debug("Processed image size: width=%.2f, height=%.2f", scaled_width, scaled_height)

        x, y = position
        x_centered = x + (cell_dimensions[0] - scaled_width) / 2
        y_centered = y + (cell_dimensions[1] - scaled_height) / 2

        c.drawImage(
            temp_image_path,
            x_centered,
            y_centered,
            width=scaled_width,
            height=scaled_height,
            preserveAspectRatio=True,
            anchor="nw",
        )
        logger.info("Ticket image drawn on PDF at (%.2f, %.2f)", x_centered, y_centered)

    except OSError as e:
        logger.critical("Error while processing or drawing image: %s", e)
        raise IOError(f"Failed to process or draw image: {e}") from e

    finally:
        if os.path.exists(temp_image_path):
            try:
                os.remove(temp_image_path)
                logger.debug("Temporary image file deleted: %s", temp_image_path)
            except OSError as e:
                logger.warning("Failed to delete temporary file: %s", e)


def get_cell_position(
    index: int, pdf_properties: Dict[str, Union[float, int, str]]
) -> Tuple[float, float]:
    """
    Calculate the top-left position of a cell in a grid layout.

    Given an index in a grid with specified rows and columns, this function
    calculates the (x, y) coordinates of the cell's top-left corner. The grid
    is laid out within a defined page size, with cells having specific dimensions
    and borders.

    Parameters:
        index (int): The zero-based index of the cell in the grid.
        pdf_properties (dict): A dictionary containing the following keys:
            - "rows" (int): The total number of rows in the grid.
            - "cols" (int): The total number of columns in the grid.
            - "cell_width" (float): The width of each cell.
            - "cell_height" (float): The height of each cell.
            - "border" (float): The size of the border around the grid.
            - "page_height" (float): The total height of the page.

    Returns:
        Tuple[float, float]: A tuple (x, y) representing the top-left coordinates of the cell.

    Raises:
        TypeError: If `index` is not an integer or `pdf_properties` contains invalid types.
        KeyError: If a required key is missing in `pdf_properties`.
        ValueError: If `index` is negative or if grid dimensions are invalid.
    """
    logger.debug(
        "Calculating cell position for index: %d with PDF properties: %s",
        index,
        pdf_properties,
    )

    required_keys = [
        "rows",
        "cols",
        "cell_width",
        "cell_height",
        "border",
        "page_height",
    ]

    for key in required_keys:
        if key not in pdf_properties:
            logger.critical("Missing key in pdf_properties: %s", key)
            raise KeyError(f"Missing key in pdf_properties: {key}")
        if not isinstance(pdf_properties[key], (int, float)):
            logger.critical(
                "Invalid type for key '%s': expected int or float, got %s",
                key,
                type(pdf_properties[key]),
            )
            raise TypeError(
                f"Invalid type for '{key}': expected int or float, got {type(pdf_properties[key])}."
            )

    rows = int(pdf_properties["rows"])
    cols = int(pdf_properties["cols"])
    cell_width = float(pdf_properties["cell_width"])
    cell_height = float(pdf_properties["cell_height"])
    border = float(pdf_properties["border"])
    page_height = float(pdf_properties["page_height"])

    if index < 0:
        logger.critical("Invalid index: %d. Must be non-negative.", index)
        raise ValueError("index must be a non-negative integer.")

    if rows <= 0 or cols <= 0:
        logger.critical(
            "Invalid grid dimensions: rows=%d, cols=%d. Must be greater than 0.",
            rows,
            cols,
        )
        raise ValueError("Grid dimensions must be greater than 0.")

    row = (index // cols) % rows
    col = index % cols

    x = border + col * cell_width
    y = page_height - border - (row + 1) * cell_height

    logger.info("Cell position calculated: index=%d -> (x=%.2f, y=%.2f)", index, x, y)
    return x, y


def create_ticket_pdf(ticket_codes: List[str], pdf_path: str) -> str:
    """
    Generates a PDF containing ticket images and saves it to the specified path.

    This function processes a collection of ticket codes, retrieves corresponding ticket images,
    and arranges them in a grid layout within a PDF document. Each page can hold a specific number
    of tickets based on the configured grid dimensions (rows and columns). If the number of tickets
    exceeds the capacity of one page, additional pages are automatically added.

    Args:
        ticket_codes (List[str]): A list containing ticket codes. Each code should correspond
                                   to an image file located at
                                   'instance/data/tickets/<ticket_code>.png'.
        pdf_path (str): The output path for the generated PDF file, including the ".pdf" extension.

    Returns:
        str: The path to the saved PDF file.

    Raises:
        FileNotFoundError: If a ticket image corresponding to a code is not found.
        ValueError: If ticket_codes is empty or contains invalid data.
        IOError: If an error occurs while saving the PDF file.
    """
    logger.info("Starting PDF generation for %d tickets.", len(ticket_codes))

    if not ticket_codes:
        logger.critical("Empty ticket_codes list provided. Cannot generate PDF.")
        raise ValueError("ticket_codes cannot be empty.")

    try:
        pdf_properties = get_pdf_properties()
        logger.debug("Loaded PDF properties: %s", pdf_properties)
    except (FileNotFoundError, KeyError, ValueError) as e:
        logger.critical("Failed to load PDF configuration: %s", e)
        raise

    temp_image_path_template = os.path.join(current_app.config["TMP_PATH"], "temp_image_{}.png")

    try:
        c = canvas.Canvas(
            pdf_path,
            pagesize=(
                cast(float, pdf_properties["page_width"]),
                cast(float, pdf_properties["page_height"]),
            ),
        )
        logger.info("PDF document initialized at %s", pdf_path)

        for i, ticket_code in enumerate(ticket_codes):
            cell_x, cell_y = get_cell_position(i, pdf_properties)

            try:
                draw_ticket_on_canvas(
                    c,
                    os.path.join(current_app.config["TICKET_IMAGE_PATH"], f"{ticket_code}.png"),
                    (
                        float(pdf_properties["cell_width"]),
                        float(pdf_properties["cell_height"]),
                    ),
                    (cell_x, cell_y),
                    temp_image_path_template.format(i),
                )
                logger.debug(
                    "Ticket %s placed at position (%.2f, %.2f)",
                    ticket_code,
                    cell_x,
                    cell_y,
                )

            except FileNotFoundError:
                logger.error(
                    "Ticket image not found for code: %s. Skipping this ticket.",
                    ticket_code,
                )
                continue  # Skips the missing ticket without canceling the whole process

            # Add new page if the grid is full
            if (i + 1) % (
                int(pdf_properties["rows"]) * int(pdf_properties["cols"])
            ) == 0 and i + 1 < len(ticket_codes):
                c.showPage()
                logger.info("New page added to PDF.")

        c.save()
        logger.info("PDF successfully saved at: %s", pdf_path)

    except IOError as e:
        logger.critical("Error while saving PDF: %s", e)
        raise IOError(f"Failed to save PDF: {e}") from e

    return pdf_path

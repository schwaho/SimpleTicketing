"""
This module brings support for sending E-Mail via Flask.
"""

from flask_mail import Mail
from typer import Typer

typer = Typer()

mail = Mail()

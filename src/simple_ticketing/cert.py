"""
This module provides functionality to generate a self-signed Certificate Authority (CA)
and create server certificates signed by this CA. The generated certificates enable a
Flask application to securely communicate over HTTPS with self-signed but trusted certificates.

Features:
- Creates a self-signed CA (`ca.pem`) and a corresponding private key (`ca-key.pem`).
- Generates a server certificate (`cert.pem`) and private key (`key.pem`).
- Signs the server certificate using the CA, ensuring that the Flask application can trust it.
- Saves all generated files inside the `instance/` directory.

"""

import os
import logging
from typing import Tuple
from datetime import datetime, timedelta, timezone
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.exceptions import InvalidSignature

logger = logging.getLogger(__name__)

INSTANCE_DIR = "instance"


def generate_rsa_key() -> rsa.RSAPrivateKey:
    """
    Generates a 2048-bit RSA private key.

    Returns:
        rsa.RSAPrivateKey: Generated RSA key.
    """
    logger.debug("Generating RSA private key...")
    try:
        return rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )
    except OSError as e:
        logger.error("System error while generating RSA key: %s", e)
        raise


def create_ca() -> Tuple[x509.Certificate, rsa.RSAPrivateKey]:
    """
    Generates a self-signed Certificate Authority (CA).

    The CA certificate and private key are saved in the 'instance/' directory.

    Returns:
        tuple: (ca_cert, ca_key)
    """
    logger.info("Creating Certificate Authority (CA)...")
    ca_key_path = os.path.join(INSTANCE_DIR, "ca-key.pem")
    ca_cert_path = os.path.join(INSTANCE_DIR, "ca.pem")

    ca_key = generate_rsa_key()

    try:
        ca_subject = x509.Name(
            [
                x509.NameAttribute(NameOID.COUNTRY_NAME, "DE"),
                x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Rheinhessen"),
                x509.NameAttribute(NameOID.LOCALITY_NAME, "Mainz"),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Simple Ticketing Custom CA"),
                x509.NameAttribute(NameOID.COMMON_NAME, "Simple Ticketing CA"),
            ]
        )

        ca_cert = (
            x509.CertificateBuilder()
            .subject_name(ca_subject)
            .issuer_name(ca_subject)
            .public_key(ca_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.now(timezone.utc))
            .not_valid_after(datetime.now(timezone.utc) + timedelta(days=3650))
            .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
            .sign(ca_key, hashes.SHA256())
        )

        logger.info("CA certificate created successfully.")
        save_key(ca_key_path, ca_key)
        save_certificate(ca_cert_path, ca_cert)
        logger.info(
            "CA certificate and key saved at:\n  - %s\n  - %s",
            ca_cert_path,
            ca_key_path,
        )
        return ca_cert, ca_key
    except InvalidSignature as e:
        logger.error("CA signature invalid: %s", e)
        raise
    except OSError as e:
        logger.error("System error during CA certificate creation: %s", e)
        raise


def create_signed_certificate(ca_cert: x509.Certificate, ca_key: rsa.RSAPrivateKey) -> None:
    """
    Generates a server certificate signed by the CA.

    Args:
        ca_cert (x509.Certificate): The CA certificate.
        ca_key (rsa.RSAPrivateKey): The CA private key.
    """
    logger.info("Creating server certificate signed by CA...")
    server_key_path = os.path.join(INSTANCE_DIR, "key.pem")
    server_cert_path = os.path.join(INSTANCE_DIR, "cert.pem")

    server_key = generate_rsa_key()

    try:
        server_subject = x509.Name(
            [
                x509.NameAttribute(NameOID.COUNTRY_NAME, "DE"),
                x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Rheinhessen"),
                x509.NameAttribute(NameOID.LOCALITY_NAME, "Mainz"),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Simple Ticketing SSL Server"),
                x509.NameAttribute(NameOID.COMMON_NAME, "localhost"),
            ]
        )
        logger.debug("Building server certificate...")
        server_cert = (
            x509.CertificateBuilder()
            .subject_name(server_subject)
            .issuer_name(ca_cert.subject)
            .public_key(server_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.now(timezone.utc))
            .not_valid_after(datetime.now(timezone.utc) + timedelta(days=365))
            .add_extension(x509.SubjectAlternativeName([x509.DNSName("localhost")]), critical=False)
            .sign(ca_key, hashes.SHA256())
        )

        logger.info("Server certificate created successfully.")
        save_key(server_key_path, server_key)
        save_certificate(server_cert_path, server_cert)
        logger.info(
            "Server certificate and key saved at:\n  - %s\n  - %s",
            server_cert_path,
            server_key_path,
        )
    except InvalidSignature as e:
        logger.error("Server certificate signature invalid: %s", e)
        raise
    except OSError as e:
        logger.error("System error during server certificate creation: %s", e)
        raise


def save_key(file_path: str, key: rsa.RSAPrivateKey) -> None:
    """
    Saves an RSA private key to a file.

    Args:
        file_path (str): The path to save the key.
        key (rsa.RSAPrivateKey): The RSA key to save.
    """
    try:
        with open(file_path, "wb") as f:
            f.write(
                key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.TraditionalOpenSSL,
                    encryption_algorithm=serialization.NoEncryption(),
                )
            )
        logger.debug("Private key saved successfully: %s", file_path)
    except PermissionError as e:
        logger.error("Permission denied while saving private key %s: %s", file_path, e)
        raise
    except OSError as e:
        logger.error("OS error while saving private key %s: %s", file_path, e)
        raise


def save_certificate(file_path: str, cert: x509.Certificate) -> None:
    """
    Saves an X.509 certificate to a file.

    Args:
        file_path (str): The path to save the certificate.
        cert (x509.Certificate): The certificate to save.
    """
    try:
        with open(file_path, "wb") as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))
        logger.debug("Certificate saved successfully: %s", file_path)
    except PermissionError as e:
        logger.error("Permission denied while saving certificate %s: %s", file_path, e)
        raise
    except OSError as e:
        logger.error("OS error while saving certificate %s: %s", file_path, e)
        raise


if __name__ == "__main__":
    logger.info("Starting certificate generation process...")
    try:
        os.makedirs(INSTANCE_DIR, exist_ok=True)
        logger.debug("Created or verified existence of directory: %s", INSTANCE_DIR)
    except PermissionError as e:
        logger.critical("Permission denied while creating directory %s: %s", INSTANCE_DIR, e)
        raise
    except OSError as e:
        logger.error("OS error when creating directory %s: %s", INSTANCE_DIR, e)
        raise

    try:
        new_ca_cert, new_ca_key = create_ca()
        create_signed_certificate(new_ca_cert, new_ca_key)
        logger.info("Certificate generation process completed successfully.")
    except OSError as e:
        logger.critical("Fatal system error during certificate generation: %s", e)
        raise
    except InvalidSignature as e:
        logger.critical("Invalid cryptographic signature detected: %s", e)
        raise

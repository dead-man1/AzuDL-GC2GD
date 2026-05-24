"""
AzuDL Security & Privacy Module
Provides file encryption, checksum verification, and security utilities.

Features:
- AES-128-CBC encryption (Fernet)
- PBKDF2 key derivation (100k iterations)
- Multiple hash algorithms (SHA256, SHA512, BLAKE2b)
- Path traversal prevention
- Sensitive data masking
- Download manifests
"""

import os
import hashlib
import secrets
import base64
from pathlib import Path
from datetime import datetime
from tqdm.notebook import tqdm
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
from cryptography.hazmat.backends import default_backend


class AzuDlSecurity:
    """Security and encryption utilities for AzuDL."""

    # Top 3 Free IP Blocklists for Security & Privacy
    DEFAULT_BLOCKLISTS = {
        "level1": {
            "name": "bluetack_level1",
            "url": "http://list.iblocklist.com/lists/bluetack/level1.gz",
            "description": "General blocklist covering spyware, adware, and ISP throttling"
        },
        "level2": {
            "name": "bluetack_level2",
            "url": "http://list.iblocklist.com/lists/bluetack/level2.gz",
            "description": "Extended blocklist with more aggressive blocking"
        },
        "badpeers": {
            "name": "iblocklist_badpeers",
            "url": "http://list.iblocklist.com/lists/iblocklist/badpeers.gz",
            "description": "Blocks malicious peers and privacy-invasive trackers"
        }
    }

    def __init__(self):
        self.backend = default_backend()

    @staticmethod
    def derive_key(password: str, salt: bytes = None, iterations: int = 100000) -> tuple:
        """
        Derive encryption key from password using PBKDF2.
        OWASP compliant: 100,000 iterations minimum for modern systems.
        Returns (key, salt) tuple.
        """
        if salt is None:
            salt = os.urandom(32)  # 256-bit salt

        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=iterations,
            backend=default_backend()
        )

        key = base64.urlsafe_b64encode(kdf.derive(password.encode('utf-8')))
        return key, salt

    @staticmethod
    def encrypt_file(source_path: Path, output_path: Path = None, password: str = None) -> tuple:
        """
        Encrypt a file using Fernet (AES-128-CBC).
        Returns (encrypted_path, password) tuple.
        
        File format:
        [Iterations (4 bytes)] [Salt (32 bytes)] [Fernet Ciphertext]
        """
        source_path = Path(source_path)

        if not source_path.exists():
            raise FileNotFoundError(f"Source file not found: {source_path}")

        # Generate password if not provided
        if password is None:
            password = secrets.token_urlsafe(32)

        # Derive encryption key
        key, salt = AzuDlSecurity.derive_key(password)
        cipher = Fernet(key)

        # Set output path
        if output_path is None:
            output_path = source_path.with_suffix(source_path.suffix + ".encrypted")

        # Read and encrypt file
        source_size = source_path.stat().st_size

        with source_path.open("rb") as src:
            plaintext = src.read()

        ciphertext = cipher.encrypt(plaintext)

        # Write: [iterations (4 bytes)] [salt (32 bytes)] [ciphertext]
        with output_path.open("wb") as dst:
            dst.write((100000).to_bytes(4, byteorder='big'))
            dst.write(salt)
            dst.write(ciphertext)

        return output_path, password

    @staticmethod
    def decrypt_file(encrypted_path: Path, output_path: Path = None, password: str = None) -> Path:
        """
        Decrypt a file encrypted with encrypt_file().
        """
        encrypted_path = Path(encrypted_path)

        if not encrypted_path.exists():
            raise FileNotFoundError(f"Encrypted file not found: {encrypted_path}")

        if password is None:
            raise ValueError("Password is required for decryption")

        # Read encrypted data
        with encrypted_path.open("rb") as f:
            iterations = int.from_bytes(f.read(4), byteorder='big')
            salt = f.read(32)
            ciphertext = f.read()

        # Derive key
        key, _ = AzuDlSecurity.derive_key(password, salt, iterations)
        cipher = Fernet(key)

        # Decrypt
        try:
            plaintext = cipher.decrypt(ciphertext)
        except InvalidToken:
            raise ValueError("Decryption failed. Password may be incorrect or file is corrupted.")

        # Set output path
        if output_path is None:
            suffix_list = encrypted_path.suffixes
            if suffix_list and suffix_list[-1] == ".encrypted":
                output_path = encrypted_path.with_suffix('')
            else:
                output_path = encrypted_path.with_suffix(encrypted_path.suffix + ".decrypted")

        # Write decrypted file
        with output_path.open("wb") as dst:
            dst.write(plaintext)

        return output_path

    @staticmethod
    def hash_file(file_path: Path, algorithm: str = "sha256") -> str:
        """
        Calculate file hash using specified algorithm.
        Supports: sha256, sha512, blake2b
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(file_path)

        if not file_path.is_file():
            raise ValueError("Path is not a file")

        # Initialize hash object
        if algorithm == "sha256":
            hasher = hashlib.sha256()
        elif algorithm == "sha512":
            hasher = hashlib.sha512()
        elif algorithm == "blake2b":
            hasher = hashlib.blake2b()
        else:
            raise ValueError(f"Unsupported hash algorithm: {algorithm}")

        file_size = file_path.stat().st_size

        with file_path.open("rb") as f:
            with tqdm(total=file_size, unit="B", unit_scale=True, unit_divisor=1024,
                     desc=f"{algorithm.upper()}") as bar:
                while True:
                    chunk = f.read(8192)
                    if not chunk:
                        break
                    hasher.update(chunk)
                    bar.update(len(chunk))

        return hasher.hexdigest()

    @staticmethod
    def verify_checksum(file_path: Path, expected_hash: str, algorithm: str = "sha256") -> bool:
        """
        Verify file checksum against expected hash.
        Raises ValueError if verification fails.
        """
        computed_hash = AzuDlSecurity.hash_file(file_path, algorithm)

        if computed_hash.lower() != expected_hash.lower():
            raise ValueError(
                f"Checksum verification failed!\n"
                f"Expected: {expected_hash}\n"
                f"Got:      {computed_hash}"
            )

        return True

    @staticmethod
    def sanitize_path(path_input: str, base_dir: Path = None) -> Path:
        """
        Securely sanitize and validate file paths to prevent directory traversal attacks.
        Prevents: ../../../etc/passwd, absolute paths, null bytes
        """
        path_input = str(path_input).strip()

        # Reject null bytes
        if '\x00' in path_input:
            raise ValueError("Invalid characters in path")

        # Reject absolute paths if base_dir is provided
        if base_dir and Path(path_input).is_absolute():
            raise ValueError("Absolute paths are not allowed")

        sanitized = Path(path_input).resolve()

        # Ensure path is within base_dir if provided
        if base_dir:
            base_dir = Path(base_dir).resolve()
            try:
                sanitized.relative_to(base_dir)
            except ValueError:
                raise ValueError(f"Path escapes base directory: {sanitized}")

        return sanitized

    @staticmethod
    def mask_sensitive_url(url: str, show_chars: int = 10) -> str:
        """
        Mask sensitive parts of URLs for logging (tokens, passwords).
        """
        if "://" in url:
            scheme, rest = url.split("://", 1)
            if "/" in rest:
                host, path = rest.split("/", 1)
            else:
                host = rest
                path = ""

            # Mask credentials in host
            if "@" in host:
                credentials, host_part = host.rsplit("@", 1)
                masked_creds = "***" if credentials else ""
                masked_host = f"{masked_creds}@{host_part}"
            else:
                masked_host = host

            return f"{scheme}://{masked_host}/{path[:show_chars]}..." if path else f"{scheme}://{masked_host}"

        return url[:show_chars] + "..." if len(url) > show_chars else url

    @staticmethod
    def get_blocklist_config(blocklist_type: str = "all") -> dict:
        """
        Get IP blocklist configuration.
        Types: 'level1', 'level2', 'badpeers', 'all'
        """
        if blocklist_type == "all":
            return AzuDlSecurity.DEFAULT_BLOCKLISTS
        elif blocklist_type in AzuDlSecurity.DEFAULT_BLOCKLISTS:
            return {blocklist_type: AzuDlSecurity.DEFAULT_BLOCKLISTS[blocklist_type]}
        else:
            raise ValueError(f"Unknown blocklist type: {blocklist_type}")

    @staticmethod
    def create_secure_download_manifest(file_path: Path, metadata: dict = None) -> dict:
        """
        Create a secure manifest file for downloaded content.
        Includes: hash, timestamp, source, size, encryption status.
        """
        file_path = Path(file_path)

        manifest = {
            "file": str(file_path.name),
            "timestamp": datetime.now().isoformat(),
            "size": file_path.stat().st_size,
            "sha256": AzuDlSecurity.hash_file(file_path, "sha256"),
            "blake2b": AzuDlSecurity.hash_file(file_path, "blake2b")
        }

        if metadata:
            manifest.update(metadata)

        return manifest

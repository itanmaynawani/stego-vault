"""Core steganography: AES-GCM encrypted text hidden in pixel LSBs.

Layout inside the image's RGB byte stream (one bit per byte, LSB):
  [0 .. 255]     header: salt(16) + nonce(12) + ciphertext length(4)  (sequential)
  [256 .. end]   ciphertext bits, scattered across the image in an order
                 derived from the key, so without the key even the *location*
                 of the data is unknown.
"""
import io
import os
import struct

import numpy as np
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from PIL import Image

Image.MAX_IMAGE_PIXELS = 20_000_000  # reject decompression bombs

HEADER_BYTES = 16 + 12 + 4
HEADER_BITS = HEADER_BYTES * 8


class StegoError(Exception):
    pass


def _derive_key(password: str, salt: bytes) -> bytes:
    return Scrypt(salt=salt, length=32, n=2**14, r=8, p=1).derive(password.encode())


def _load(data: bytes) -> np.ndarray:
    try:
        img = Image.open(io.BytesIO(data)).convert("RGB")
    except Exception:
        raise StegoError("That file isn't a readable image.")
    return np.array(img, dtype=np.uint8)


def _scatter_order(key: bytes, total: int) -> np.ndarray:
    seed = np.frombuffer(key[:16], dtype=np.uint32)
    rng = np.random.default_rng(seed)
    return HEADER_BITS + rng.permutation(total - HEADER_BITS)


def capacity_bytes(image_bytes: bytes) -> int:
    arr = _load(image_bytes)
    return max(0, (arr.size - HEADER_BITS) // 8 - 16)  # minus GCM tag


def encode(image_bytes: bytes, message: str, password: str) -> bytes:
    if not password:
        raise StegoError("A key is required.")
    arr = _load(image_bytes)
    flat = arr.reshape(-1)

    salt, nonce = os.urandom(16), os.urandom(12)
    key = _derive_key(password, salt)
    ciphertext = AESGCM(key).encrypt(nonce, message.encode("utf-8"), None)

    if HEADER_BITS + len(ciphertext) * 8 > flat.size:
        raise StegoError("Message is too long for this image. Use a larger image or shorter text.")

    header = salt + nonce + struct.pack(">I", len(ciphertext))
    flat[:HEADER_BITS] = (flat[:HEADER_BITS] & 0xFE) | np.unpackbits(np.frombuffer(header, np.uint8))

    bits = np.unpackbits(np.frombuffer(ciphertext, np.uint8))
    idx = _scatter_order(key, flat.size)[: len(bits)]
    flat[idx] = (flat[idx] & 0xFE) | bits

    out = io.BytesIO()
    Image.fromarray(arr).save(out, format="PNG")  # lossless, or the bits would be destroyed
    return out.getvalue()


def decode(image_bytes: bytes, password: str) -> str:
    fail = StegoError("Nothing came out. Wrong key, or this image holds no message.")
    arr = _load(image_bytes)
    flat = arr.reshape(-1)
    if flat.size <= HEADER_BITS:
        raise fail

    header = np.packbits(flat[:HEADER_BITS] & 1).tobytes()
    salt, nonce = header[:16], header[16:28]
    (length,) = struct.unpack(">I", header[28:32])
    if length < 16 or HEADER_BITS + length * 8 > flat.size:
        raise fail

    key = _derive_key(password, salt)
    idx = _scatter_order(key, flat.size)[: length * 8]
    ciphertext = np.packbits(flat[idx] & 1).tobytes()
    try:
        return AESGCM(key).decrypt(nonce, ciphertext, None).decode("utf-8")
    except (InvalidTag, UnicodeDecodeError):
        raise fail

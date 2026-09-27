import hashlib
import io
import os
import uuid
from pathlib import Path

from fastapi import HTTPException
from PIL import Image, UnidentifiedImageError

Image.MAX_IMAGE_PIXELS = 20_000_000


class LocalStorage:
    def __init__(self):
        self.root = Path(os.getenv("UPLOAD_DIR", "data/evidence"))
        self.root.mkdir(parents=True, exist_ok=True)

    def save(self, content):
        key = f"{uuid.uuid4().hex}.jpg"
        (self.root / key).write_bytes(content)
        return key

    def path(self, key):
        return self.root / key


def clean_image(raw, filename, content_type):
    if len(raw) > 5 * 1024 * 1024:
        raise HTTPException(413, "Maximum image size is 5 MB.")
    if Path(filename or "").suffix.lower() not in {
        ".jpg",
        ".jpeg",
        ".png",
        ".webp",
    } or content_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise HTTPException(422, "Use a JPEG, PNG or WebP image.")
    try:
        with Image.open(io.BytesIO(raw)) as im:
            if im.width * im.height > Image.MAX_IMAGE_PIXELS:
                raise ValueError("Image dimensions exceed the pixel limit")
            if im.format not in {"JPEG", "PNG", "WEBP"}:
                raise ValueError("Unsupported image")
            im.load()
            im.thumbnail((2000, 2000))
            result = io.BytesIO()
            im.convert("RGB").save(result, format="JPEG", quality=88)
            content = result.getvalue()
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
        raise HTTPException(422, "The file is not a safe decodable image.")
    return content, hashlib.sha256(content).hexdigest()

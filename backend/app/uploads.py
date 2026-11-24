from pathlib import Path


UPLOADS_DIR = Path(__file__).resolve().parents[1] / "uploads"
PRODUCT_IMAGES_DIR = UPLOADS_DIR / "products"
PROFILE_IMAGES_DIR = UPLOADS_DIR / "profiles"
MAX_IMAGE_SIZE_BYTES = 5 * 1024 * 1024


def image_extension(data: bytes) -> str | None:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if data.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    return None

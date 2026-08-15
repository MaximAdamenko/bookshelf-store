import re
import uuid
from io import BytesIO
from pathlib import Path
from typing import BinaryIO, Protocol

from PIL import Image, UnidentifiedImageError

_CHUNK = 64 * 1024

# extension -> the format Pillow must sniff for it. Both must agree. (SECURITY.md 4.3)
_FORMATS = {"jpg": "JPEG", "jpeg": "JPEG", "png": "PNG", "webp": "WEBP"}
_CANONICAL_EXT = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}

_FILENAME_RE = re.compile(r"[0-9a-f]{32}\.(jpg|png|webp)")


class UploadRejected(ValueError):
    """Bad image upload. Router maps to 413/422."""

    def __init__(self, reason: str, *, too_large: bool = False):
        self.too_large = too_large
        super().__init__(reason)


class Storage(Protocol):
    def save(self, data: bytes, ext: str) -> str: ...
    def delete(self, filename: str) -> None: ...
    def resolve(self, filename: str) -> Path | None: ...


class LocalDiskStorage:
    def __init__(self, root: Path):
        self.root = root
        root.mkdir(parents=True, exist_ok=True)

    def save(self, data: bytes, ext: str) -> str:
        # Server-generated name, client filename never consulted. (SECURITY.md 4.4)
        filename = f"{uuid.uuid4().hex}.{ext}"
        path = self.root / filename
        path.write_bytes(data)
        path.chmod(0o644)
        return filename

    def resolve(self, filename: str) -> Path | None:
        if not _FILENAME_RE.fullmatch(filename):
            return None
        path = (self.root / filename).resolve()
        if not path.is_relative_to(self.root.resolve()) or not path.is_file():
            return None
        return path

    def delete(self, filename: str) -> None:
        path = self.resolve(filename)
        if path is not None:
            path.unlink(missing_ok=True)


def process_cover(
    file: BinaryIO, client_filename: str, *, max_bytes: int, max_pixels: int
) -> tuple[bytes, str]:
    ext = (client_filename.rsplit(".", 1)[-1] if "." in client_filename else "").lower()
    if ext not in _FORMATS:
        raise UploadRejected("only .jpg, .jpeg, .png, .webp are accepted")

    # Cap enforced while streaming, aborting mid-read. (SECURITY.md 4.2)
    buf = BytesIO()
    while chunk := file.read(_CHUNK):
        if buf.tell() + len(chunk) > max_bytes:
            raise UploadRejected("file too large", too_large=True)
        buf.write(chunk)
    if buf.tell() == 0:
        raise UploadRejected("empty file")

    Image.MAX_IMAGE_PIXELS = max_pixels  # bombs raise DecompressionBombError (4.6)
    buf.seek(0)
    try:
        with Image.open(buf) as img:
            if img.format != _FORMATS[ext]:
                raise UploadRejected("file content does not match its extension")
            fmt = img.format
            # Re-encode: EXIF, appended payloads and polyglots do not survive. (4.5)
            out = BytesIO()
            if fmt == "JPEG" and img.mode not in ("RGB", "L"):
                img = img.convert("RGB")
            img.save(out, format=fmt)
    except UploadRejected:
        raise
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError):
        raise UploadRejected("not a valid image")

    return out.getvalue(), _CANONICAL_EXT[fmt]

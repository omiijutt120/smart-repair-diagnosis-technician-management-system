from io import BytesIO
from pathlib import Path
from uuid import uuid4

from flask import current_app
from PIL import Image, UnidentifiedImageError
from werkzeug.utils import secure_filename

from smart_repair.models import RepairAttachment
from .workflow import BusinessError


def validate_upload(storage):
    original = secure_filename(storage.filename or "")
    extension = Path(original).suffix.lower()
    data = storage.read(current_app.config["MAX_CONTENT_LENGTH"] + 1)
    if not data or len(data) > current_app.config["MAX_CONTENT_LENGTH"]:
        raise BusinessError("Upload is empty or exceeds the configured file size limit.")
    if extension == ".pdf":
        if not data.startswith(b"%PDF-") or storage.mimetype != "application/pdf":
            raise BusinessError("The file must be a valid PDF document.")
        mime = "application/pdf"
    elif extension in {".jpg", ".jpeg", ".png", ".webp"}:
        try:
            with Image.open(BytesIO(data)) as image:
                image.verify()
                mime = Image.MIME.get(image.format)
        except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
            raise BusinessError("The file must be a valid JPG, PNG or WebP image.")
        expected = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}[extension]
        if mime != expected or storage.mimetype != expected:
            raise BusinessError("The image type does not match its extension or MIME type.")
    else:
        raise BusinessError("Only JPG, PNG, WebP and PDF files are allowed.")
    return original, extension, mime, data


def store_upload(validated, request_id, user_id):
    original, extension, mime, data = validated
    filename = f"{uuid4().hex}{extension}"
    path = Path(current_app.config["UPLOAD_FOLDER"]) / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return RepairAttachment(repair_request_id=request_id, uploaded_by_user_id=user_id,
        file_name=original, file_path=filename, mime_type=mime, file_size=len(data))

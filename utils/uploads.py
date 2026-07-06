"""
Grabbite — utils/uploads.py
Shared file-upload helpers used by both auth_routes.py and blueprints/admin/__init__.py.

Consolidates the duplicate helper blocks that previously lived in both files.
H11 fix: validates magic bytes so a renamed non-image file is rejected even if
the extension looks valid.
"""
import os
import uuid

from flask import current_app
from werkzeug.utils import secure_filename

# Pillow is optional — only used for image resizing
try:
    from PIL import Image as PILImage
    _PIL_AVAILABLE = True
except ImportError:
    _PIL_AVAILABLE = False

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

# H11: known magic-byte signatures for accepted image types
_IMAGE_MAGIC = (
    b'\xff\xd8\xff',                       # JPEG
    b'\x89PNG\r\n\x1a\n',                  # PNG
    b'GIF87a', b'GIF89a',                   # GIF
    b'RIFF',                                # WEBP (RIFF....WEBP)
)


def allowed_file(filename: str) -> bool:
    """Return True if *filename* has an allowed image extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def _looks_like_image(file_storage) -> bool:
    """Read the leading bytes of an upload and verify against known image magic signatures."""
    try:
        head = file_storage.stream.read(12)
    except Exception:
        return False
    finally:
        try:
            file_storage.stream.seek(0)
        except Exception:
            pass  # non-fatal; already read 0 bytes
    if not head:
        return False
    for sig in _IMAGE_MAGIC:
        if head.startswith(sig):
            # For WEBP we also want the WEBP marker in the first 12 bytes.
            if sig == b'RIFF' and b'WEBP' not in head[:12]:
                continue
            return True
    return False


def resize_image(image_path: str, max_size: tuple = (800, 800)) -> None:
    """Resize image to max_size while maintaining aspect ratio. Skips if PIL unavailable."""
    if not _PIL_AVAILABLE:
        return
    try:
        with PILImage.open(image_path) as img:
            img.thumbnail(max_size, PILImage.Resampling.LANCZOS)
            img.save(image_path, optimize=True, quality=85)
    except Exception as e:
        current_app.logger.warning(f'Image resize failed: {e}')


def save_upload(file, subfolder: str = '') -> str | None:
    """Save an uploaded profile/auth image to the uploads directory and return filename.

    Returns the relative filename (including subfolder if given), or None on failure.
    Performs extension check + magic-byte sniff before persisting to disk.
    """
    if not file or file.filename == '':
        return None
    if not allowed_file(file.filename):
        return None
    # H11 fix: extension check passed — verify the file content is really an image.
    if not _looks_like_image(file):
        current_app.logger.warning(
            f'Upload rejected: extension says image but content is not. '
            f'filename={file.filename!r}'
        )
        return None

    filename    = secure_filename(file.filename)
    unique_name = f'{uuid.uuid4().hex}_{filename}'
    upload_dir  = current_app.config['UPLOAD_FOLDER']
    if subfolder:
        upload_dir = os.path.join(upload_dir, subfolder)
        os.makedirs(upload_dir, exist_ok=True)

    file_path = os.path.join(upload_dir, unique_name)
    file.save(file_path)
    resize_image(file_path)
    return os.path.join(subfolder, unique_name) if subfolder else unique_name


def save_image(file, old_image=None) -> tuple:
    """Admin-style image save: returns (filename, error_msg).

    On success error_msg is None. Optionally removes the old image file.
    Does NOT resize — admin images are stored at original quality.
    """
    if not file or file.filename == '':
        return None, 'No file selected'
    if not allowed_file(file.filename):
        return None, 'Invalid file type. Allowed: PNG, JPG, JPEG, GIF, WEBP'
    if not _looks_like_image(file):
        return None, 'File content does not match an allowed image format.'
    try:
        ext         = file.filename.rsplit('.', 1)[1].lower()
        unique_name = f'{uuid.uuid4().hex}.{ext}'
        filepath    = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_name)
        file.save(filepath)

        if old_image and not old_image.endswith('_default.jpg') and \
                old_image not in ('default.jpg', 'blog_default.jpg',
                                  'restaurant_default.jpg', 'food_default.jpg'):
            old_path = os.path.join(current_app.config['UPLOAD_FOLDER'], old_image)
            if os.path.exists(old_path):
                try:
                    os.remove(old_path)
                except OSError:
                    pass

        return unique_name, None
    except Exception as e:
        return None, str(e)

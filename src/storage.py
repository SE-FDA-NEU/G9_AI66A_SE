"""Photo storage abstraction.

Local development keeps uploaded venue photos on disk under `UPLOAD_DIR`.
On Vercel, set `CLOUDINARY_URL` (or `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`,
`CLOUDINARY_API_SECRET`) to persist photos in Cloudinary instead.
"""
import os
import uuid
from pathlib import Path


def _cloudinary_configured():
    return bool(os.environ.get("CLOUDINARY_URL") or (
        os.environ.get("CLOUDINARY_CLOUD_NAME")
        and os.environ.get("CLOUDINARY_API_KEY")
        and os.environ.get("CLOUDINARY_API_SECRET")
    ))


def using_cloudinary():
    """Expose the storage backend choice so routes can serve photos correctly."""
    return _cloudinary_configured()


def save_photo(upload_dir, photo, venue_id):
    """Persist an uploaded photo and return the identifier stored in the database.

    The identifier is either a local filename or a Cloudinary public_id.
    """
    extension = "." + photo.filename.rsplit(".", 1)[-1].lower()
    if _cloudinary_configured():
        return _save_to_cloudinary(photo, venue_id, extension)
    return _save_to_disk(upload_dir, photo, venue_id, extension)


def _save_to_disk(upload_dir, photo, venue_id, extension):
    upload_dir = Path(upload_dir)
    file_name = f"venue{venue_id}-{uuid.uuid4().hex}{extension}"
    upload_dir.mkdir(parents=True, exist_ok=True)
    photo.save(upload_dir / file_name)
    return file_name


def _save_to_cloudinary(photo, venue_id, extension):
    import cloudinary
    import cloudinary.uploader

    if os.environ.get("CLOUDINARY_URL"):
        cloudinary.config_from_url(os.environ["CLOUDINARY_URL"])
    else:
        cloudinary.config(
            cloud_name=os.environ.get("CLOUDINARY_CLOUD_NAME"),
            api_key=os.environ.get("CLOUDINARY_API_KEY"),
            api_secret=os.environ.get("CLOUDINARY_API_SECRET"),
        )

    public_id = f"sports-venue/venue{venue_id}-{uuid.uuid4().hex}"
    result = cloudinary.uploader.upload(photo, public_id=public_id)
    # Store the Cloudinary public_id so the image URL can be reconstructed at serve time.
    return result.get("public_id", public_id)


def photo_url(file_name):
    """Return a public URL for a stored photo identifier."""
    if not file_name:
        return None
    if _cloudinary_configured():
        import cloudinary
        return cloudinary.CloudinaryImage(file_name).build_url()
    return f"/venues/photos/{file_name}"

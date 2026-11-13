"""OWNER: Member 1 (Stanley). Image storage on Cloudinary.

The frontend first sends the file to POST /api/uploads/image and gets back a link.
It then saves that link in the normal JSON requests (`image_url` for properties, `photo_urls` for maintenance).
"""
from flask import current_app

ALLOWED_TYPES = ("image/jpeg", "image/png", "image/webp")
ALLOWED_FORMATS = ["jpg", "jpeg", "png", "webp"]
MAX_BYTES = 2 * 1024 * 1024  # 2 MB


def cloudinary_ready():
    """True when the three Cloudinary settings are filled in."""
    config = current_app.config
    return all(config.get(key) for key in ("CLOUDINARY_CLOUD_NAME", "CLOUDINARY_API_KEY", "CLOUDINARY_API_SECRET"))


def upload_image(file, folder):
    """Check the file, send it to Cloudinary and return {"url", "public_id"}.
    Raises ValueError with a message that is safe to show the user."""
    import cloudinary  # imported here so the app still starts if the package is not installed yet
    import cloudinary.uploader

    if file.mimetype not in ALLOWED_TYPES:
        raise ValueError("Only JPG, PNG or WebP images are allowed.")

    file.stream.seek(0, 2)
    size = file.stream.tell()
    file.stream.seek(0)
    if size > MAX_BYTES:
        raise ValueError("The image must be 2 MB or smaller.")

    config = current_app.config
    cloudinary.config(
        cloud_name=config["CLOUDINARY_CLOUD_NAME"],
        api_key=config["CLOUDINARY_API_KEY"],
        api_secret=config["CLOUDINARY_API_SECRET"],
        secure=True,
    )
    result = cloudinary.uploader.upload(
        file.stream,
        folder=f"rentconnect/{folder}",
        resource_type="image",
        allowed_formats=ALLOWED_FORMATS,  # Cloudinary checks the real file type, not just the name
        transformation=[{"width": 1600, "height": 1600, "crop": "limit"}],  # keep stored images a sensible size
    )
    return {"url": result["secure_url"], "public_id": result["public_id"]}


def is_valid_image_url(url):
    """Accept only links that point to our own Cloudinary account, so nobody can save random links.
    While Cloudinary is not set up (development), any https link is accepted."""
    if not isinstance(url, str) or not url.startswith("https://"):
        return False
    if cloudinary_ready():
        return url.startswith(f"https://res.cloudinary.com/{current_app.config['CLOUDINARY_CLOUD_NAME']}/")
    return True

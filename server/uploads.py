import cloudinary
import cloudinary.uploader
from flask import current_app


def upload_image(file):
    """
    Uploads an image to Cloudinary and returns the secure URL.
    """
    cloudinary.config(
        cloud_name=current_app.config.get("CLOUDINARY_CLOUD_NAME"),
        api_key=current_app.config.get("CLOUDINARY_API_KEY"),
        api_secret=current_app.config.get("CLOUDINARY_API_SECRET"),
        secure=True,
    )

    try:
        result = cloudinary.uploader.upload(file)
        return result.get("secure_url")
    except Exception as e:
        print(f"❌ Error uploading to Cloudinary: {e}")
        return None


def is_valid_image_url(url):
    """
    Checks if the provided string is a valid URL (specifically from Cloudinary).
    """
    if not url:
        return False

    # Basic check to ensure it's a URL string
    if not isinstance(url, str):
        return False

    # Usually, we just want to make sure it's a secure https link
    return url.startswith("http://") or url.startswith("https://")

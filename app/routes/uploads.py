"""OWNER: Member 1 (Stanley). Upload an image to Cloudinary and get its link back."""
from flask import Blueprint, current_app, jsonify, request

from ..uploads import cloudinary_ready, upload_image
from ..utils import current_user, error, roles_required

bp = Blueprint("uploads", __name__)
URL_PREFIX = "/api/uploads"

# Landlords upload property images, tenants upload maintenance photos.
FOLDERS = {"landlord": "properties", "tenant": "maintenance"}


@bp.post("/image")
@roles_required("landlord", "tenant")
def upload():
    """Send the file as multipart form data in a field called `file`."""
    file = request.files.get("file")
    if file is None or not file.filename:
        return error("Choose an image to upload.", 400, fields={"file": "Choose an image to upload."})
    if not cloudinary_ready():
        return error("Image uploads are not set up on this server yet.", 503)

    try:
        result = upload_image(file, FOLDERS[current_user().role])
    except ValueError as problem:
        return error(str(problem), 400, fields={"file": str(problem)})
    except Exception:  # Cloudinary or network problem
        current_app.logger.exception("Cloudinary upload failed")
        return error("The image could not be uploaded. Try again.", 502)

    return jsonify(result), 201

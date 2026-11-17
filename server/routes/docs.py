"""
Open  http://localhost:5555/api/docs  in the browser.
The documentation itself is the file docs/openapi.yaml (at the repo root).
The page loads Swagger UI from a CDN, so it needs an internet connection.

Register it in create_app():
    from server.routes.docs import bp as docs_bp, URL_PREFIX as docs_prefix
    app.register_blueprint(docs_bp, url_prefix=docs_prefix)
"""

from pathlib import Path

from flask import Blueprint, Response, send_from_directory

bp = Blueprint("docs", __name__)
URL_PREFIX = "/api"

DOCS_DIR = Path(__file__).resolve().parents[2] / "docs"  # <repo root>/docs
SWAGGER_UI = "https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.17.14"

PAGE = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>RentConnect API docs</title>
  <link rel="stylesheet" href="{SWAGGER_UI}/swagger-ui.css">
</head>
<body>
  <div id="swagger-ui"></div>
  <script src="{SWAGGER_UI}/swagger-ui-bundle.js"></script>
  <script>
    window.onload = function () {{
      SwaggerUIBundle({{
        url: "/api/openapi.yaml",
        dom_id: "#swagger-ui",
        deepLinking: true,
        persistAuthorization: true,
        tryItOutEnabled: true
      }});
    }};
  </script>
</body>
</html>
"""


@bp.get("/docs")
def swagger_ui():
    return Response(PAGE, mimetype="text/html")


@bp.get("/openapi.yaml")
def openapi_spec():
    return send_from_directory(DOCS_DIR, "openapi.yaml", mimetype="application/yaml")

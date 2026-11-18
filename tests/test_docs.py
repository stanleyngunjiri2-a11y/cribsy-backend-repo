"""

Needs PyYAML:  pip install pyyaml
test_every_documented_endpoint_exists only passes once every member's routes are merged and registered,
so use it as a "is everything merged?" check.
"""

import re
from pathlib import Path

import yaml

SPEC_PATH = Path(__file__).resolve().parents[1] / "docs" / "openapi.yaml"
NOT_API = {"/api/docs", "/api/openapi.yaml"}  # the documentation pages themselves


def documented():
    spec = yaml.safe_load(SPEC_PATH.read_text())
    return {
        (method.upper(), path)
        for path, operations in spec["paths"].items()
        for method in operations
    }


def real_routes(app):
    found = set()
    for rule in app.url_map.iter_rules():
        if not rule.rule.startswith("/api") or rule.rule in NOT_API:
            continue
        path = re.sub(
            r"<(?:\w+:)?(\w+)>", r"{\1}", rule.rule
        )  # <int:property_id> -> {property_id}
        for method in rule.methods - {"HEAD", "OPTIONS"}:
            found.add((method, path))
    return found


def test_the_docs_page_and_the_spec_are_served(client):
    page = client.get("/api/docs")
    spec = client.get("/api/openapi.yaml")

    assert page.status_code == 200
    assert b"swagger-ui" in page.data
    assert spec.status_code == 200
    assert b"openapi: 3" in spec.data


def test_every_endpoint_is_documented(app):
    missing = sorted(real_routes(app) - documented())

    assert not missing, f"Add these endpoints to docs/openapi.yaml: {missing}"


def test_every_documented_endpoint_exists(app):
    extra = sorted(documented() - real_routes(app))

    assert (
        not extra
    ), f"Documented, but not in the app (not merged yet, or removed): {extra}"

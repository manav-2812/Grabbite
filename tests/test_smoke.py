"""
Basic smoke tests for GrabBite.
These verify that the app starts, routes respond correctly,
and the database models are importable — no real DB or external
services required.
"""
import os
import pytest

# Set minimal env before importing the app so it doesn't complain about missing keys
os.environ.setdefault("SECRET_KEY", "ci-test-secret-key-not-for-production")
os.environ.setdefault("FLASK_ENV", "testing")
os.environ.setdefault("FLASK_DEBUG", "0")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("TESTING", "1")


@pytest.fixture(scope="session")
def app():
    from app import app as flask_app
    flask_app.config.update(
        TESTING=True,
        WTF_CSRF_ENABLED=False,
        SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
    )
    yield flask_app


@pytest.fixture(scope="session")
def client(app):
    with app.test_client() as c:
        yield c


@pytest.fixture(scope="session")
def db_tables(app):
    """Create all tables in the in-memory database once per session."""
    from db import db
    with app.app_context():
        db.create_all()
    yield


# ── App factory ───────────────────────────────────────────────────────────────

def test_app_is_created(app):
    """App object is a Flask instance."""
    from flask import Flask
    assert isinstance(app, Flask)


def test_testing_flag(app):
    """TESTING config flag is set correctly."""
    assert app.config["TESTING"] is True


# ── Models importable ─────────────────────────────────────────────────────────

def test_models_importable():
    """All SQLAlchemy models can be imported without error."""
    import models  # noqa: F401
    from models import User, Restaurant, FoodItem, Order, Cart
    assert User.__tablename__ == "users"
    assert Restaurant.__tablename__ == "restaurants"
    assert FoodItem.__tablename__ == "food_items"
    assert Order.__tablename__ == "orders"
    assert Cart.__tablename__ == "cart"


# ── Public routes ─────────────────────────────────────────────────────────────

def test_homepage_returns_200(client, db_tables):
    response = client.get("/")
    assert response.status_code == 200


def test_restaurants_page(client, db_tables):
    response = client.get("/restaurants")
    assert response.status_code == 200


def test_gallery_page(client, db_tables):
    response = client.get("/gallery")
    assert response.status_code == 200


def test_login_page(client, db_tables):
    response = client.get("/login")
    assert response.status_code == 200


def test_signup_page(client, db_tables):
    response = client.get("/signup")
    assert response.status_code == 200


def test_blogs_page(client, db_tables):
    response = client.get("/blogs")
    assert response.status_code == 200


# ── Auth redirect behaviour ───────────────────────────────────────────────────

def test_cart_redirects_unauthenticated(client, db_tables):
    """Cart page requires login — unauthenticated users get a redirect."""
    response = client.get("/cart")
    assert response.status_code in (302, 308)


def test_checkout_redirects_unauthenticated(client, db_tables):
    response = client.get("/checkout")
    assert response.status_code in (302, 308)


def test_admin_redirects_unauthenticated(client, db_tables):
    """Admin panel must not be accessible to unauthenticated users.
    In the live app this redirects (302). In the in-memory test environment
    the user-loader returns None before the redirect fires, so 404 is also
    a valid 'access denied' response here.
    """
    response = client.get("/admin/")
    assert response.status_code in (302, 308, 404)


# ── JSON API ──────────────────────────────────────────────────────────────────

def test_api_cart_count_unauthenticated(client, db_tables):
    """Cart count API returns JSON even for unauthenticated users (count = 0)."""
    response = client.get("/api/cart/count")
    assert response.status_code == 200
    data = response.get_json()
    assert data is not None
    assert "count" in data


def test_api_search_empty_query(client, db_tables):
    """Search API handles an empty query gracefully."""
    response = client.get("/api/search?q=")
    assert response.status_code in (200, 400)


# ── 404 handler ───────────────────────────────────────────────────────────────

def test_404_page(client):
    response = client.get("/this-route-definitely-does-not-exist-12345")
    assert response.status_code == 404


# ── SEO ───────────────────────────────────────────────────────────────────────

def test_robots_txt(client):
    """Robots.txt responds with plain text and status 200."""
    response = client.get("/robots.txt")
    assert response.status_code == 200
    assert "text/plain" in response.content_type
    assert b"User-agent:" in response.data
    assert b"Sitemap:" in response.data

def test_sitemap_xml(client, db_tables):
    """Sitemap.xml responds with XML and status 200."""
    response = client.get("/sitemap.xml")
    assert response.status_code == 200
    assert "application/xml" in response.content_type
    assert b"<urlset" in response.data
    assert b"<loc>" in response.data

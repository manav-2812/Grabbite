# GrabBite — Full-Stack Food Delivery Platform

[![CI](https://github.com/manav-2812/Grabbite/actions/workflows/ci.yml/badge.svg)](https://github.com/manav-2812/Grabbite/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-2.3-000000?style=flat&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Primary%20DB-336791?style=flat&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=flat&logo=docker&logoColor=white)](https://www.docker.com/)
[![Bootstrap](https://img.shields.io/badge/Bootstrap-5-7952B3?style=flat&logo=bootstrap&logoColor=white)](https://getbootstrap.com/)
[![Socket.IO](https://img.shields.io/badge/Socket.IO-Realtime-010101?style=flat&logo=socket.io&logoColor=white)](https://socket.io/)
[![Razorpay](https://img.shields.io/badge/Razorpay-Payments-02042B?style=flat&logo=razorpay&logoColor=white)](https://razorpay.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-22c55e?style=flat)](LICENSE)

[![GitHub stars](https://img.shields.io/github/stars/manav-2812/Grabbite?style=flat&logo=github&color=f59e0b)](https://github.com/manav-2812/Grabbite/stargazers)
[![GitHub forks](https://img.shields.io/github/forks/manav-2812/Grabbite?style=flat&logo=github&color=6366f1)](https://github.com/manav-2812/Grabbite/forks)
[![GitHub issues](https://img.shields.io/github/issues/manav-2812/Grabbite?style=flat&logo=github&color=ef4444)](https://github.com/manav-2812/Grabbite/issues)
[![GitHub last commit](https://img.shields.io/github/last-commit/manav-2812/Grabbite?style=flat&logo=github&color=10b981)](https://github.com/manav-2812/Grabbite/commits)

**GrabBite** is a full-stack food delivery platform engineered with **Python (Flask)** and **PostgreSQL**, designed to replicate the end-to-end experience of modern food-tech products. Customers discover restaurants, build orders, and complete payments through an integrated Razorpay checkout — while restaurant owners manage their menus and fulfil orders through a dedicated dashboard, and platform administrators maintain full operational control via a real-time admin panel. The platform is built with production concerns in mind: CSRF protection, HMAC-verified payment webhooks, rate limiting, signed password-reset tokens, WebSocket-based live order tracking, and a role-based access control system across three distinct user types.

---

## Table of Contents

- [Platform at a Glance](#platform-at-a-glance)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Installation & Setup](#installation--setup)
- [Environment Variables](#environment-variables)
- [User Roles](#user-roles)
- [API Reference](#api-reference)
- [Database Schema](#database-schema)
- [Security](#security)
- [Screenshots](#screenshots)
- [Deployment](#deployment)
- [Contributing](#contributing)

---

## Platform at a Glance

| Metric | Value |
|---|---|
| Database tables | 19 (fully relational, indexed, with audit trails) |
| API endpoints | 35+ (server-rendered pages + JSON APIs + webhooks) |
| User roles | 3 — Customer, Restaurant Owner, Admin |
| Payment flows | 2 — Cash on Delivery + Razorpay (UPI / card / net banking) |
| Order lifecycle states | 8 — `placed → accepted → preparing → ready → picked → on_the_way → delivered / cancelled` |
| Real-time events | WebSocket push via Flask-SocketIO (order updates, admin alerts) |
| CI | GitHub Actions — Python 3.11 + 3.12, SQLite in-memory, 85 tests |
| Primary database | PostgreSQL (SQLite fallback for local dev without `DATABASE_URL`) |

---

## Features

### For Customers

| Feature | Description |
|---|---|
| Restaurant discovery | Browse with ratings, cuisine types, location, and estimated delivery time |
| Dish gallery | Explore 60+ categorised dishes with details, calories, and prep time |
| Cart | Add, update, and remove items; cart is persisted in the DB and restored on login |
| Wishlist | Save favourite restaurants for later |
| Delivery addresses | Manage multiple saved addresses; select at checkout |
| Order placement | COD or online payment via Razorpay (UPI, card, net banking) |
| Order tracking | Live status updates pushed via WebSocket |
| Coupons | Apply discount codes at checkout with per-user usage limits |
| Reviews | Rate and review restaurants after delivery |
| Notifications | Real-time in-app notification feed |
| Blog | Read food-related articles |
| Search | AJAX search across restaurants, dishes, and blog posts |
| Password reset | Time-limited, signed email link via `itsdangerous` |

### For Restaurant Owners

| Feature | Description |
|---|---|
| Owner dashboard | Revenue summary, pending orders, today's order count |
| Dish management | Add, edit, delete dishes with images and availability toggles |
| Order management | Accept incoming orders and update status through the delivery lifecycle |
| Restaurant profile | Edit name, description, timings, cuisine type, and cover image |

### For Admins

| Feature | Description |
|---|---|
| Live dashboard | Real-time stats — total orders, revenue, active restaurants, user count |
| User management | View, activate, deactivate, or delete accounts |
| Restaurant management | Approve new restaurant registrations; assign owners |
| Order oversight | View and manage all orders across all restaurants |
| Dish management | Manage menu items across all restaurants |
| Blog management | Create, edit, and publish blog articles |
| Offers & coupons | Create and manage discount codes with usage limits |
| Payment records | View all payment transactions and statuses |
| Review moderation | Approve or remove customer reviews |
| Support tickets | Read and respond to customer support submissions |
| Database viewer | Inspect raw table data directly from the admin panel |
| Activity log | Full audit trail of admin actions with timestamps |
| Data exports | Export orders, users, and revenue data |

---

## Tech Stack

### Backend

| Package | Version | Purpose |
|---|---|---|
| Python | 3.11+ | Language |
| Flask | 2.3.3 | Web framework |
| Flask-SQLAlchemy | 3.0.5 | ORM |
| Flask-Login | 0.6.3 | Session & authentication |
| Flask-SocketIO | 5.3.6 | WebSocket real-time events |
| Flask-Limiter | 3.5.0 | Rate limiting on sensitive routes |
| Flask-Mail | 0.10.0 | Transactional email |
| Flask-Migrate | 4.0.5 | Alembic-backed schema migrations |
| Flask-WTF | 1.2.1 | Form handling (admin blog forms) |
| Werkzeug | 2.3.8 | Password hashing, secure uploads (patched CVE-2023-46136) |
| psycopg2-binary | 2.9.9 | PostgreSQL driver |
| Pillow | 10+ | Image resizing for uploads |
| itsdangerous | 2.1+ | Signed password-reset tokens |
| razorpay | 1.4.1 | Payment gateway SDK |
| python-dotenv | 1.0.0 | `.env` loading |

### Frontend

| Technology | Purpose |
|---|---|
| HTML5 + Jinja2 | Server-side templating |
| Bootstrap 5 | Responsive layout and components |
| Custom CSS | `modern.css`, `style.css`, `search.css`, `offers.css` |
| Vanilla JS (ES6) | Cart, search, order management, admin utilities |
| Socket.IO (client) | Live order status subscription |
| Razorpay Checkout.js | Payment modal |
| Font Awesome 6 | Icons |
| Google Fonts (Poppins + Inter) | Typography |

### Infrastructure

| Component | Role |
|---|---|
| PostgreSQL | Primary database (production) |
| SQLite | Local dev fallback (no `DATABASE_URL` needed) |
| Waitress | Pure-Python WSGI production server (zero C deps, works on Windows + Linux) |
| Nginx | Reverse proxy, static files, WebSocket upgrade |
| Docker + docker-compose | Containerised deployment (app + PostgreSQL) |
| GitHub Actions | CI — runs 85 tests on Python 3.11 + 3.12 |
| Railway | One-click cloud deployment (see [Deployment](#deployment)) |

---

## Architecture

### System Overview

```mermaid
flowchart TD
    Browser(["🌐 Browser"])
    WS(["⚡ WebSocket Client"])

    subgraph Proxy["Reverse Proxy"]
        Nginx["Nginx\n(HTTP + WS upgrade)"]
    end

    subgraph App["Application Server"]
        WSGI["Waitress / Gunicorn\n(WSGI)"]
        Flask["Flask App\napp.py"]
    end

    subgraph Blueprints["Blueprints — Route Handlers"]
        public["public_bp\n/ · /restaurants · /gallery · /blogs"]
        account["account_bp\n/login · /cart · /checkout · /orders"]
        payment["payment_bp\n/api/payment/cod · /verify · /webhook"]
        api["api_bp\n/api/cart · /api/search · /api/address"]
        admin["admin_bp\n/admin/*"]
        owner["owner_bp\n/owner/*"]
    end

    subgraph Services["Services"]
        SocketIO["Flask-SocketIO\nRoom-based push events"]
        Limiter["Flask-Limiter\nRate limiting"]
        Mail["Flask-Mail\nSMTP email"]
    end

    subgraph Data["Data Layer"]
        DB[("PostgreSQL\n19 tables")]
        Uploads["static/uploads/\nUser images"]
    end

    subgraph External["External Services"]
        Razorpay["Razorpay API\nPayments + Webhook"]
        SMTP["SMTP Server\nGmail / SendGrid"]
    end

    Browser -->|HTTP| Nginx
    Browser <-->|WebSocket| Nginx
    Nginx --> WSGI --> Flask
    Flask --> public & account & payment & api & admin & owner
    payment -->|Create order| Razorpay
    Razorpay -->|Webhook HMAC verify| payment
    public & account & payment & api & admin & owner --> DB
    Flask --> SocketIO -->|Emit order_update| WS
    Flask --> Limiter
    account -->|Send email| Mail --> SMTP
    Flask --> Uploads
```

### Razorpay Payment Flow

```mermaid
sequenceDiagram
    actor Customer as Customer
    participant Flask as Flask (payment_bp)
    participant DB as PostgreSQL
    participant RZ as Razorpay API
    participant Socket as Flask-SocketIO

    Customer->>Flask: POST /api/payment/create-razorpay-order
    Flask->>Flask: CSRF check · @login_required
    Flask->>DB: Build order from cart · apply coupon · calc totals
    Flask->>RZ: rz.order.create(amount, currency)
    RZ-->>Flask: razorpay_order_id
    Flask->>DB: INSERT order (pending) + order_items + payment
    Flask-->>Customer: { razorpay_order_id, key_id, amount }

    Customer->>RZ: Open Razorpay checkout modal · complete payment
    RZ-->>Customer: Payment success callback

    Customer->>Flask: POST /api/payment/verify { razorpay_order_id, payment_id, signature }
    Flask->>Flask: HMAC-SHA256 signature verify (compare_digest)
    Flask->>DB: UPDATE order payment_status=paid
    Flask->>DB: UPDATE payment record
    Flask->>DB: DELETE cart rows
    Flask->>DB: INSERT order_status_history + notifications
    Flask->>Socket: broadcast_update(order_update)
    Socket-->>Customer: Real-time status push
    Flask-->>Customer: { success: true, redirect: /payment/success/<id> }
```

### Database Schema

```mermaid
erDiagram
    users {
        int id PK
        string name
        string email
        string password_hash
        string role
        float wallet_balance
        string referral_code
        datetime last_login
    }
    restaurants {
        int id PK
        int owner_id FK
        string name
        string location
        string cuisine_type
        float rating
        bool is_active
        bool is_approved
    }
    food_items {
        int id PK
        int restaurant_id FK
        string name
        float price
        string category
        bool is_available
        bool is_vegetarian
    }
    orders {
        int id PK
        int user_id FK
        int restaurant_id FK
        string status
        string payment_status
        float total_amount
        string payment_method
        string razorpay_order_id
    }
    order_items {
        int id PK
        int order_id FK
        int food_item_id FK
        string name
        float price
        int quantity
    }
    order_status_history {
        int id PK
        int order_id FK
        string status
        string note
        datetime created_at
    }
    payments {
        int id PK
        int order_id FK
        int user_id FK
        float amount
        string payment_method
        string status
        string gateway_order_id
        string gateway_payment_id
        string gateway_signature
    }
    cart {
        int id PK
        int user_id FK
        int food_item_id FK
        int quantity
        float price
    }
    addresses {
        int id PK
        int user_id FK
        string label
        string full_address
        bool is_default
    }
    reviews {
        int id PK
        int user_id FK
        int restaurant_id FK
        int order_id FK
        float rating
        string comment
    }
    notifications {
        int id PK
        int user_id FK
        string title
        string type
        bool is_read
    }
    offers {
        int id PK
        string code
        string discount_type
        float discount_value
        int usage_limit
        int used_count
    }
    coupon_usage {
        int id PK
        int offer_id FK
        int user_id FK
        int order_id FK
    }
    wishlist {
        int id PK
        int user_id FK
        int restaurant_id FK
    }

    users ||--o{ restaurants : owns
    users ||--o{ orders : places
    users ||--o{ cart : has
    users ||--o{ addresses : has
    users ||--o{ reviews : writes
    users ||--o{ notifications : receives
    users ||--o{ wishlist : saves
    restaurants ||--o{ food_items : has
    restaurants ||--o{ orders : receives
    restaurants ||--o{ reviews : receives
    food_items ||--o{ cart : in
    food_items ||--o{ order_items : in
    orders ||--o{ order_items : contains
    orders ||--o{ order_status_history : tracks
    orders ||--|| payments : has
    orders ||--o{ coupon_usage : uses
    offers ||--o{ coupon_usage : tracked-by
    wishlist }o--|| restaurants : references
```

---

## Project Structure

```
Grabbite/
│
├── app.py                    # App factory — config, blueprints, CSRF, security headers
├── run.py                    # Entry point — Flask dev server or Waitress (prod)
├── db.py                     # SQLAlchemy db instance (singleton, avoids circular imports)
├── auth_routes.py            # Login, signup, logout, profile update handler functions
│
├── models/
│   ├── __init__.py           # Re-exports all models — no import changes elsewhere
│   ├── constants.py          # Shared enums: ROLES, ORDER_STATUSES, PAYMENT_*
│   ├── user.py               # User, Address
│   ├── restaurant.py         # Restaurant, FoodItem
│   ├── order.py              # Cart, Order, OrderItem, OrderStatusHistory
│   ├── payment.py            # Payment, WalletTransaction
│   ├── offer.py              # Offer, CouponUsage
│   ├── blog.py               # Blog
│   ├── review.py             # Review
│   ├── notification.py       # Notification, AdminNotification
│   ├── support.py            # SupportTicket
│   ├── wishlist.py           # Wishlist
│   └── admin.py              # AdminActivity
│
├── blueprints/
│   ├── __init__.py           # Imports and exposes all blueprint objects
│   ├── public.py             # Home, restaurants, gallery, blogs, search, offers
│   ├── account.py            # Auth pages, profile, cart, checkout, orders, addresses
│   ├── payment.py            # COD order, Razorpay order creation, verify, webhook
│   ├── admin/
│   │   ├── __init__.py       # Blueprint object + shared helpers (save_image, log_activity)
│   │   ├── dashboard.py      # Live stats, charts, recent activity
│   │   ├── users.py          # User management CRUD
│   │   ├── restaurants.py    # Restaurant CRUD, menu management, owner assignment
│   │   ├── orders.py         # All-orders view, status updates
│   │   ├── dishes.py         # Cross-restaurant dish management
│   │   ├── blogs.py          # Blog CRUD
│   │   ├── offers.py         # Coupon creation and management
│   │   ├── payments.py       # Payment records and refund tracking
│   │   ├── reviews.py        # Review moderation
│   │   ├── support.py        # Support ticket management
│   │   ├── notifications.py  # Admin broadcast notifications
│   │   ├── database.py       # Raw database viewer
│   │   └── exports.py        # CSV/JSON data exports
│   ├── api/
│   │   ├── __init__.py       # Blueprint object; imports all sub-modules
│   │   ├── cart.py           # GET/POST cart, add, update, remove, clear
│   │   ├── search.py         # Full-text search across restaurants, dishes, blogs
│   │   ├── address.py        # Delivery address CRUD
│   │   ├── coupon.py         # Coupon validation and application
│   │   ├── wishlist.py       # Wishlist add / remove
│   │   ├── reviews.py        # Review submission
│   │   ├── notifications.py  # Mark read, clear all
│   │   └── misc.py           # Health, misc helpers
│   └── owner/
│       ├── __init__.py
│       └── routes.py         # Dashboard, dishes CRUD, order status, profile
│
├── utils/
│   ├── helpers.py            # food_image_url, format_currency, safe_next_url, register_template_globals
│   ├── mail.py               # send_order_confirmation, send_password_reset_email, send_welcome_email
│   ├── decorators.py         # @admin_required, @owner_required, @role_required
│   ├── order_helpers.py      # _build_order_from_cart, _create_order_record, _post_order_notifications
│   ├── razorpay_helpers.py   # _get_razorpay_client, verify_razorpay_signature, verify_webhook_signature
│   ├── socket_events.py      # register_socket_events, broadcast_update
│   ├── uploads.py            # allowed_file, magic-byte check, resize_image, save_upload
│   ├── seed_data.py          # Seed restaurants, dishes, and blog posts on first boot
│   ├── image_data.py         # Curated Pexels image URL map for seeded data
│   └── page_builders.py      # Static offer cards and dish catalogue for gallery/search
│
├── templates/
│   ├── base.html             # Master layout (navbar, cart drawer, footer, socket init)
│   ├── index.html            # Homepage — hero, categories, top restaurants, trending dishes
│   ├── login.html / signup.html / signup_owner.html
│   ├── forgot_password.html / reset_password.html
│   ├── restaurants.html      # Restaurant listing with filters and pagination
│   ├── restaurant_menu.html  # Menu, reviews, wishlist button
│   ├── gallery.html          # Full dish catalogue grouped by category
│   ├── dish_detail.html      # Individual dish detail page
│   ├── cart.html             # Shopping cart with quantity controls
│   ├── checkout.html         # Address selection, payment method, order summary
│   ├── orders.html           # Customer order history
│   ├── profile.html          # Profile editor, password change
│   ├── address.html          # Saved delivery addresses
│   ├── wishlist.html         # Saved restaurants
│   ├── notifications.html    # In-app notification feed
│   ├── blogs.html / blog_detail.html
│   ├── search.html           # Live search results
│   ├── payment_success.html / payment_failed.html
│   ├── offer_details.html / about.html / help.html / careers.html
│   ├── database_viewer.html  # Admin raw table viewer
│   ├── admin/                # 18 admin panel templates
│   ├── owner/                # 6 owner dashboard templates
│   ├── emails/               # 6 transactional HTML email templates
│   └── errors/               # 403, 404, 500 error pages
│
├── static/
│   ├── css/                  # modern.css, style.css, search.css, offers.css
│   ├── js/                   # admin-utils.js, cart.js, checkout.js, search.js, …
│   ├── img/                  # Default images (food-default.jpg, restaurant-default.jpg, …)
│   └── uploads/              # User-uploaded images (gitignored)
│
├── scripts/
│   ├── audit_and_fix.py      # DB health check: tables, sequences, FK integrity, order smoke test
│   └── fix_sequences.py      # Resets PostgreSQL sequences to MAX(id) after a bulk import
│
├── tests/
│   ├── test_smoke.py         # Smoke tests — app boot, routing, auth redirects, JSON APIs
│   ├── test_order_logic.py   # Unit tests — Order/OrderItem models, pricing, coupon, _create_order_record
│   └── test_payment_logic.py # Unit tests — Payment model, HMAC signatures, webhook DB side-effects
│
├── docs/
│   └── DEPLOYMENT.md         # Full production deployment guide (VPS, Docker, Railway, cloud)
│
├── Dockerfile                # Multi-stage production image (python:3.11-slim)
├── docker-compose.yml        # App + PostgreSQL for local Docker development
├── .dockerignore             # Excludes .venv, .env, instance/, tests/ from the image
├── .env.example              # All supported environment variables with documentation
├── .github/workflows/ci.yml  # GitHub Actions CI pipeline
├── requirements.txt          # Python production dependencies (pinned)
├── requirements-dev.txt      # Development and test dependencies
├── pytest.ini                # Pytest configuration
└── pyrightconfig.json        # Pyright type checker configuration
```

---

## Prerequisites

- **Python 3.11+**
- **PostgreSQL 14+** (or use SQLite for local dev by omitting `DATABASE_URL`)
- **Git**

---

## Installation & Setup

### 1. Clone the repository

```bash
git clone https://github.com/manav-2812/Grabbite.git
cd Grabbite
```

### 2. Create and activate a virtual environment

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt   # optional, for tests and linting
```

### 4. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env`. The minimum required for local development:

```env
SECRET_KEY=any-random-string-for-dev
FLASK_ENV=development
FLASK_DEBUG=1

# Leave DATABASE_URL unset to use SQLite automatically, or set PostgreSQL:
DATABASE_URL=postgresql+psycopg2://postgres@localhost:5432/grabbite
```

### 5. Run the application

```bash
python run.py
```

On first boot the app will:
- Create all database tables via `db.create_all()`
- Seed demo restaurants, dishes, and blog posts
- Print a one-time admin password to the terminal

Open **http://127.0.0.1:8000** in your browser.

### Alternative — Docker (app + PostgreSQL in one command)

```bash
docker-compose up -d --build
```

This starts the Flask app on port `8000` and a PostgreSQL container. No manual DB setup needed. On first boot the app seeds demo data automatically.

```bash
docker-compose logs -f web    # follow app logs
docker-compose down           # stop
docker-compose down -v        # stop + wipe DB volume
```

### 6. (Optional) Fix PostgreSQL sequences after a bulk import

If you restored data from a dump or migrated from SQLite, primary key sequences may be out of sync (causing duplicate key errors on insert). Run once:

```bash
PYTHONPATH=. python scripts/fix_sequences.py
```

### 7. Run the test suite

```bash
pytest tests/ -v
```

The suite has 85 tests across three files:

| File | Coverage |
|---|---|
| `test_smoke.py` | App boot, routing, auth redirects, JSON API responses |
| `test_order_logic.py` | Order/OrderItem models, pricing rules, coupon validation, `_create_order_record` DB persistence |
| `test_payment_logic.py` | Payment model, Razorpay HMAC signature verification, webhook signature, webhook DB side-effects |

---

## Environment Variables

Full documentation for every variable is in `.env.example`. Key variables:

| Variable | Required | Description |
|---|---|---|
| `SECRET_KEY` | Production | Flask session signing key. Generate with `python -c "import secrets; print(secrets.token_urlsafe(64))"` |
| `FLASK_ENV` | No | `development` (default) or `production` |
| `DATABASE_URL` | No | PostgreSQL URI. Omit to fall back to `instance/grabbite.db` (SQLite) |
| `RAZORPAY_KEY_ID` | No | Razorpay public key. App falls back to COD-only if unset |
| `RAZORPAY_KEY_SECRET` | No | Razorpay secret key |
| `RAZORPAY_WEBHOOK_SECRET` | Production | Webhook HMAC signing secret |
| `MAIL_SERVER` | No | SMTP host. Leave blank to disable email silently |
| `MAIL_USERNAME` | No | SMTP username |
| `MAIL_PASSWORD` | No | SMTP password or app password |
| `ADMIN_EMAIL` | Production | Bootstrap admin email (read once on first boot in production) |
| `ADMIN_PASSWORD` | Production | Bootstrap admin password |
| `REDIS_URL` | No | Redis URI for rate limiter. Defaults to `memory://` (single-worker) |
| `SOCKETIO_ALLOWED_ORIGINS` | No | Comma-separated WebSocket origins. Defaults to localhost |

---

## User Roles

| Role | Registration | Access |
|---|---|---|
| **Customer** | `/signup` | Browse, order, review, wishlist, notifications |
| **Restaurant Owner** | `/signup/restaurant` | Owner dashboard (`/owner/*`), dishes, orders for own restaurant |
| **Admin** | Seeded on first boot or via `flask create-admin` | Full admin panel (`/admin/*`) |

---

## API Reference

All API endpoints return JSON. State-changing requests require a `_csrf_token` field (forms) or `X-CSRF-Token` header (fetch/XHR).

### Cart

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/cart/count` | Cart item count (unauthenticated returns 0) |
| `GET` | `/api/cart` | Full cart with pricing summary |
| `POST` | `/api/cart/add` | Add item `{food_item_id, quantity, notes}` |
| `POST` | `/api/cart/update` | Update quantity `{cart_id, quantity}` |
| `POST` | `/api/cart/remove` | Remove item `{cart_id}` |
| `POST` | `/api/cart/clear` | Clear entire cart |

### Payments & Orders

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/payment/cod` | Place a Cash on Delivery order |
| `POST` | `/api/payment/create-razorpay-order` | Create Razorpay order, returns gateway details |
| `POST` | `/api/payment/verify` | Verify Razorpay HMAC signature, confirm order as paid |
| `POST` | `/api/payment/webhook` | Razorpay server-to-server webhook (CSRF-exempt) |

### Search

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/search?q=&type=` | Search restaurants, dishes, or blogs |

### Address

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/addresses` | List saved addresses |
| `POST` | `/api/address/add` | Add address |
| `POST` | `/api/address/<id>/set-default` | Set default address |
| `DELETE` | `/api/address/<id>` | Delete address |

### Wishlist & Reviews

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/wishlist/toggle` | Add or remove restaurant from wishlist |
| `POST` | `/api/reviews/submit` | Submit a review `{restaurant_id, rating, comment}` |

### Notifications

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/notifications/mark-read` | Mark one or all notifications read |
| `POST` | `/api/notifications/clear` | Delete all notifications for current user |

### Health

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/healthz` | Liveness probe — always 200 |
| `GET` | `/readyz` | Readiness probe — checks DB connectivity |

---

## Database Schema

19 tables. Relationships at a glance:

```
users
  ├── addresses           (user_id FK)
  ├── cart                (user_id FK, food_item_id FK)
  ├── orders              (user_id FK, restaurant_id FK)
  │     ├── order_items          (order_id FK, food_item_id FK)
  │     ├── order_status_history (order_id FK)
  │     └── payments             (order_id FK)
  ├── reviews             (user_id FK, restaurant_id FK)
  ├── notifications       (user_id FK)
  ├── wishlist            (user_id FK, restaurant_id FK)
  ├── support_tickets     (user_id FK)
  └── wallet_transactions (user_id FK)

restaurants             (owner_id FK → users)
  └── food_items         (restaurant_id FK)

offers
  └── coupon_usage       (offer_id FK, user_id FK, order_id FK)

blogs
admin_notifications
admin_activities        (admin_id FK → users)
```

All tables use integer primary keys with PostgreSQL sequences. Foreign key indexes are explicit. Compound indexes on high-traffic lookups (`payments.order_id + status`, `cart.user_id + food_item_id`).

---

## Security

| Control | Implementation |
|---|---|
| CSRF protection | Custom `before_request` hook; validates token from header, JSON body, or form field via `hmac.compare_digest` |
| Password hashing | `werkzeug` `pbkdf2:sha256` |
| Password reset | Time-limited (30 min) signed URL via `itsdangerous.URLSafeTimedSerializer` |
| Session protection | `strong` mode in production (rotates session ID on IP/UA change) |
| Rate limiting | `Flask-Limiter` on login, signup, payment verify; Redis-backed in production |
| File uploads | Extension allowlist + magic-byte validation + `secure_filename` + Pillow resize |
| Razorpay webhook | `HMAC-SHA256` signature verification on raw request body |
| Security headers | `X-Content-Type-Options`, `X-Frame-Options: SAMEORIGIN`, `Referrer-Policy`, `Permissions-Policy`, `HSTS` (production only) |
| Open redirect prevention | `safe_next_url()` rejects non-relative `?next=` URLs |
| Production secret key | Refuses to boot without `SECRET_KEY`; derives stable dev key from file path |
| Cookie flags | `HttpOnly`, `SameSite=Lax`; `Secure` enabled automatically in production |

---

## Screenshots

| Page | Screenshot |
|---|---|
| Homepage | ![Homepage](assets/screenshots/homepage.png) |
| Restaurant listing | ![Restaurants](assets/screenshots/restaurants.png) |
| Restaurant menu | ![Menu](assets/screenshots/menu.png) |
| Cart | ![Cart](assets/screenshots/cart.png) |
| Admin dashboard | ![Admin](assets/screenshots/admin.png) |
| Login | ![Login](assets/screenshots/login.png) |
| Gallery | ![Gallery](assets/screenshots/gallery.png) |

---

## Deployment

### Railway (recommended — one-click from GitHub)

Railway automatically detects the `Dockerfile` and provides a managed PostgreSQL add-on.

1. Push the repo to GitHub (already done)
2. Go to [railway.app](https://railway.app) → **New Project** → **Deploy from GitHub repo** → select `Grabbite`
3. Add a **PostgreSQL** plugin from the Railway dashboard
4. Set the following environment variables in the Railway service settings:

```env
SECRET_KEY=<generate a 64-byte random string>
FLASK_ENV=production
FLASK_DEBUG=0
DATABASE_URL=<auto-filled by Railway PostgreSQL plugin>
ADMIN_EMAIL=admin@yourdomain.com
ADMIN_PASSWORD=<strong password>
RAZORPAY_KEY_ID=<your live key>
RAZORPAY_KEY_SECRET=<your live secret>
RAZORPAY_WEBHOOK_SECRET=<your webhook secret>
SOCKETIO_ALLOWED_ORIGINS=https://your-railway-domain.up.railway.app
```

5. Railway deploys automatically on every push to `main`. The `/healthz` endpoint is used as the health probe.

> Railway injects `$PORT` at runtime — `run.py` reads it automatically.

---

### Docker (local or any VPS)

```bash
# Build and start app + PostgreSQL
docker-compose up -d --build

# App is available at http://localhost:8000
# Follow logs
docker-compose logs -f web

# Stop
docker-compose down
```

Override any environment variable by creating a `.env` file in the project root before running `docker-compose up`.

---

### Traditional VPS (Ubuntu + Nginx)

See [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) for the full guide covering Nginx config, systemd service, and Let's Encrypt SSL.

---

### Production checklist

- [ ] `SECRET_KEY` set to a 64-byte random value
- [ ] `FLASK_ENV=production`, `FLASK_DEBUG=0`
- [ ] `DATABASE_URL` pointing to PostgreSQL
- [ ] `ADMIN_EMAIL` and `ADMIN_PASSWORD` set for first boot
- [ ] HTTPS / TLS certificate configured
- [ ] `MAIL_SERVER` and credentials set for transactional email
- [ ] Razorpay **live** keys set (not test keys)
- [ ] `RAZORPAY_WEBHOOK_SECRET` set
- [ ] `SOCKETIO_ALLOWED_ORIGINS` set to your public domain
- [ ] `SESSION_COOKIE_SECURE=1` ensured by `FLASK_ENV=production`

---

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for guidelines. Pull requests are welcome.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Run tests (`pytest tests/ -v`)
4. Commit and push
5. Open a pull request against `main`

---

## License

MIT — see [`LICENSE`](LICENSE).

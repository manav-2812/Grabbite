# 🍽️ GrabBite — Full-Stack Food Ordering Platform

<!-- CI badge -->

![CI](https://github.com/manav-2812/Grabbite/actions/workflows/ci.yml/badge.svg)

<!-- Tech badges -->

![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=flat&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-2.3-000000?style=flat&logo=flask&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-Database-003B57?style=flat&logo=sqlite&logoColor=white)
![Bootstrap](https://img.shields.io/badge/Bootstrap-5-7952B3?style=flat&logo=bootstrap&logoColor=white)
![Socket.IO](https://img.shields.io/badge/Socket.IO-Realtime-010101?style=flat&logo=socket.io&logoColor=white)
![Razorpay](https://img.shields.io/badge/Razorpay-Payments-02042B?style=flat&logo=razorpay&logoColor=white)
![License: MIT](https://img.shields.io/badge/License-MIT-22c55e?style=flat)

<!-- GitHub repo badges — replace YOUR_USERNAME with your GitHub username after pushing -->

![GitHub stars](https://img.shields.io/github/stars/manav-2812/Grabbite?style=flat&logo=github&color=f59e0b)
![GitHub forks](https://img.shields.io/github/forks/manav-2812/Grabbite?style=flat&logo=github&color=6366f1)
![GitHub issues](https://img.shields.io/github/issues/manav-2812/Grabbite?style=flat&logo=github&color=ef4444)
![GitHub last commit](https://img.shields.io/github/last-commit/manav-2812/Grabbite?style=flat&logo=github&color=10b981)

GrabBite is a production-grade, full-stack food ordering platform built with **Python (Flask)**. It mirrors the core flows of platforms like Zomato and Swiggy: customers browse restaurants, order food, and pay online — while restaurant owners manage menus and admins oversee everything from a live dashboard.

---

## 📋 Table of Contents

- [Why This Is Interesting](#-why-this-is-interesting)
- [Technical Highlights](#-technical-highlights--what-i-learned)
- [Features](#-features)
- [Tech Stack](#️-tech-stack)
- [Architecture](#️-architecture)
- [Project Structure](#-project-structure)
- [Prerequisites](#-prerequisites)
- [Installation & Setup](#️-installation--setup)
- [Environment Variables](#-environment-variables)
- [User Roles](#-user-roles)
- [API Endpoints](#-api-endpoints)
- [Database Schema](#️-database-schema)
- [Security](#-security)
- [Screenshots](#-screenshots)
- [Deployment](#-deployment)
- [Future Improvements](#-future-improvements)
- [Author](#-author)
- [Acknowledgements](#-acknowledgements)

---

## 🌟 Why This Is Interesting

This is not a tutorial CRUD app. GrabBite solves the kinds of engineering problems that show up in real production systems — and the decisions made here are the same ones you'd face at a food-tech startup.

### Scale & Scope

| Metric | Value |
|---|---|
| **Database tables** | 16 (fully relational, with indexes and audit trails) |
| **API endpoints** | 30+ (pages, JSON APIs, webhooks) |
| **User roles** | 3 (Customer, Restaurant Owner, Admin) — each with distinct route guards |
| **Test coverage** | 15 smoke tests across auth, routing, and JSON APIs via CI (GitHub Actions) |
| **Lines of Python** | ~4,500 across 25+ modules |
| **Payment flows** | 3 (COD, Razorpay online, GrabBite Wallet) |
| **Order lifecycle states** | 8 (`placed → accepted → preparing → ready → picked → on_the_way → delivered / cancelled`) |

### Real Problems Solved

**1. Consistent money handling across three payment methods**
The platform supports COD, Razorpay (UPI/card/net banking), and a built-in wallet — each with its own state machine. A single `Payment` model stores gateway IDs, HMAC signatures, and refund status so order reconciliation is always traceable. Razorpay webhooks are verified with `hmac.compare_digest` to prevent replay attacks.

**2. Real-time order tracking without long-polling**
Instead of hammering the server every few seconds, the app pushes order status changes to browsers via Flask-SocketIO. Users join authenticated rooms on connect; owners and admins join a separate `admin_users` room. This means a status update in the admin panel reflects instantly in the customer's browser — zero polling, zero extra load.

**3. A cart that survives page reloads and logins**
The cart is persisted in the database (not localStorage), so a customer can add items on mobile, log in on desktop, and pick up exactly where they left off. A `UniqueConstraint('user_id', 'food_item_id')` prevents duplicate rows; quantity is always an update, never an insert.

**4. Security hardened from the ground up**
Most Flask tutorials skip security. GrabBite didn't: custom CSRF protection on every state-changing request, `pbkdf2:sha256` password hashing, time-limited signed password-reset tokens via `itsdangerous`, `strong` session protection in production, rate limiting on login/signup/payment endpoints, and a full set of security response headers (`X-Content-Type-Options`, `X-Frame-Options`, `HSTS`).

**5. One codebase, three database backends**
The `DATABASE_URL` env var switches between SQLite (dev), PostgreSQL (production), and MySQL/MariaDB — with the SQLAlchemy `postgres://` → `postgresql+psycopg2://` scheme fix applied automatically so Heroku deployments don't break silently.

### Architecture Decisions Explained

| Decision | Why |
|---|---|
| **Flask over Django** | Deliberately chosen for transparency — you see every wire-up (extensions, blueprints, CSRF). Django hides this; Flask forces you to understand it. |
| **SQLite → PostgreSQL via `DATABASE_URL`** | Zero friction locally; swap one env var for production scale. SQLAlchemy ORM abstracts the difference. |
| **Flask-SocketIO threading mode** | Avoids the eventlet monkey-patch footgun. Simpler, more debuggable, and sufficient for demo/small-scale production. Eventlet can be enabled with one line. |
| **Custom CSRF (not Flask-WTF)** | WTF-CSRF exempts JSON APIs by default, which left gaps. The custom `before_request` hook covers form-encoded POST, JSON body, and header — all paths. |
| **Blueprints for each domain** | `public`, `account`, `payment`, `api`, `admin`, `owner` — each owns its URL namespace and can be tested or deployed independently. |
| **Dual order line-item storage** | `Order.order_items` (JSON) for backward compat + `OrderItem` table (normalized) for querying. New orders write both; old data isn't broken. |
| **Session notification cache** | Notification count is cached in the session for 30 s to avoid a DB hit on every page render. Invalidated on write. |

---

## 🧠 Technical Highlights — What I Learned

### 1. Building CSRF Protection from First Principles

Flask-WTF's CSRF skips JSON endpoints by design. GrabBite's `before_request` hook validates a token from **four different locations** — `X-CSRF-Token` header, `X-CSRFToken` header (Django-style alias for admin templates), JSON body `_csrf` field, and form field `_csrf_token`. This closed a real gap where form-encoded POST requests (profile update, address save) had no CSRF protection at all.

```python
def _csrf_is_valid():
    sent = (
        request.headers.get('X-CSRF-Token', '')
        or request.headers.get('X-CSRFToken', '')
        or (request.get_json(silent=True) or {}).get('_csrf')
        or request.form.get('_csrf_token', '')
    )
    stored = session.get('_csrf_token', '')
    return bool(sent) and bool(stored) and hmac.compare_digest(sent, stored)
```

**Lesson:** `hmac.compare_digest` is essential — string `==` is vulnerable to timing attacks on auth tokens.

### 2. Razorpay Webhook Security — HMAC Signature Verification

Razorpay sends a `X-Razorpay-Signature` header with every webhook. The server verifies it by computing `HMAC-SHA256(webhook_secret, raw_body)` and comparing with `compare_digest`. Without this, any attacker who discovers the webhook URL can fake a "payment successful" event and get free food.

```python
def verify_webhook_signature(raw_body: bytes, signature: str, secret: str) -> bool:
    expected = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)
```

**Lesson:** Never trust payment gateway callbacks without cryptographic verification. The raw body (not parsed JSON) must be used for signing.

### 3. WebSocket Room Architecture

Flask-SocketIO's room system maps directly to user roles. On connect:
- All authenticated users join `authenticated_users` — receives order updates
- Admins additionally join `admin_users` — receives new-order alerts for the live dashboard

The `broadcast_update()` helper is a single call-site throughout the app — it wraps `socketio.emit` with error suppression so a disconnected socket never crashes an order placement.

**Lesson:** Rooms are the right primitive for role-scoped real-time events. Don't try to filter events client-side — filter them server-side at emit time.

### 4. Blueprint Refactoring — Breaking Up a Monolith

The project started as a single `app.py` file (common Flask beginner pattern). It was split into 6 blueprints (`public`, `account`, `payment`, `api`, `admin`, `owner`) and 12 utility modules. The critical challenge: **circular imports**. The solution was a `db.py` singleton (SQLAlchemy instance lives there, not in `app.py`) and an `extensions.py` for shared objects — both imported by blueprints without importing `app.py`.

```
db.py          ← SQLAlchemy instance (no Flask app import)
extensions.py  ← mail, limiter, socketio instances
models/        ← import from db.py only
blueprints/    ← import from models, db, extensions
app.py         ← imports everything, wires it up last
```

**Lesson:** The circular import problem in Flask is a design smell — it's solved by dependency injection and the application factory pattern, not by creative import ordering.

### 5. Secure File Uploads with Server-Side Validation

Uploaded images (profile photos, dish images, restaurant banners) are validated in two layers:
1. **Extension allowlist** — only `{png, jpg, jpeg, gif, webp}` accepted
2. **Magic-byte check** (`_looks_like_image`) — reads the first 12 bytes to verify the file is actually an image, not a renamed `.php` or `.exe`

Filenames are sanitized with `werkzeug.secure_filename` before saving. Images are resized with Pillow to a max of 800×800 px to prevent disk exhaustion.

**Lesson:** Client-supplied MIME types and extensions are untrusted. Always validate file content server-side.

### 6. Production Secret Key Management

The app refuses to start in production without `SECRET_KEY`. In development, a stable key is *derived* from the project path so sessions survive server restarts during iteration — without hardcoding a weak key. A warning is printed so developers know they're not running a real secret.

```python
def _resolve_secret_key() -> str:
    key = os.environ.get('SECRET_KEY')
    if key:
        return key
    if _is_production:
        raise RuntimeError('SECRET_KEY is required in production.')
    # Dev: derive stable key from file path — survives restarts, never committed
    return hashlib.sha256((db_url + '|' + __file__).encode()).hexdigest()
```

**Lesson:** "Just use a random key in dev" causes constant session invalidation. Deriving from a stable seed is the ergonomic middle ground.

### 7. Order Line-Item Migration Without Breaking Old Data

The original `Order` model stored line items as a JSON blob (`order_items = db.Column(db.JSON)`). This is queryable but not relational — you can't ask "which food items appear most in orders?" without parsing JSON in Python.

The fix: add a normalized `OrderItem` table (foreign-keyed to both `Order` and `FoodItem`) while keeping the JSON column for backward compatibility. New orders write to **both**. Old orders are still readable via the JSON column. A migration backfill script is provided.

**Lesson:** Dual-write is a safe migration pattern for production systems where you can't afford downtime or data loss during schema changes.

### 8. Rate Limiting with Graceful Degradation

`Flask-Limiter` is imported inside a `try/except` block. If the library is missing, a `_NullLimiter` stub is injected so `@limiter.limit(...)` decorators on routes become no-ops rather than import errors. The same pattern applies to Razorpay — COD works without the SDK installed.

**Lesson:** Optional dependencies should degrade gracefully, not crash. Use stub objects to keep decorator syntax working without the real library.

---

## ✨ Features

### 👤 For Customers

| Feature                  | Description                                                                           |
| ------------------------ | ------------------------------------------------------------------------------------- |
| **Restaurant Discovery** | Browse restaurants with ratings, cuisine types, location, and estimated delivery time |
| **Dish Gallery**         | Explore 60+ dishes across categories with full details, calories, and prep time       |
| **Cart System**          | Add/remove items, update quantities; cart is saved to the DB and restored on login    |
| **Wishlist**             | Save favourite dishes for later                                                       |
| **Multiple Addresses**   | Manage and select delivery addresses at checkout                                      |
| **Order Placement**      | COD or online payment via Razorpay (UPI, card, net banking)                           |
| **Order Tracking**       | Live status updates: placed → preparing → on the way → delivered                      |
| **Wallet**               | GrabBite wallet balance with top-up and usage history                                 |
| **Offers & Coupons**     | Apply discount coupons at checkout                                                    |
| **Reviews**              | Rate and review restaurants after delivery                                            |
| **Notifications**        | Real-time in-app notifications via WebSockets                                         |
| **Blog**                 | Read food-related articles                                                            |
| **Search**               | Real-time AJAX search across restaurants, dishes, and blogs                           |

### 🏪 For Restaurant Owners

| Feature              | Description                                                      |
| -------------------- | ---------------------------------------------------------------- |
| **Owner Dashboard**  | Manage dishes, view incoming orders, and update order status     |
| **Dish Management**  | Add, edit, or remove dishes with images and availability toggles |
| **Order Management** | Accept and update status of incoming orders                      |

### 🛡️ For Admins

| Feature                  | Description                                                                         |
| ------------------------ | ----------------------------------------------------------------------------------- |
| **Admin Panel**          | Manage all users, restaurants, orders, dishes, blogs, offers, payments, and tickets |
| **Live Dashboard**       | Real-time stats — total orders, revenue, active restaurants, user count             |
| **User Management**      | View, activate/deactivate, or delete user accounts                                  |
| **Restaurant Approvals** | Approve new registrations and send approval emails                                  |
| **Database Viewer**      | Inspect raw database tables directly from the panel                                 |
| **Activity Log**         | Track all admin actions with timestamps                                             |

---

## 🛠️ Tech Stack

### Backend

| Technology           | Version | Purpose                                               |
| -------------------- | ------- | ----------------------------------------------------- |
| **Python**           | 3.11+   | Programming language                                  |
| **Flask**            | 2.3     | Web framework                                         |
| **Flask-SQLAlchemy** | 3.0     | Database ORM                                          |
| **Flask-Login**      | 0.6     | Session & authentication management                   |
| **Flask-SocketIO**   | 5.3     | Real-time WebSocket (order notifications)             |
| **Flask-Limiter**    | 3.5     | Rate limiting on sensitive endpoints                  |
| **Flask-Mail**       | 0.10    | Transactional emails (confirmations, password resets) |
| **Flask-Migrate**    | 4.0     | Database schema migrations                            |
| **Werkzeug**         | 2.3     | Password hashing, secure file uploads                 |
| **Pillow**           | 10+     | Profile photo and image resizing                      |
| **itsdangerous**     | 2.1+    | Signed, time-limited password-reset tokens            |
| **Razorpay**         | 1.4     | Online payment gateway (UPI, card, net banking)       |
| **Gunicorn**         | —       | Production WSGI server (Linux/Mac)                    |

### Frontend

| Technology                         | Purpose                                                               |
| ---------------------------------- | --------------------------------------------------------------------- |
| **HTML5 + Jinja2**                 | Server-side templating                                                |
| **Vanilla CSS**                    | Custom styles (`modern.css`, `style.css`, `search.css`, `offers.css`) |
| **Bootstrap 5**                    | Responsive layout grid and components                                 |
| **JavaScript (ES6)**               | Cart logic, search, order management, admin utilities                 |
| **Font Awesome 6**                 | Icons                                                                 |
| **Google Fonts (Poppins + Inter)** | Typography                                                            |
| **Socket.IO (client)**             | Live order status updates                                             |
| **Razorpay Checkout.js**           | Payment UI                                                            |

### Database

| Database            | Usage                                                     |
| ------------------- | --------------------------------------------------------- |
| **SQLite**          | Default for development — zero setup, built into Python   |
| **PostgreSQL**      | Recommended for production — set `DATABASE_URL` in `.env` |
| **MySQL / MariaDB** | Supported — install the `PyMySQL` driver                  |

---

## 🏗️ Architecture

```mermaid
graph TB
    subgraph "Client Layer"
        A[User Browser]
        WS[WebSocket Client<br/>Socket.IO]
    end

    subgraph "Reverse Proxy"
        B[Nginx]
    end

    subgraph "Application Server"
        C[Gunicorn / Waitress<br/>WSGI]
        D[Flask App Factory<br/>app.py]
    end

    subgraph "Blueprints — Route Handlers"
        E[public_bp<br/>Home · Restaurants · Gallery · Search]
        F[account_bp<br/>Login · Signup · Profile · Wishlist]
        G[payment_bp<br/>COD · Razorpay · Webhook]
        H[api_bp<br/>Cart · Orders · Search JSON]
        I[admin_bp<br/>Dashboard · Users · Reports]
        J[owner_bp<br/>Dishes · Order Status]
    end

    subgraph "Services"
        K[Flask-SocketIO<br/>Room-based push events]
        L[Flask-Limiter<br/>Rate limiting]
        M[Flask-Mail<br/>SMTP email]
    end

    subgraph "Data Layer"
        N[(SQLite · PostgreSQL<br/>16 tables)]
        O[static/uploads/<br/>Images]
    end

    subgraph "External"
        P[Razorpay API<br/>Payment + Webhook]
        Q[SMTP Server<br/>Gmail / SendGrid]
    end

    A -->|HTTP| B
    A <-->|WebSocket| B
    B --> C
    C --> D
    D --> E & F & G & H & I & J
    E & F & G & H & I & J --> N
    G -->|Create order| P
    P -->|Webhook HMAC verify| G
    D --> K
    K -->|Emit order_update| WS
    D --> L
    F -->|Send email| M
    M --> Q
    D --> O
```

### Request Lifecycle

```mermaid
sequenceDiagram
    participant Browser
    participant Nginx
    participant Flask
    participant DB
    participant Razorpay
    participant SocketIO

    Browser->>Nginx: POST /api/payment/create-order
    Nginx->>Flask: Forward + X-Real-IP header
    Flask->>Flask: CSRF token validation (before_request)
    Flask->>Flask: @login_required check
    Flask->>DB: Build order from cart items
    Flask->>Razorpay: Create Razorpay order (REST)
    Razorpay-->>Flask: razorpay_order_id
    Flask-->>Browser: {razorpay_order_id, key_id}
    Browser->>Razorpay: Open checkout modal
    Razorpay-->>Browser: Payment success callback
    Browser->>Flask: POST /api/payment/verify (signature)
    Flask->>Flask: HMAC-SHA256 signature verify
    Flask->>DB: Mark order paid, clear cart
    Flask->>SocketIO: broadcast_update('order_update')
    SocketIO-->>Browser: Real-time status push
    Flask-->>Browser: {success: true, order_id}
```

### Database ER Diagram

```mermaid
erDiagram
    users ||--o{ restaurants : owns
    users ||--o{ orders : places
    users ||--o{ cart : has
    users ||--o{ reviews : writes
    users ||--o{ addresses : has
    users ||--o{ wishlist : has
    users ||--o{ notifications : receives
    users ||--o{ wallet_transactions : has
    users ||--o{ support_tickets : creates

    restaurants ||--o{ food_items : has
    restaurants ||--o{ orders : receives
    restaurants ||--o{ reviews : has

    orders ||--o{ order_items : contains
    orders ||--o{ order_status_history : tracks
    orders ||--|| payments : has

    food_items ||--o{ cart : in
    food_items ||--o{ order_items : in
    food_items ||--o{ wishlist : in

    users {
        int id PK
        string email
        string password_hash
        string role
        float wallet_balance
        string referral_code
    }
    restaurants {
        int id PK
        int owner_id FK
        string name
        string cuisine
        string location
        boolean is_approved
    }
    food_items {
        int id PK
        int restaurant_id FK
        string name
        float price
        string category
        boolean is_available
    }
    orders {
        int id PK
        int user_id FK
        int restaurant_id FK
        string status
        float total_amount
    }
    payments {
        int id PK
        int order_id FK
        string method
        string status
        string razorpay_order_id
        string gateway_signature
    }
```

---

## 📁 Project Structure

```
Grabbite/
│
├── app.py                    # App factory — config, extensions, blueprints, socket events
├── run.py                    # Entry point — dev server (Flask) or prod server (Waitress)
├── db.py                     # SQLAlchemy db instance (avoids circular imports)
├── extensions.py             # Shared extension objects (mail, limiter, socketio)
├── config.py                 # Config class
├── auth_routes.py            # Login, signup, logout, profile update
│
├── models/                   # SQLAlchemy database models (one file per domain)
│   ├── __init__.py           # Re-exports all classes — no import changes needed
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
├── blueprints/               # Flask blueprints (feature modules)
│   ├── __init__.py           # Registers and exports all blueprints
│   ├── public.py             # Public pages: home, restaurants, gallery, blogs, search
│   ├── account.py            # User account: profile, addresses, wishlist, notifications
│   ├── payment.py            # Checkout, Razorpay order creation & webhook
│   ├── admin/                # Admin panel blueprint (split by resource)
│   │   ├── __init__.py       # Registers admin sub-routes
│   │   ├── dashboard.py      # Live stats & charts
│   │   ├── users.py          # User management
│   │   ├── restaurants.py    # Restaurant approvals & management
│   │   ├── orders.py         # All orders view
│   │   ├── dishes.py         # Dish management across restaurants
│   │   ├── blogs.py          # Blog management
│   │   ├── offers.py         # Discount coupons & offers
│   │   ├── payments.py       # Payment records
│   │   ├── reviews.py        # Customer reviews
│   │   ├── support.py        # Support tickets
│   │   ├── notifications.py  # Admin notifications
│   │   ├── database.py       # Raw database viewer
│   │   └── exports.py        # Data export utilities
│   ├── api/                  # JSON API blueprint (split by resource)
│   │   ├── __init__.py       # Registers all /api/* endpoints
│   │   ├── cart.py           # Cart CRUD endpoints
│   │   ├── search.py         # Search across restaurants, dishes, blogs
│   │   ├── address.py        # Delivery address management
│   │   ├── coupon.py         # Coupon validation & application
│   │   ├── wishlist.py       # Wishlist add/remove
│   │   ├── reviews.py        # Review submission
│   │   ├── notifications.py  # Notification read/clear
│   │   └── misc.py           # Miscellaneous helpers
│   └── owner/                # Restaurant owner blueprint
│       ├── __init__.py
│       └── routes.py         # Owner dashboard, dish & order management
│
├── utils/                    # Shared utilities
│   ├── helpers.py            # Jinja2 template helpers, image URL resolver, safe_next_url
│   ├── mail.py               # Email functions (order confirm, password reset, welcome)
│   ├── decorators.py         # @admin_required, @owner_required decorators
│   ├── order_helpers.py      # _build_order_from_cart, _create_order_record
│   ├── razorpay_helpers.py   # HMAC signature verification, Razorpay client
│   ├── socket_events.py      # WebSocket room registration and broadcast_update
│   ├── uploads.py            # File validation (extension + magic-byte), resize, save
│   ├── tokens.py             # Password-reset token generation & verification
│   ├── seed_data.py          # Homepage showcase data seeder
│   ├── image_data.py         # Seed image URLs for restaurants & dishes
│   └── page_builders.py      # Heavy page-building logic extracted from blueprints
│
├── templates/                # Jinja2 HTML templates
│   ├── base.html             # Master layout (navbar, footer, cart drawer)
│   ├── index.html            # Homepage
│   ├── login.html            # Login page
│   ├── signup.html           # Customer registration
│   ├── signup_owner.html     # Restaurant owner registration
│   ├── restaurants.html      # Restaurant listing
│   ├── restaurant_menu.html  # Restaurant menu & dishes
│   ├── gallery.html          # Full dish catalogue
│   ├── dish_detail.html      # Individual dish detail
│   ├── cart.html             # Shopping cart
│   ├── checkout.html         # Checkout & address selection
│   ├── orders.html           # Order history
│   ├── profile.html          # User profile & settings
│   ├── address.html          # Address management
│   ├── wishlist.html         # Saved dishes
│   ├── notifications.html    # In-app notifications
│   ├── blogs.html            # Blog listing
│   ├── blog_detail.html      # Blog article
│   ├── search.html           # Search results
│   ├── payment_success.html  # Payment success confirmation
│   ├── payment_failed.html   # Payment failure page
│   ├── forgot_password.html  # Password reset request
│   ├── reset_password.html   # Password reset form
│   ├── about.html            # About page
│   ├── help.html             # Help & FAQ
│   ├── careers.html          # Careers page
│   ├── offer_details.html    # Offer detail
│   ├── database_viewer.html  # Raw DB viewer (admin)
│   ├── admin/                # Admin panel templates (18 files)
│   │   ├── base.html         # Admin layout
│   │   ├── dashboard.html    # Live stats dashboard
│   │   ├── users.html        # User management
│   │   ├── restaurants.html  # Restaurant management
│   │   ├── orders.html       # Orders overview
│   │   ├── dishes.html       # Dishes management
│   │   ├── blogs.html        # Blog management
│   │   ├── add_blog.html     # Add blog form
│   │   ├── edit_blog.html    # Edit blog form
│   │   ├── add_dish.html     # Add dish form
│   │   ├── edit_dish.html    # Edit dish form
│   │   ├── add_restaurant.html
│   │   ├── edit_restaurant.html
│   │   ├── offers.html       # Offers & coupons
│   │   ├── payments.html     # Payment records
│   │   ├── reviews.html      # Customer reviews
│   │   ├── support.html      # Support tickets
│   │   └── notifications.html
│   ├── owner/                # Restaurant owner templates (6 files)
│   │   ├── base.html         # Owner layout
│   │   ├── dashboard.html    # Owner dashboard
│   │   ├── dishes.html       # Dish listing
│   │   ├── dish_form.html    # Add/edit dish form
│   │   ├── orders.html       # Incoming orders
│   │   └── profile.html      # Owner profile
│   ├── emails/               # Transactional HTML email templates (6 files)
│   │   ├── order_confirmation.html
│   │   ├── order_status.html
│   │   ├── password_reset.html
│   │   ├── password_reset_success.html
│   │   ├── restaurant_approved.html
│   │   └── welcome.html
│   └── errors/               # HTTP error pages
│       ├── 404.html
│       └── 500.html          # (also 403.html)
│
├── static/                   # Static assets served directly
│   ├── css/                  # Stylesheets
│   │   ├── modern.css        # Primary custom styles
│   │   ├── style.css         # Base styles
│   │   ├── search.css        # Search page styles
│   │   └── offers.css        # Offers page styles
│   ├── js/                   # JavaScript files
│   ├── img/                  # Static images (placeholders, fallbacks)
│   └── uploads/              # User-uploaded files (profile photos, dish images)
│
├── assets/                   # Design & media assets
│   └── screenshots/          # App screenshots used in README
│
├── docs/                     # Supplementary documentation
│   └── DEPLOYMENT.md         # Full deployment guide (VPS, Docker, cloud)
│
├── migrations/               # Database migration files (Flask-Migrate / Alembic)
│
├── tests/                    # Test suite
│   └── test_smoke.py         # 15 smoke tests — auth, routing, JSON API, 404
│
├── scripts/
│   └── migrate_db.py         # Database initialisation & seed script
│
├── .github/
│   └── workflows/ci.yml      # GitHub Actions CI (Python 3.11 + 3.12)
│
├── .env.example              # All environment variables with explanations
├── .gitignore                # Git ignore rules
├── requirements.txt          # Production Python dependencies
├── requirements-dev.txt      # Dev/test dependencies (pytest, etc.)
├── pytest.ini                # Pytest configuration
├── LICENSE                   # MIT License
└── README.md                 # This file
```

---

## ✅ Prerequisites

- **Python 3.11+** — [Download](https://www.python.org/downloads/)
- **pip** — bundled with Python
- **Git** — [Download](https://git-scm.com/)
- **Terminal** — PowerShell (Windows) or Terminal (Mac/Linux)

> **No database server required** for local development. SQLite is used by default.

---

## ⚙️ Installation & Setup

### 1. Clone the Repository

```bash
git clone <repository-url>
cd Grabbite
```

### 2. Create a Virtual Environment

```bash
# Create
python -m venv .venv

# Activate — Windows (PowerShell)
.venv\Scripts\Activate.ps1

# Activate — Mac / Linux
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

```bash
# Windows
copy .env.example .env

# Mac / Linux
cp .env.example .env
```

Open `.env` and set at minimum:

```env
SECRET_KEY=your-random-secret-key-here
FLASK_ENV=development
FLASK_DEBUG=1
```

Generate a secure secret key:

```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

### 5. Initialise the Database

```bash
python scripts/migrate_db.py
```

This creates `instance/grabbite.db` with all 16 tables and seeds sample data.

### 6. Run the Application

```bash
python run.py
```

Open **http://localhost:5000** in your browser.

> **Dev admin account** — on first startup, credentials are printed to the terminal. In production, set `ADMIN_EMAIL` and `ADMIN_PASSWORD` in `.env`.

---

## 🔧 Environment Variables

Full documentation is in [`.env.example`](.env.example). Key variables:

| Variable                   | Required  | Description                                       |
| -------------------------- | --------- | ------------------------------------------------- |
| `SECRET_KEY`               | ✅ Always | Flask session encryption key                      |
| `FLASK_ENV`                | ✅ Always | `development` or `production`                     |
| `FLASK_DEBUG`              | dev only  | `1` to enable auto-reload and tracebacks          |
| `DATABASE_URL`             | prod      | Connection string — defaults to SQLite in dev     |
| `RAZORPAY_KEY_ID`          | payments  | Razorpay API key (COD works without it)           |
| `RAZORPAY_KEY_SECRET`      | payments  | Razorpay API secret                               |
| `RAZORPAY_WEBHOOK_SECRET`  | payments  | Webhook signing secret                            |
| `MAIL_SERVER`              | email     | SMTP server (leave blank to disable email)        |
| `MAIL_USERNAME`            | email     | SMTP username / Gmail address                     |
| `MAIL_PASSWORD`            | email     | SMTP password / Gmail App Password                |
| `ADMIN_EMAIL`              | prod      | Bootstrap admin email (production only)           |
| `ADMIN_PASSWORD`           | prod      | Bootstrap admin password (production only)        |
| `SOCKETIO_ALLOWED_ORIGINS` | prod      | Allowed WebSocket origins (comma-separated)       |
| `REDIS_URL`                | prod      | Redis URL for rate-limiter in multi-worker setups |

---

## 👥 User Roles

| Role                 | Access                                                                              |
| -------------------- | ----------------------------------------------------------------------------------- |
| **Customer**         | Browse restaurants, order food, manage cart / wishlist / profile, track orders      |
| **Restaurant Owner** | Manage their restaurant's dishes and incoming orders                                |
| **Admin**            | Full access to all users, restaurants, orders, payments, blogs, and system settings |

---

## 🔌 API Endpoints

### Public Pages

| Method | URL                | Description         |
| ------ | ------------------ | ------------------- |
| `GET`  | `/`                | Homepage            |
| `GET`  | `/restaurants`     | Restaurant listing  |
| `GET`  | `/restaurant/<id>` | Restaurant menu     |
| `GET`  | `/gallery`         | Full dish catalogue |
| `GET`  | `/dish/<id>`       | Dish detail         |
| `GET`  | `/blogs`           | Blog listing        |
| `GET`  | `/blog/<id>`       | Blog article        |
| `GET`  | `/search`          | Search results      |

### Authentication

| Method     | URL                       | Description                   |
| ---------- | ------------------------- | ----------------------------- |
| `GET/POST` | `/login`                  | Login                         |
| `GET/POST` | `/signup`                 | Customer registration         |
| `GET/POST` | `/signup/owner`           | Restaurant owner registration |
| `GET`      | `/logout`                 | Logout                        |
| `POST`     | `/forgot-password`        | Request password reset email  |
| `GET/POST` | `/reset-password/<token>` | Reset password via email link |

### Cart & Orders (JSON API)

| Method | URL                | Description                 |
| ------ | ------------------ | --------------------------- |
| `GET`  | `/api/cart`        | Get cart contents           |
| `POST` | `/api/cart/add`    | Add item to cart            |
| `POST` | `/api/cart/update` | Update item quantity        |
| `POST` | `/api/cart/remove` | Remove item from cart       |
| `POST` | `/api/cart/clear`  | Empty the cart              |
| `GET`  | `/api/cart/count`  | Cart item count (for badge) |
| `GET`  | `/api/orders`      | Order history               |

### Search & Discovery (JSON API)

| Method | URL                          | Description                       |
| ------ | ---------------------------- | --------------------------------- |
| `GET`  | `/api/search?q=query`        | Search restaurants, dishes, blogs |
| `GET`  | `/api/restaurants`           | Paginated restaurant list         |
| `GET`  | `/api/restaurants/<id>/menu` | Restaurant menu items             |

### Payments

| Method | URL                         | Description              |
| ------ | --------------------------- | ------------------------ |
| `GET`  | `/checkout`                 | Checkout page            |
| `POST` | `/api/payment/create-order` | Create Razorpay order    |
| `POST` | `/api/payment/verify`       | Verify payment signature |
| `POST` | `/api/payment/webhook`      | Razorpay webhook handler |
| `GET`  | `/payment/success`          | Payment success page     |
| `GET`  | `/payment/failed`           | Payment failed page      |

### Admin Panel (`/admin/`)

| URL                  | Description                              |
| -------------------- | ---------------------------------------- |
| `/admin/`            | Dashboard — stats, charts, recent orders |
| `/admin/users`       | User management                          |
| `/admin/restaurants` | Restaurant management & approvals        |
| `/admin/orders`      | All orders                               |
| `/admin/dishes`      | All dishes across restaurants            |
| `/admin/blogs`       | Blog post management                     |
| `/admin/offers`      | Discount coupons & offers                |
| `/admin/payments`    | Payment records                          |
| `/admin/reviews`     | Customer reviews                         |
| `/admin/support`     | Support tickets                          |
| `/admin/database`    | Raw database viewer                      |

### Health Probes

| Method | URL        | Description                              |
| ------ | ---------- | ---------------------------------------- |
| `GET`  | `/healthz` | Liveness probe — returns `200` if alive  |
| `GET`  | `/readyz`  | Readiness probe — checks DB connectivity |

---

## 🗄️ Database Schema

The database has **16 tables**:

| Table                  | Purpose                                                          |
| ---------------------- | ---------------------------------------------------------------- |
| `users`                | Customers, owners, admins — roles, wallet balance, referral code |
| `restaurants`          | Restaurant details, location, cuisine, approval status           |
| `food_items`           | Dishes belonging to restaurants — price, category, availability  |
| `cart`                 | Per-user cart items linked to food items                         |
| `orders`               | Placed orders with full status lifecycle                         |
| `order_items`          | Individual items within an order (snapshot at purchase time)     |
| `order_status_history` | Full audit trail of status changes with timestamps               |
| `payments`             | Payment records (method, status, Razorpay IDs, HMAC signature)   |
| `addresses`            | Multiple saved delivery addresses per user                       |
| `reviews`              | Restaurant ratings and comments (one per user per restaurant)    |
| `blogs`                | Blog posts with author, image, and content                       |
| `offers`               | Discount coupons — percentage or flat, min order, expiry         |
| `notifications`        | In-app notifications per user                                    |
| `wishlist`             | User-saved favourite food items                                  |
| `wallet_transactions`  | Wallet credit/debit history                                      |
| `support_tickets`      | Customer support requests                                        |

**Order lifecycle:** `placed` → `accepted` → `preparing` → `ready` → `picked` → `on_the_way` → `delivered` (or `cancelled` / `refunded`)

**Payment methods:** `cod` · `upi` · `card` · `wallet` · `netbanking`

---

## 🔐 Security

| Measure                 | Implementation                                               |
| ----------------------- | ------------------------------------------------------------ |
| **Password Hashing**    | Werkzeug `pbkdf2:sha256` — never stored in plaintext         |
| **Secure Sessions**     | HttpOnly, SameSite=Lax cookies; Secure flag in production    |
| **Session Protection**  | `strong` mode — rotates session on IP/user-agent change      |
| **Rate Limiting**       | Login, signup, password reset, and payment endpoints         |
| **CSRF Protection**     | Custom token validation on all state-changing POST requests  |
| **File Upload Safety**  | Filenames sanitised with `secure_filename`; magic-byte check; 16 MB size limit |
| **SQL Injection**       | SQLAlchemy ORM — all queries are parameterised               |
| **Password Reset**      | Time-limited (30 min), signed tokens via `itsdangerous`      |
| **Webhook Verification**| Razorpay webhooks verified with `HMAC-SHA256 + compare_digest` |
| **Secret Key Guard**    | App refuses to start in production without `SECRET_KEY`      |
| **Security Headers**    | `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `HSTS` (prod) |
| **Open Redirect Guard** | `safe_next_url()` validates `?next=` against same-origin before redirect |

---

## 📸 Screenshots

### App Preview

![App Preview](assets/screenshots/installation.gif)
_Animated walkthrough — Homepage → Login → Restaurants → Menu → Cart → Admin → Gallery_

### Homepage

![Homepage](assets/screenshots/homepage.png)

### Restaurant Listing

![Restaurants](assets/screenshots/restaurants.png)

### Restaurant Menu

![Menu](assets/screenshots/menu.png)

### Dish Gallery

![Gallery](assets/screenshots/gallery.png)

### Shopping Cart

![Cart](assets/screenshots/cart.png)

### Login Page

![Login](assets/screenshots/login.png)

### Admin Dashboard

![Admin](assets/screenshots/admin.png)

---

## 🚀 Deployment

Full instructions for VPS, Docker, and cloud platforms are in **[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)**.

### Quick Start (VPS)

### Option 1 — Traditional VPS (Ubuntu/Debian)

**1. Server setup**

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install python3 python3-pip python3-venv nginx -y

git clone <repository-url>
cd Grabbite

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**2. Configure environment**

```bash
cp .env.example .env
nano .env
```

Minimum production values:

```env
SECRET_KEY=<generate-a-64-byte-random-key>
FLASK_ENV=production
FLASK_DEBUG=0
DATABASE_URL=postgresql://user:password@localhost/grabbite
MAIL_SERVER=smtp.gmail.com
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
RAZORPAY_KEY_ID=your-key-id
RAZORPAY_KEY_SECRET=your-key-secret
ADMIN_EMAIL=admin@yourdomain.com
ADMIN_PASSWORD=<strong-password>
```

**3. Configure Nginx**

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static {
        alias /path/to/Grabbite/static;
    }

    location /socket.io {
        proxy_pass http://127.0.0.1:5000/socket.io;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/grabbite /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl restart nginx
```

**4. Systemd service**

```ini
# /etc/systemd/system/grabbite.service
[Unit]
Description=GrabBite Flask Application
After=network.target

[Service]
User=www-data
WorkingDirectory=/path/to/Grabbite
Environment="PATH=/path/to/Grabbite/.venv/bin"
ExecStart=/path/to/Grabbite/.venv/bin/python run.py
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now grabbite
```

**5. SSL with Let's Encrypt**

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

---

### Option 2 — Docker

```bash
# Build and start (app + PostgreSQL)
docker-compose up -d --build

# View logs
docker-compose logs -f web
```

The included `Dockerfile` and `docker-compose.yml` are ready to use. Set your secrets via environment variables or a `.env` file before starting.

---

### Option 3 — Cloud Platforms

| Platform    | Steps                                                                               |
| ----------- | ----------------------------------------------------------------------------------- |
| **Heroku**  | Add a `Procfile` with `web: python run.py`, attach Heroku Postgres, set config vars |
| **Railway** | Connect the GitHub repo, set env vars in the dashboard, auto-deploys on push        |
| **Render**  | Same as Railway — connect repo, set env vars, deploy                                |

---

### Production Checklist

- [ ] `SECRET_KEY` set to a random 64-byte value
- [ ] `FLASK_ENV=production`, `FLASK_DEBUG=0`
- [ ] `DATABASE_URL` pointing to PostgreSQL
- [ ] `ADMIN_EMAIL` and `ADMIN_PASSWORD` set
- [ ] HTTPS / SSL certificate configured
- [ ] SMTP credentials configured for emails
- [ ] Razorpay **live** keys set (not test keys)
- [ ] `RAZORPAY_WEBHOOK_SECRET` set and endpoint registered in Razorpay dashboard
- [ ] `SOCKETIO_ALLOWED_ORIGINS` restricted to your domain

---

## 🔮 Future Improvements

- **AI Recommendation Engine** — personalised dish and restaurant suggestions
- **Real-time Delivery Tracking** — live map view of the delivery agent
- **AI Chatbot** — order assistance and FAQs
- **Mobile App** — React Native / Flutter client
- **Multi-language Support** — i18n for regional languages
- **Content Security Policy** — strict CSP once inline scripts are moved to external files
- **Redis-backed Sessions** — for horizontal scaling across multiple Gunicorn workers

---

## 👤 Author

**Manav Baghel**

📧 [manavraj854@gmail.com](mailto:manavraj854@gmail.com)

---

## 🙏 Acknowledgements

- Design and UX inspired by [Zomato](https://www.zomato.com)
- Food images from [Pexels](https://www.pexels.com) and [Unsplash](https://www.unsplash.com) (free to use)
- [Bootstrap](https://getbootstrap.com) — responsive grid and UI components
- [Font Awesome](https://fontawesome.com) — icons
- [Flask](https://flask.palletsprojects.com) community — excellent documentation

---

_GrabBite — Bringing delicious food to your doorstep 🍕🍔🍜_

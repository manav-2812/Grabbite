# 🍽️ GrabBite — Food Ordering Web Application

<!-- CI badge -->

![CI](https://github.com/YOUR_USERNAME/Grabbite/actions/workflows/ci.yml/badge.svg)

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

GrabBite is a full-stack food ordering platform built with **Python (Flask)**. Customers can browse restaurants, explore menus, add dishes to a cart, and place orders online — with Razorpay payment integration, real-time order notifications via WebSockets, email confirmations, and a full admin panel.

---

## 📋 Table of Contents

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
    end

    subgraph "Web Server"
        B[Nginx / Gunicorn]
        C[Flask App]
    end

    subgraph "Application Layer"
        D[Blueprints]
        E[Auth Routes]
        F[Admin Routes]
        G[API Endpoints]
        H[Socket.IO Server]
    end

    subgraph "Data Layer"
        I[(SQLite / PostgreSQL)]
        J[Static Files]
        K[User Uploads]
    end

    subgraph "External Services"
        L[Razorpay API]
        M[SMTP Server]
    end

    A --> B
    B --> C
    C --> D & E & F & G & H
    D & E & F & G --> I
    H --> A
    G --> L
    E --> M
    C --> J & K
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
    }
```

---

## 📁 Project Structure

```
Grabbite/
│
├── app.py                    # App factory — config, extensions, blueprints, socket events
├── run.py                    # Entry point — dev server (Flask) or prod server (Waitress)
├── models.py                 # All SQLAlchemy database models (16 tables)
├── admin_routes.py           # Admin panel routes (/admin/*)
├── auth_routes.py            # Login, signup, logout, profile update
├── db.py                     # SQLAlchemy db instance (avoids circular imports)
├── extensions.py             # Shared extension objects (mail, limiter, socketio)
├── config.py                 # Config class
│
├── blueprints/               # Flask blueprints (feature modules)
│   ├── public.py             # Public pages: home, restaurants, gallery, blogs, search
│   ├── account.py            # User account: profile, addresses, wishlist, notifications
│   ├── payment.py            # Checkout, Razorpay order creation & webhook
│   ├── api_bp.py             # All /api/* JSON endpoints (cart, search, orders, etc.)
│   └── owner/
│       └── routes.py         # Restaurant owner dashboard routes
│
├── utils/                    # Shared utilities
│   ├── helpers.py            # Jinja2 template helpers, image URL resolver
│   ├── mail.py               # Email functions (order confirm, password reset, welcome)
│   └── decorators.py         # @admin_required, @owner_required decorators
│
├── templates/                # Jinja2 HTML templates
│   ├── base.html             # Master layout (navbar, footer, cart drawer)
│   ├── index.html            # Homepage
│   ├── admin/                # Admin panel templates
│   ├── owner/                # Restaurant owner templates
│   └── emails/               # Transactional HTML email templates
│
├── static/                   # Static assets served directly
│   ├── css/                  # Stylesheets (modern.css, style.css, etc.)
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
├── migrations/               # Database migration files (Flask-Migrate)
│
├── tests/                    # Test suite
│   └── test_smoke.py         # Smoke tests (15 tests)
│
├── scripts/
│   └── migrate_db.py         # Database migration helper script
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
| `payments`             | Payment records (method, status, Razorpay IDs)                   |
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
| **File Upload Safety**  | Filenames sanitised with `secure_filename`; 16 MB size limit |
| **SQL Injection**       | SQLAlchemy ORM — all queries are parameterised               |
| **Password Reset**      | Time-limited (30 min), signed tokens via `itsdangerous`      |
| **Secret Key Guard**    | App refuses to start in production without `SECRET_KEY`      |
| **Responsive Security** | Mobile-first; HTTPS auto-enforced in production config       |

---

## 📸 Screenshots

### App Preview

![App Preview](assets/screenshots/installation.gif)
_Animated walkthrough — Homepage → Login → Restaurants → Menu → Cart → Admin → Gallery_

---

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

---

## 🔮 Future Improvements

- **AI Recommendation Engine** — personalised dish and restaurant suggestions
- **Real-time Delivery Tracking** — live map view of the delivery agent
- **AI Chatbot** — order assistance and FAQs
- **Mobile App** — React Native / Flutter client
- **Multi-language Support** — i18n for regional languages

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

# GrabBite — API Reference

> **Base URL:** `https://your-domain.com` (or `http://localhost:8000` locally)
>
> **Content-Type:** All request bodies must be `application/json`.
>
> **Authentication:** Session-cookie based. Log in via `POST /login` to receive a session cookie. All protected endpoints require this cookie.
>
> **CSRF Protection:** Every state-changing request (`POST`, `PUT`, `DELETE`) must include a CSRF token via one of:
> - Header: `X-CSRF-Token: <token>`
> - JSON body field: `"_csrf": "<token>"`
> - Form field: `_csrf_token=<token>`
>
> Obtain the token from the `csrf_token()` Jinja2 helper, the `/login` page source, or any rendered HTML page that includes the meta tag `<meta name="csrf-token">`.
>
> **Webhook exception:** `POST /api/payment/webhook` is CSRF-exempt (uses HMAC verification instead).

---

## Response Format

All JSON API endpoints follow a consistent envelope:

```json
{
  "success": true,
  "message": "Human-readable status",
  "data":    { ... }
}
```

Error responses include an HTTP status code ≥ 400 and `"success": false`:

```json
{
  "success": false,
  "message": "Descriptive error message"
}
```

---

## Table of Contents

1. [Authentication](#1-authentication)
2. [Cart](#2-cart)
3. [Orders & Payments](#3-orders--payments)
4. [Search](#4-search)
5. [Address](#5-address)
6. [Wishlist](#6-wishlist)
7. [Reviews](#7-reviews)
8. [Notifications](#8-notifications)
9. [Utility](#9-utility)
10. [Health](#10-health)
11. [Error Codes](#11-error-codes)

---

## 1. Authentication

Authentication is session-based. On successful login the server sets a `session` cookie which must be sent with every subsequent request (browsers handle this automatically).

---

### POST /login

Authenticate a user and start a session.

**Auth required:** No

**Request**

```json
{
  "email":    "user@example.com",
  "password": "yourpassword",
  "remember": true
}
```

| Field      | Type    | Required | Description                              |
|------------|---------|----------|------------------------------------------|
| `email`    | string  | Yes      | Registered email address                 |
| `password` | string  | Yes      | Account password                         |
| `remember` | boolean | No       | Keep session alive for 30 days (default `false`) |

**Response — Success `302`**

Redirects to the appropriate dashboard (`/`, `/admin/`, or `/owner/dashboard`) depending on role. Session cookie is set.

**Response — Failure `302`**

Redirects back to `/login` with a flashed error message:

```
"Invalid email or password. Please try again."
"Your account has been deactivated. Please contact support."
```

---

### POST /signup

Register a new customer account.

**Auth required:** No

**Request (multipart/form-data)**

| Field              | Type   | Required | Description               |
|--------------------|--------|----------|---------------------------|
| `name`             | string | Yes      | Full name (min 2 chars)   |
| `email`            | string | Yes      | Email address             |
| `password`         | string | Yes      | Password (min 6 chars)    |
| `confirm_password` | string | Yes      | Must match `password`     |
| `contact`          | string | No       | Phone number              |
| `address`          | string | No       | Default address           |
| `profile_photo`    | file   | No       | Profile image (JPG/PNG)   |

**Response — Success `302`**

Redirects to `/` with a success flash message. Session is started immediately.

---

### POST /signup/restaurant

Register a new restaurant owner account and create their restaurant in one step.

**Auth required:** No

**Request (multipart/form-data)**

| Field                    | Type   | Required | Description                   |
|--------------------------|--------|----------|-------------------------------|
| `name`                   | string | Yes      | Owner full name               |
| `email`                  | string | Yes      | Email address                 |
| `password`               | string | Yes      | Password (min 6 chars)        |
| `confirm_password`       | string | Yes      | Must match `password`         |
| `contact`                | string | No       | Phone number                  |
| `restaurant_name`        | string | Yes      | Restaurant name               |
| `restaurant_location`    | string | Yes      | Restaurant location           |
| `cuisine_type`           | string | Yes      | Cuisine type                  |
| `restaurant_phone`       | string | No       | Restaurant phone              |
| `restaurant_description` | string | No       | Restaurant description        |
| `restaurant_image`       | file   | No       | Restaurant cover image        |

**Response — Success `302`**

Redirects to `/owner/dashboard`. Restaurant is created with `is_approved=false` — admin must approve before it appears publicly.

---

### GET /logout

End the current session.

**Auth required:** Yes

**Response `302`** — Redirects to `/` with a success flash message.

---

### POST /forgot-password

Request a password reset email.

**Auth required:** No

**Request**

```json
{
  "email": "user@example.com"
}
```

**Response `302`**

Always redirects back to `/forgot-password` with the message:

```
"If an account exists for that email, a password reset link has been sent."
```

> The response is deliberately ambiguous to prevent email enumeration.

---

### POST /reset-password/`<token>`

Set a new password using a signed reset token (valid for 30 minutes).

**Auth required:** No

**Request**

```json
{
  "password":         "newpassword123",
  "confirm_password": "newpassword123"
}
```

**Response — Success `302`** — Redirects to `/login`.

**Response — Failure `200`** — Re-renders the reset form with an error if the token has expired or passwords don't match.

---

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

## 2. Cart

All cart endpoints require an active session (except `/api/cart/count`).

---

### GET /api/cart/count

Returns the number of distinct items in the current user's cart. Safe to call unauthenticated — returns `0` instead of an error.

**Auth required:** No

**Response `200`**
```json
{
  "count": 3
}
```

---

### GET /api/cart

Return the full cart with per-item details and a pricing summary.

**Auth required:** Yes

**Response `200`**
```json
{
  "success": true,
  "items": [
    {
      "cart_id":         12,
      "food_id":         45,
      "food_name":       "Butter Chicken",
      "restaurant_id":   3,
      "restaurant_name": "Spice Paradise",
      "price":           320.0,
      "quantity":        2,
      "notes":           "Extra spicy",
      "image":           "butter_chicken.jpg",
      "item_total":      640.0
    }
  ],
  "summary": {
    "subtotal":     640.0,
    "tax":          115.2,
    "delivery_fee": 0.0,
    "total":        755.2,
    "count":        1
  }
}
```

> Delivery fee is **₹40** for orders ≤ ₹500 and **₹0** for orders > ₹500. Tax is 18% of subtotal.

---

### POST /api/cart/add

Add a food item to the cart. If the item is already in the cart, quantity is incremented.

**Auth required:** Yes

**Request**
```json
{
  "food_item_id": 45,
  "quantity":     2,
  "notes":        "Extra spicy"
}
```

| Field          | Type    | Required | Description                        |
|----------------|---------|----------|------------------------------------|
| `food_item_id` | integer | Yes      | ID of the food item to add         |
| `quantity`     | integer | No       | Units to add (default `1`, min `1`)|
| `notes`        | string  | No       | Special instructions               |

**Response `200`**
```json
{
  "success":    true,
  "message":    "Butter Chicken added to cart!",
  "cart_count": 3
}
```

**Error `401`** — User not authenticated
```json
{
  "success":  false,
  "message":  "Please login to add items to cart",
  "redirect": "/login"
}
```

**Error `400`** — Item unavailable or missing `food_item_id`
```json
{ "success": false, "message": "This item is currently unavailable" }
```

---

### POST /api/cart/update

Update the quantity of an existing cart item.

**Auth required:** Yes

**Request**
```json
{
  "cart_id":  12,
  "quantity": 3
}
```

**Response `200`**
```json
{
  "success":    true,
  "message":    "Cart updated",
  "item_total": 960.0,
  "summary": {
    "subtotal":     960.0,
    "tax":          172.8,
    "delivery_fee": 0.0,
    "total":        1132.8
  }
}
```

---

### POST /api/cart/remove

Remove a single item from the cart.

**Auth required:** Yes

**Request**
```json
{ "cart_id": 12 }
```

**Response `200`**
```json
{
  "success":    true,
  "message":    "Item removed",
  "cart_count": 2
}
```

---

### POST /api/cart/clear

Remove all items from the cart.

**Auth required:** Yes

**Request** — No body required.

**Response `200`**
```json
{ "success": true, "message": "Cart cleared" }
```

---

## 3. Orders & Payments

---

### POST /api/payment/cod

Place a **Cash on Delivery** order from the current cart. The cart is cleared on success.

**Auth required:** Yes

**Request**
```json
{
  "delivery_address": "42 Marine Drive, Mumbai 400001",
  "delivery_phone":   "9876543210",
  "coupon_code":      "SAVE50",
  "notes":            "Ring the doorbell twice"
}
```

| Field              | Type   | Required | Description                          |
|--------------------|--------|----------|--------------------------------------|
| `delivery_address` | string | Yes      | Full delivery address (min 5 chars)  |
| `delivery_phone`   | string | Yes      | Contact phone number                 |
| `coupon_code`      | string | No       | Discount coupon code                 |
| `notes`            | string | No       | Delivery instructions (max 1000 chars) |

**Response `200`**
```json
{
  "success":  true,
  "order_id": 37,
  "redirect": "/payment/success/37"
}
```

**Error `400`**
```json
{ "success": false, "message": "Your cart is empty" }
{ "success": false, "message": "Delivery address and phone required" }
{ "success": false, "message": "Delivery address looks too short." }
```

---

### POST /api/payment/create-razorpay-order

Initiate an **online payment** (UPI / card / net banking). Creates a Razorpay order and a pending GrabBite order. Returns gateway details for the frontend to open the Razorpay checkout modal.

**Auth required:** Yes

**Request**
```json
{
  "delivery_address":  "42 Marine Drive, Mumbai 400001",
  "delivery_phone":    "9876543210",
  "payment_method":    "upi",
  "coupon_code":       "SAVE50"
}
```

| Field              | Type   | Required | Description                                       |
|--------------------|--------|----------|---------------------------------------------------|
| `delivery_address` | string | Yes      | Full delivery address                             |
| `delivery_phone`   | string | Yes      | Contact number                                    |
| `payment_method`   | string | No       | `upi` / `card` / `netbanking` (default `upi`)     |
| `coupon_code`      | string | No       | Discount coupon code                              |

**Response `200`**
```json
{
  "success":           true,
  "razorpay_key":      "rzp_live_xxxxxxxxxxxx",
  "razorpay_order_id": "order_PQR123456789",
  "amount":            75520,
  "currency":          "INR",
  "order_id":          37,
  "prefill": {
    "name":    "Ravi Kumar",
    "email":   "ravi@example.com",
    "contact": "9876543210"
  }
}
```

> `amount` is in **paise** (÷ 100 for rupees). Pass `razorpay_order_id` and `amount` directly to `Razorpay.checkout.open()`.

**Error `400`** — Razorpay not configured
```json
{
  "success":      false,
  "message":      "Online payments not configured. Please use Cash on Delivery.",
  "fallback_cod": true
}
```

---

### POST /api/payment/verify

Verify the Razorpay HMAC-SHA256 payment signature after the user completes checkout. Marks the order as paid and clears the cart.

**Auth required:** Yes  
**CSRF required:** No (payment verification flow)

**Request**
```json
{
  "razorpay_order_id":   "order_PQR123456789",
  "razorpay_payment_id": "pay_ABC987654321",
  "razorpay_signature":  "3d8f2b1e...",
  "order_id":            37
}
```

**Response `200`**
```json
{
  "success":  true,
  "order_id": 37,
  "redirect": "/payment/success/37"
}
```

**Error `400`** — Signature mismatch
```json
{ "success": false, "message": "Payment verification failed" }
```

**Error `400`** — Missing fields
```json
{ "success": false, "message": "Incomplete payment data" }
```

---

### POST /api/payment/webhook

Razorpay server-to-server webhook for asynchronous payment events. Signature verified via `X-Razorpay-Signature` header (HMAC-SHA256 of raw body using `RAZORPAY_WEBHOOK_SECRET`).

**Auth required:** No  
**CSRF required:** No (HMAC-verified)

**Headers**
```
X-Razorpay-Signature: <hmac-sha256-signature>
Content-Type: application/json
```

**Supported events**

| Event               | Action                                          |
|---------------------|-------------------------------------------------|
| `payment.captured`  | Sets `order.payment_status = 'paid'`            |
| `payment.failed`    | Sets `order.payment_status = 'failed'`          |
| Other events        | Ignored — returns `200 {"status":"ok"}`         |

**Response `200`**
```json
{ "status": "ok" }
```

**Error `400`** — Invalid signature
```json
{ "error": "Invalid signature" }
```

---

### GET /api/orders/`<id>`/status

Return the current tracking status, full status history, and stepper pipeline for an order.

**Auth required:** Yes (must own the order)

**Response `200`**
```json
{
  "success":         true,
  "order_id":        37,
  "status":          "preparing",
  "status_label":    "Preparing",
  "status_desc":     "Your food is being freshly prepared.",
  "is_done":         false,
  "estimated_time":  30,
  "restaurant_name": "Spice Paradise",
  "total_amount":    755.2,
  "payment_method":  "cod",
  "payment_status":  "pending",
  "delivered_at":    null,
  "created_at":      "06 Jul 2026, 02:30 PM",
  "steps": [
    { "status": "placed",     "label": "Order Placed",    "icon": "fa-receipt",      "color": "#f59e0b", "done": true,  "active": false },
    { "status": "accepted",   "label": "Accepted",        "icon": "fa-check-circle", "color": "#3b82f6", "done": true,  "active": false },
    { "status": "preparing",  "label": "Preparing",       "icon": "fa-fire-burner",  "color": "#8b5cf6", "done": false, "active": true  },
    { "status": "ready",      "label": "Ready for Pickup","icon": "fa-bag-shopping", "color": "#06b6d4", "done": false, "active": false },
    { "status": "on_the_way", "label": "Out for Delivery","icon": "fa-motorcycle",   "color": "#10b981", "done": false, "active": false },
    { "status": "delivered",  "label": "Delivered",       "icon": "fa-circle-check", "color": "#16a34a", "done": false, "active": false }
  ],
  "history": [
    { "status": "placed",    "label": "Order Placed", "note": "Order placed by customer", "timestamp": "06 Jul 2026, 02:30 PM", "ts_iso": "2026-07-06T14:30:00" },
    { "status": "accepted",  "label": "Accepted",     "note": "Status updated by restaurant owner", "timestamp": "06 Jul 2026, 02:33 PM", "ts_iso": "2026-07-06T14:33:00" },
    { "status": "preparing", "label": "Preparing",    "note": "Status updated by restaurant owner", "timestamp": "06 Jul 2026, 02:35 PM", "ts_iso": "2026-07-06T14:35:00" }
  ]
}
```

**Order status lifecycle**

```
placed → accepted → preparing → ready → picked → on_the_way → delivered
                                                              ↘ cancelled
```

---

## 4. Search

---

### GET /api/home-search

Global search across restaurants, dishes, and blogs simultaneously. Used by the homepage search bar.

**Auth required:** No

**Query parameters**

| Parameter | Type   | Required | Description              |
|-----------|--------|----------|--------------------------|
| `q`       | string | Yes      | Search query (min 2 chars) |

**Example**
```
GET /api/home-search?q=biryani
```

**Response `200`**
```json
{
  "success":     true,
  "query":       "biryani",
  "total":       8,
  "restaurants": [
    {
      "id": 5, "name": "Biryani By Kilo", "cuisine": "Biryani, North Indian",
      "location": "Marathahalli, Bengaluru", "rating": 4.8,
      "image": "restaurant.jpg", "delivery_time": 40,
      "url": "/restaurant/5"
    }
  ],
  "dishes": [
    {
      "id": 23, "name": "Hyderabadi Chicken Biryani", "price": 499.0,
      "category": "Biryani", "restaurant_id": 5,
      "restaurant_name": "Biryani By Kilo",
      "image": "biryani.jpg", "url": "/restaurant/5"
    }
  ],
  "blogs": [
    {
      "id": 2, "title": "Best Biryani Styles Across India",
      "author": "GrabBite Editorial", "excerpt": "From Hyderabadi dum...",
      "image": "blog.jpg", "url": "/blog/2"
    }
  ]
}
```

**Error `400`** — Query too short
```json
{ "success": false, "message": "Please enter at least 2 characters", "restaurants": [], "dishes": [], "blogs": [] }
```

---

### GET /api/search

Paginated search filtered by type. Used by the `/search` page.

**Auth required:** No

**Query parameters**

| Parameter  | Type    | Required | Description                                      |
|------------|---------|----------|--------------------------------------------------|
| `q`        | string  | Yes      | Search query (min 2 chars)                       |
| `type`     | string  | No       | `all` / `restaurants` / `food` / `blogs` (default `all`) |
| `per_page` | integer | No       | Results per type, max 50 (default `10`)          |

**Example**
```
GET /api/search?q=pizza&type=food&per_page=5
```

**Response `200`**
```json
{
  "success": true,
  "query":   "pizza",
  "count":   3,
  "results": [
    {
      "type":            "food",
      "id":              12,
      "name":            "Farmhouse Feast Pizza",
      "restaurant_id":   1,
      "restaurant_name": "Domino's",
      "price":           399.0,
      "image":           "pizza.jpg",
      "category":        "Pizza",
      "is_available":    true,
      "url":             "/restaurant/1"
    }
  ]
}
```

---

### GET /api/search/suggestions

Lightweight typeahead suggestions for the search input.

**Auth required:** No

**Query parameters**

| Parameter | Type    | Required | Description                         |
|-----------|---------|----------|-------------------------------------|
| `q`       | string  | Yes      | Partial query (min 2 chars)         |
| `limit`   | integer | No       | Max results (default `5`)           |

**Response `200`**
```json
{
  "success": true,
  "suggestions": [
    { "type": "restaurant", "text": "Biryani By Kilo", "value": "Biryani By Kilo" },
    { "type": "food",       "text": "Butter Chicken",  "value": "Butter Chicken"  }
  ]
}
```

---

## 5. Address

---

### POST /api/address/add

Save a new delivery address for the authenticated user.

**Auth required:** Yes

**Request**
```json
{
  "label":        "Home",
  "full_address": "42 Marine Drive, Nariman Point",
  "city":         "Mumbai",
  "state":        "Maharashtra",
  "pincode":      "400001",
  "landmark":     "Near NCPA",
  "is_default":   true
}
```

| Field          | Type    | Required | Description                              |
|----------------|---------|----------|------------------------------------------|
| `label`        | string  | No       | Address label (`Home`, `Work`, etc.) — default `Home` |
| `full_address` | string  | Yes      | Complete address string                  |
| `city`         | string  | No       | City name                                |
| `state`        | string  | No       | State name                               |
| `pincode`      | string  | No       | PIN / ZIP code                           |
| `landmark`     | string  | No       | Nearby landmark                          |
| `is_default`   | boolean | No       | Set as default address (clears existing default) |

**Response `200`**
```json
{ "success": true, "message": "Address saved", "id": 8 }
```

---

### DELETE /api/address/`<id>`

Delete a saved address.

**Auth required:** Yes

**Response `200`**
```json
{ "success": true, "message": "Address deleted" }
```

**Error `404`**
```json
{ "success": false, "message": "Address not found" }
```

---

## 6. Wishlist

---

### POST /api/wishlist/toggle

Add or remove a restaurant from the authenticated user's wishlist. Calling the endpoint twice on the same restaurant toggles it off.

**Auth required:** Yes

**Request**
```json
{ "restaurant_id": 5 }
```

**Response `200` — Added**
```json
{ "success": true, "wishlisted": true,  "message": "Added to wishlist" }
```

**Response `200` — Removed**
```json
{ "success": true, "wishlisted": false, "message": "Removed from wishlist" }
```

**Error `400`**
```json
{ "success": false, "message": "restaurant_id required" }
```

---

## 7. Reviews

---

### POST /api/review

Submit or update a review for a restaurant. One review per user per restaurant — submitting again updates the existing review.

**Auth required:** Yes

**Request**
```json
{
  "restaurant_id": 5,
  "rating":        4,
  "comment":       "Great biryani, fast delivery!"
}
```

| Field           | Type    | Required | Description            |
|-----------------|---------|----------|------------------------|
| `restaurant_id` | integer | Yes      | Target restaurant ID   |
| `rating`        | integer | Yes      | Score from `1` to `5`  |
| `comment`       | string  | No       | Review text            |

**Response `200`**
```json
{ "success": true, "message": "Review submitted!" }
```

**Error `400`**
```json
{ "success": false, "message": "Rating must be 1–5" }
```

---

### GET /api/reviews/restaurant/`<id>`

Fetch paginated reviews for a restaurant.

**Auth required:** No

**Query parameters**

| Parameter | Type    | Required | Description              |
|-----------|---------|----------|--------------------------|
| `page`    | integer | No       | Page number (default `1`, 10 results per page) |

**Response `200`**
```json
{
  "success":  true,
  "total":    42,
  "has_next": true,
  "has_prev": false,
  "reviews": [
    {
      "id":         7,
      "rating":     5,
      "comment":    "Best butter chicken in the city!",
      "user_name":  "Ravi K.",
      "created_at": "July 06, 2026"
    }
  ]
}
```

---

## 8. Notifications

---

### GET /api/notifications

Return the authenticated user's notifications (most recent first, max 30).

**Auth required:** Yes

**Query parameters**

| Parameter    | Type | Required | Description                         |
|--------------|------|----------|-------------------------------------|
| `unread_only`| `1`  | No       | If `1`, return only unread items    |

**Response `200`**
```json
{
  "success":      true,
  "unread_count": 2,
  "notifications": [
    {
      "id":         14,
      "title":      "Order Accepted! 🎉",
      "message":    "Restaurant accepted your order #37.",
      "type":       "order_update",
      "link":       "/orders",
      "is_read":    false,
      "created_at": "2026-07-06T14:33:00+00:00"
    }
  ]
}
```

**Notification types:** `order_update` · `promo` · `general` · `system`

---

### POST /api/notifications/read

Mark a single notification as read.

**Auth required:** Yes

**Request**
```json
{ "id": 14 }
```

**Response `200`**
```json
{ "success": true }
```

---

### POST /api/notifications/read-all

Mark all notifications for the authenticated user as read.

**Auth required:** Yes

**Request** — No body required.

**Response `200`**
```json
{ "success": true }
```

---

## 9. Coupon

---

### POST /api/coupon/apply

Validate a coupon code against the current cart total and return the discount amount if applicable.

**Auth required:** Yes

**Request**
```json
{
  "code":       "SAVE50",
  "cart_total": 640.0
}
```

| Field        | Type   | Required | Description              |
|--------------|--------|----------|--------------------------|
| `code`       | string | Yes      | Coupon code (case-insensitive) |
| `cart_total` | number | Yes      | Current cart subtotal in ₹ |

**Response `200`**
```json
{
  "success":        true,
  "message":        "Coupon applied! You save ₹50.00",
  "discount":       50.0,
  "discount_type":  "flat",
  "discount_value": 50.0,
  "code":           "SAVE50"
}
```

**Error `404`** — Unknown code
```json
{ "success": false, "message": "Invalid coupon code" }
```

**Error `400`** — Already used
```json
{ "success": false, "message": "You have already used this coupon" }
```

**Error `400`** — Below minimum order
```json
{ "success": false, "message": "Min order ₹299 required for this coupon" }
```

---

## 10. Utility

---

### POST /api/newsletter/subscribe

Subscribe an email address to the GrabBite newsletter.

**Auth required:** No

**Request**
```json
{ "email": "user@example.com" }
```

**Response `200`**
```json
{ "success": true, "message": "Subscribed! Welcome to the GrabBite family 🎉" }
```

**Error `400`**
```json
{ "success": false, "message": "Please enter a valid email address." }
```

---

## 11. Health

---

### GET /healthz

Liveness probe — confirms the process is alive. Always returns `200`.

**Auth required:** No

**Response `200`**
```json
{ "status": "ok" }
```

---

### GET /readyz

Readiness probe — verifies database connectivity. Used by Docker / Railway health checks.

**Auth required:** No

**Response `200`** — DB reachable
```json
{ "status": "ready", "db": "ok" }
```

**Response `503`** — DB unreachable
```json
{ "status": "not_ready", "db": "error" }
```

---

## 12. Error Codes

| HTTP Status | Meaning                                                    |
|-------------|------------------------------------------------------------|
| `200`       | Success                                                    |
| `302`       | Redirect (auth pages use HTML redirects, not JSON)         |
| `400`       | Bad request — validation error, missing field, or business rule violation |
| `401`       | Unauthenticated — session cookie missing or expired        |
| `403`       | Forbidden — authenticated but not authorised (wrong role, CSRF failure) |
| `404`       | Resource not found                                         |
| `500`       | Internal server error — unexpected exception               |
| `503`       | Service unavailable — DB down or webhook not configured    |

### Common error bodies

```json
{ "success": false, "message": "CSRF token missing or invalid" }
{ "success": false, "message": "Cart item not found" }
{ "success": false, "message": "Order not found" }
{ "success": false, "message": "Restaurant not found" }
```

---

## WebSocket Events

GrabBite uses **Flask-SocketIO** for real-time order updates. Connect via the Socket.IO client library.

### Connection

```js
const socket = io("https://your-domain.com", {
  transports: ["websocket", "polling"]
});
```

Authenticated users are automatically placed in the `authenticated_users` room on connect. Admins are additionally placed in the `admin_users` room.

### Incoming event: `real_time_update`

Emitted to `authenticated_users` when an order status changes.

```js
socket.on("real_time_update", (msg) => {
  // msg.type    → "order_update"
  // msg.data    → { order_id, status, message }
  // msg.timestamp → ISO 8601 string
  console.log(msg);
});
```

**Example payload**
```json
{
  "type": "order_update",
  "data": {
    "order_id": 37,
    "status":   "on_the_way",
    "message":  "Order #37 is on the way."
  },
  "timestamp": "2026-07-06T14:50:00+00:00"
}
```

When this event fires, call `GET /api/orders/<id>/status` to get the full updated state.

---

*Last updated: July 2026 · GrabBite v2.0*

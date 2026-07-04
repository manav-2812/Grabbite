# Changelog

All notable changes to GrabBite will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial release of GrabBite food ordering platform
- User authentication system (login, signup, password reset)
- Restaurant browsing and discovery
- Food item gallery with category filtering
- Shopping cart with persistent database storage
- Order placement and tracking system
- Multiple payment methods (COD, Razorpay UPI, cards, wallet)
- Real-time order notifications via WebSockets
- Restaurant owner dashboard
- Full admin panel with user/restaurant/order management
- Blog system with articles and categories
- Customer reviews and ratings
- Wishlist functionality
- Multiple address management
- Wallet system with transaction history
- Coupon and offer system
- Support ticket system
- Email notifications for orders and password resets
- Responsive mobile-first design
- Search functionality across restaurants, dishes, and blogs

### Security
- Password hashing with pbkdf2:sha256
- CSRF protection on state-changing requests
- Rate limiting on sensitive endpoints
- Secure file upload handling
- Session protection with HttpOnly cookies
- SQL injection prevention via SQLAlchemy ORM

## [1.0.0] - 2024-06-26

### Added
- Initial public release
- Complete food ordering platform
- Full documentation

---

**Note:** Version numbers follow MAJOR.MINOR.PATCH format:
- MAJOR: Incompatible API changes
- MINOR: New functionality (backwards compatible)
- PATCH: Bug fixes (backwards compatible)

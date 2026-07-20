# Changelog

All notable changes to GrabBite will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.1.0] - 2026-07-20 — Responsive Dark Mode & UX Refinement

### Added
- **Full Dark Mode**: High-contrast, premium dark theme support integrated across the entire platform.
- **User Preference Memory**: Persistent theme selection stored in `localStorage` with a fast-loading head script to prevent flash-of-unstyled-content.
- **Enhanced Responsive Design**: Optimized layouts and responsive controls specifically tailored for mobile and tablet viewports.

### Fixed
- **Theme Rendering Bugs**: Neutralized hardcoded inline light backgrounds on home, gallery, blogs, cart, and restaurant search bars.
- **Bootstrap Widget Overrides**: Resolved visual layout errors on Accordions, Modals, Forms, Tables, and List Groups under dark mode.
- **Eventlet Startup Deprecation**: Silenced console deprecation warning logs from the Eventlet concurrent library during server boot.

### Refined
- **Seamless User Experience**: Enhanced typography contrast, card elevations, hover states, and navigation transitions for a cleaner checkout and discovery flow.

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

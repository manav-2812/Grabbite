# Contributing to GrabBite

Thank you for your interest in contributing to GrabBite! We welcome contributions from the community.

## How to Contribute

### Reporting Bugs

Before creating bug reports, please check the existing issues to avoid duplicates. When creating a bug report, include:

- **Clear description** of the problem
- **Steps to reproduce** the issue
- **Expected behavior** vs **actual behavior**
- **Screenshots** if applicable
- **Environment details** (OS, Python version, browser)
- **Error logs** or stack traces

### Suggesting Enhancements

Enhancement suggestions are welcome! Please:

- Use a clear and descriptive title
- Provide a detailed description of the proposed enhancement
- Explain why this enhancement would be useful
- Include examples if applicable

### Pull Requests

1. **Fork the repository** and create your branch from `main`
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** following the code style guidelines

3. **Test your changes** thoroughly
   - Run the application locally
   - Test all affected features
   - Ensure no existing tests are broken

4. **Commit your changes** with clear messages
   ```bash
   git commit -m "feat: add user profile photo upload"
   ```

5. **Push to your fork** and create a Pull Request

## Development Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/Grabbite.git
   cd Grabbite
   ```

2. Create a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Mac/Linux
   .venv\Scripts\Activate.ps1  # Windows
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure environment:
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

5. Initialize database:
   ```bash
   python scripts/migrate_db.py
   ```

6. Run the application:
   ```bash
   python run.py
   ```

## Code Style Guidelines

### Python Code
- Follow PEP 8 style guidelines
- Use meaningful variable and function names
- Add docstrings to functions and classes
- Keep functions focused and concise
- Maximum line length: 100 characters

### HTML/Jinja2 Templates
- Use 4 spaces for indentation
- Close all tags properly
- Use template inheritance via `base.html`
- Keep templates DRY (Don't Repeat Yourself)

### CSS
- Use BEM naming convention for classes
- Group related styles
- Use CSS variables for colors and spacing
- Ensure responsive design

### JavaScript
- Use ES6+ syntax
- Add JSDoc comments for functions
- Handle errors gracefully
- Avoid global namespace pollution

## Commit Message Convention

We follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `style:` Code style changes (formatting, etc.)
- `refactor:` Code refactoring
- `test:` Adding or updating tests
- `chore:` Maintenance tasks

Examples:
```
feat: add restaurant search by cuisine
fix: resolve cart quantity update bug
docs: update README with deployment instructions
```

## Project Structure

- `app.py` - Main application factory
- `models/` - Database models package (one file per domain)
  - `__init__.py` — re-exports all classes; no import changes needed elsewhere
  - `user.py` — `User`, `Address`
  - `restaurant.py` — `Restaurant`, `FoodItem`
  - `order.py` — `Cart`, `Order`, `OrderItem`, `OrderStatusHistory`
  - `payment.py` — `Payment`, `WalletTransaction`
  - `offer.py` — `Offer`, `CouponUsage`
  - `blog.py` — `Blog`
  - `review.py` — `Review`
  - `notification.py` — `Notification`, `AdminNotification`
  - `support.py` — `SupportTicket`
  - `wishlist.py` — `Wishlist`
  - `admin.py` — `AdminActivity`
  - `constants.py` — shared enums (`ROLES`, `ORDER_STATUSES`, etc.)
- `blueprints/` - Route modules organized by feature
- `templates/` - HTML/Jinja2 templates
- `static/` - CSS, JS, and static assets
- `utils/` - Helper functions and decorators
- `scripts/` - Utility scripts

## Testing

Before submitting a PR, ensure:
- [ ] Application runs without errors
- [ ] New features work as expected
- [ ] Existing features are not broken
- [ ] Code follows style guidelines
- [ ] Commit messages are clear

## Questions?

Feel free to open an issue for any questions about contributing or the project structure.

---

**Happy contributing! 🍕**

# Security Policy

## Supported Versions

| Version | Supported          |
|---------|--------------------|
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

If you discover a security vulnerability, please report it responsibly.

### How to Report

**Do NOT** open a public issue for security vulnerabilities.

Instead, please send an email to: **security@grabbite.com**

Include the following information:
- Description of the vulnerability
- Steps to reproduce the issue
- Potential impact of the vulnerability
- Suggested fix (if known)

### Response Timeline

- **Initial response**: Within 48 hours
- **Detailed investigation**: Within 7 days
- **Fix and patch**: Based on severity and complexity
- **Public disclosure**: After fix is deployed

### What to Expect

1. We will acknowledge receipt of your report
2. We will investigate the vulnerability
3. We will work on a fix
4. We will coordinate disclosure with you
5. We will credit you in the release notes (if desired)

## Security Best Practices

### For Developers

- **Never commit secrets** - Use environment variables for sensitive data
- **Keep dependencies updated** - Regularly run `pip install --upgrade`
- **Review code changes** - Peer review all security-related changes
- **Use strong passwords** - For database and API keys
- **Enable HTTPS** - In production environments
- **Validate all inputs** - Sanitize user data
- **Implement rate limiting** - On authentication and API endpoints
- **Monitor logs** - For suspicious activity

### For Users

- **Use strong passwords** - Minimum 8 characters, mix of letters, numbers, symbols
- **Enable 2FA** - When available
- **Keep software updated** - Use the latest version
- **Don't share credentials** - Protect your login information
- **Report suspicious activity** - If you notice anything unusual

## Known Security Considerations

### Current Implementation

- **Passwords**: Hashed using Werkzeug's pbkdf2:sha256
- **Sessions**: HttpOnly, SameSite=Lax cookies
- **CSRF**: Custom token validation on POST requests
- **File Uploads**: Sanitized filenames, 16MB size limit
- **SQL Injection**: Prevented via SQLAlchemy ORM
- **Rate Limiting**: Applied to login, signup, and payment endpoints
- **Payment**: Razorpay handles sensitive payment data

### Recommendations for Production

1. **Use PostgreSQL** instead of SQLite for production
2. **Enable HTTPS** with valid SSL certificate
3. **Set up firewall rules** to restrict database access
4. **Regular backups** of the database
5. **Monitor for suspicious activity** in logs
6. **Keep dependencies updated** regularly
7. **Use environment-specific configurations**
8. **Implement proper logging** for security events

## Dependency Security

We regularly audit our dependencies. To check for vulnerabilities:

```bash
pip install safety
safety check
```

Update dependencies:
```bash
pip install --upgrade -r requirements.txt
```

## Security Headers

The application implements the following security headers in production:

- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`
- `Strict-Transport-Security: max-age=31536000; includeSubDomains`

## Data Protection

- **User Data**: Stored securely in database
- **Passwords**: Never stored in plaintext
- **Payment Data**: Handled by Razorpay, never stored directly
- **Uploads**: Validated and stored in designated directory
- **Logs**: Do not contain sensitive user information

## Contact

For security-related questions not involving vulnerability reports:
- Email: security@grabbite.com
- GitHub Issues: Use the `security` label

---

Thank you for helping keep GrabBite secure! 🔒

## 2024-05-10 - Secure Refresh Token Cookies
**Vulnerability:** Refresh tokens were being set as cookies with `secure=False` indiscriminately, meaning they could be intercepted over unencrypted HTTP connections in production.
**Learning:** Hardcoding `secure=False` for local development convenience leads to vulnerabilities when deployed. The application needs a reliable way to differentiate environments for security settings.
**Prevention:** Always use environment-aware configurations for security-sensitive flags. Cookies containing authentication tokens should dynamically check `settings.app_env == "production"` to ensure `secure=True` in production while permitting HTTP for local development.

## 2024-05-14 - Fix Hardcoded Insecure Cookie Flag

**Vulnerability:** The `refresh_token` cookie was being set with `secure=False` explicitly in the `backend/app/api/v1/auth.py` file, both during the login process and the token refresh process.

**Learning:** This exposes the application to security risks by allowing the sensitive refresh token cookie to be transmitted over unencrypted HTTP connections. Setting `settings.app_env == "production"` might throw an `AttributeError` if `app_env` isn't fully defined during runtime access. Always use `getattr(settings, "app_env", "development")` or verify `settings` attributes explicitly.

**Prevention:** Always make the `secure` flag dynamic by checking the environment, using something like `is_secure = getattr(settings, "app_env", "development") == "production"` to ensure cookies are sent securely over HTTPS in production and to avoid potential app crashes if properties are missing.

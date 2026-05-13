## 2024-05-13 - [CRITICAL] Fix insecure database SSL configuration
**Vulnerability:** The database connection was configured with `_ssl_ctx.check_hostname = False` and `_ssl_ctx.verify_mode = ssl.CERT_NONE` by default, making connections vulnerable to MITM attacks.
**Learning:** Hardcoded insecure SSL contexts for database connections bypass built-in security features, leading to unprotected transport of sensitive database data.
**Prevention:** Always use `ssl.create_default_context()` without reducing its security features, or tie insecure configurations explicitly to a verified environment/configuration flag (e.g., `database_ssl_verify: bool = True`).

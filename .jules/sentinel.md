## 2024-05-11 - Database SSL Verification Disabled by Default
**Vulnerability:** The database connection configuration disabled SSL certificate validation and hostname checking (`ssl.CERT_NONE` and `check_hostname = False`) by default.
**Learning:** Defaulting to an insecure SSL context leaves the application vulnerable to Man-In-The-Middle (MITM) attacks on database traffic, even if the application enforces secure connections via its URL. The context configuration must explicitly require validation.
**Prevention:** Always use `ssl.create_default_context()` with secure defaults and only disable verification conditionally (e.g., in a development environment or via explicit configuration flags) rather than hardcoding it globally.

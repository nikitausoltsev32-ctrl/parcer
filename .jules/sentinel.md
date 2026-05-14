## 2024-05-18 - [CRITICAL] Enforce SSL Verification for Database Connections
**Vulnerability:** Database connections disabled hostname checking and certificate validation (`ssl.CERT_NONE`), leaving them vulnerable to Man-in-the-Middle (MitM) attacks globally.
**Learning:** Hardcoded disabling of SSL verification in SQLAlchemy/asyncpg engine setup compromises database transport security across all environments.
**Prevention:** Control SSL verification behavior using a configuration setting (`database_ssl_verify`), default it to `True` for secure-by-default behavior, and enable `check_hostname = True` with `ssl.CERT_REQUIRED` accordingly.

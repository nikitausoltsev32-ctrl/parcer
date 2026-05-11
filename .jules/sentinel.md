## 2025-02-14 - Fix insecure database SSL configuration
**Vulnerability:** The application was hardcoded to disable SSL hostname verification (`check_hostname = False`) and certificate validation (`verify_mode = ssl.CERT_NONE`) for database connections by default.
**Learning:** Defaulting to an insecure SSL context creates a man-in-the-middle vulnerability for database connections, which could expose sensitive data like credentials and personal info.
**Prevention:** Always use secure defaults (`database_ssl_verify: bool = True`) for connections handling sensitive data. Only disable verification with an explicit opt-out configuration flag.

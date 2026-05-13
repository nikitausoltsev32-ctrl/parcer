## 2024-05-24 - Database Connection SSL Configuration
**Vulnerability:** The application was disabling SSL hostname verification and certificate validation (`check_hostname = False` and `verify_mode = ssl.CERT_NONE`) by default for all database connections.
**Learning:** This exposes the application to Man-in-the-Middle (MitM) attacks by attackers intercepting or modifying the database connection.
**Prevention:** Always use default secure SSL configurations for database connections and only disable verification if explicitly configured to do so via `settings.database_ssl_verify`.

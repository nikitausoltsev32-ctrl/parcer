## 2024-05-15 - Hardcoded Secrets & Weak Default DB SSL Validation

**Vulnerability:**
The application had hardcoded default fallback values for `secret_key`, `tracking_secret`, and `database_url` in `app/core/config.py`. Additionally, the database connection SSL context in `app/core/database.py` disabled certificate validation and hostname checking unconditionally by default.

**Learning:**
Pydantic BaseSettings models with default string values are silent footguns - if `.env` is missing or variables are not set in the environment, the app uses insecure defaults in production instead of failing fast. Hardcoding `ssl.CERT_NONE` overrides any secure configuration the DB driver might have.

**Prevention:**
1. Sensitive settings (`secret_key`, `database_url`, etc.) must not have default values in configuration classes. They should be type-hinted without an assignment to force Pydantic to raise `ValidationError` on startup if missing.
2. A `.env.example` file must be maintained to document required settings for developers.
3. Database and external connections must default to verifying SSL certificates. If local development requires insecure connections, it must be explicitly configured via an environment variable (e.g., `DATABASE_SSL_VERIFY=false`) rather than hardcoding `ssl.CERT_NONE`.
## 2024-05-10 - Secure Database Connection Defaults
**Vulnerability:** Database connections disabled SSL certificate verification and hostname checking by default (`CERT_NONE` and `check_hostname = False`), which allows Man-in-the-Middle (MitM) attacks by attackers presenting a self-signed or forged certificate.
**Learning:** Hardcoding insecure configurations for development convenience often leaks into production. Default-allow or fail-open logic in security controls undermines infrastructure integrity.
**Prevention:** Always enforce secure SSL defaults by default. Require explicit, intentional configuration (e.g. `database_ssl_verify=False`) to bypass security checks for local testing.

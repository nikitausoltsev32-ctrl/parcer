## 2024-05-18 - Fix Open Redirect vulnerability in tracking endpoint
**Vulnerability:** Open Redirect in `track_click` endpoint when tracking signature is invalid.
**Learning:** `RedirectResponse` to user-supplied query parameters directly, even if signature verification fails, results in an Open Redirect vulnerability. Also, `unquote` shouldn't be used on query params as FastAPI does this automatically, leading to potential double-unquoting issues.
**Prevention:** Always return a 400 or appropriate error response if a tracking/redirect signature fails verification instead of proceeding with the redirect. Rely on FastAPI's native query parameter handling rather than manual unquoting.

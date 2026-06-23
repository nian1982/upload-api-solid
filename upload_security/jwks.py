import threading
import time

import requests

from upload_security.exceptions import JWKSFetchError


class JWKSProvider:
    def __init__(self, jwks_url: str, refresh_seconds: int = 3600, http_timeout: int = 10):
        self._url = jwks_url
        self._ttl = refresh_seconds
        self._timeout = http_timeout
        self._keys: dict[str, dict] = {}
        self._expires_at: float = 0
        self._lock = threading.Lock()

    def get_key(self, kid: str) -> dict | None:
        self._refresh_if_expired()
        with self._lock:
            return self._keys.get(kid)

    def _refresh_if_expired(self) -> None:
        if time.monotonic() < self._expires_at:
            return
        with self._lock:
            if time.monotonic() < self._expires_at:
                return
            try:
                resp = requests.get(self._url, timeout=self._timeout)
                resp.raise_for_status()
                jwks = resp.json()
                new_keys = {}
                for key in jwks.get("keys", []):
                    kid = key.get("kid")
                    if kid:
                        new_keys[kid] = {k: key[k] for k in ("kty", "kid", "use", "n", "e") if k in key}
                self._keys = new_keys
                self._expires_at = time.monotonic() + self._ttl
            except requests.RequestException as e:
                if not self._keys:
                    raise JWKSFetchError(str(e)) from e
    # Si ya hay keys cacheadas y falla el refresh, se mantienen las viejas

from jose import jwt
from jose.exceptions import JWTError, ExpiredSignatureError

from upload_security.config import KeycloakSettings
from upload_security.exceptions import InvalidTokenError, TokenExpiredError
from upload_security.jwks import JWKSProvider


_providers: dict[str, JWKSProvider] = {}


def _get_provider(settings: KeycloakSettings) -> JWKSProvider:
    url = settings.jwks_url
    if url not in _providers:
        _providers[url] = JWKSProvider(url, settings.jwks_refresh_seconds)
    return _providers[url]


def verify_token(token: str, settings: KeycloakSettings) -> dict | None:
    try:
        header = jwt.get_unverified_header(token)
        provider = _get_provider(settings)
        rsa_key = provider.get_key(header.get("kid"))
        if not rsa_key:
            return None

        decode_kwargs = {
            "token": token,
            "key": rsa_key,
            "algorithms": ["RS256"],
            "issuer": settings.issuer,
            "options": {
                "verify_exp": True,
                "verify_iss": True,
                "verify_aud": settings.verify_audience,
            },
        }
        if settings.verify_audience and settings.client_id:
            decode_kwargs["audience"] = settings.client_id

        return jwt.decode(**decode_kwargs)

    except ExpiredSignatureError:
        raise TokenExpiredError()
    except JWTError:
        return None


def has_role(payload: dict, client_id: str, role: str) -> bool:
    resource_access = payload.get("resource_access", {})
    client_roles = resource_access.get(client_id, {}).get("roles", [])
    return role in client_roles

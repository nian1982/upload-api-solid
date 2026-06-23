from upload_security.config import KeycloakSettings
from upload_security.exceptions import InvalidTokenError, RoleRequiredError
from upload_security.token import has_role, verify_token


def validate_ws_token(
    token: str,
    settings: KeycloakSettings,
    required_client_id: str = "",
    required_role: str = "",
) -> dict:
    payload = verify_token(token, settings)
    if not payload:
        raise InvalidTokenError()

    if required_client_id and required_role:
        if not has_role(payload, required_client_id, required_role):
            raise RoleRequiredError(required_role, required_client_id)

    return payload

class KeycloakError(Exception):
    pass


class InvalidTokenError(KeycloakError):
    def __init__(self, message: str = "Invalid or expired token"):
        self.message = message
        super().__init__(message)


class TokenExpiredError(InvalidTokenError):
    def __init__(self):
        super().__init__("Token has expired")


class JWKSFetchError(KeycloakError):
    def __init__(self, message: str = "Failed to fetch JWKS from Keycloak"):
        self.message = message
        super().__init__(message)


class RoleRequiredError(KeycloakError):
    def __init__(self, role: str, client_id: str = ""):
        self.role = role
        self.client_id = client_id
        msg = f"Required role '{role}'"
        if client_id:
            msg += f" for client '{client_id}'"
        msg += " not found in token"
        self.message = msg
        super().__init__(msg)

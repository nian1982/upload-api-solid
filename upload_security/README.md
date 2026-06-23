# upload_security

Módulo independiente de seguridad Keycloak para proyectos Python.
Valida tokens JWT (RS256) contra un servidor Keycloak sin acoplarse a ningún framework web.

---

## Índice

- [Arquitectura](#arquitectura)
- [Flujo de validación](#flujo-de-validación)
- [Estructura](#estructura)
- [Cómo usar en cualquier proyecto](#cómo-usar-en-cualquier-proyecto)
  - [1. Instalar dependencias](#1-instalar-dependencias)
  - [2. Configurar variables de entorno](#2-configurar-variables-de-entorno)
  - [3. Validar un token JWT](#3-validar-un-token-jwt)
  - [4. Verificar roles](#4-verificar-roles)
  - [5. Validar token en WebSocket](#5-validar-token-en-websocket)
- [Integración con FastAPI](#integración-con-fastapi)
  - [Dependencias de seguridad](#dependencias-de-seguridad)
  - [Proteger endpoints REST](#proteger-endpoints-rest)
  - [Proteger WebSocket](#proteger-websocket)
- [Integración con otros frameworks](#integración-con-otros-frameworks)
- [Configuración Keycloak](#configuración-keycloak)
- [Mejoras sobre security.py original](#mejoras-sobre-securitypy-original)

---

## Arquitectura

```
                 ┌──────────────────┐
                 │   Keycloak       │
                 │   /certs (JWKS)  │
                 └────────┬─────────┘
                          │
                   GET /certs
                          │
                          ▼
             ┌──────────────────────┐
             │   JWKSProvider       │
             │   (cache + TTL)      │
             │   - thread-safe      │
             │   - refresh autom.   │
             └──────────┬───────────┘
                        │
                        ▼
┌──────────┐    ┌───────────────┐
│  Token   │───→│ verify_token  │
│  JWT     │    │               │
│          │    │ 1. kid → key  │
│          │    │ 2. RS256 sig  │
│          │    │ 3. exp        │
│          │    │ 4. iss        │
│          │    │ 5. aud (opc)  │
│          │    │               │
│          │    │ → payload     │
│          │    │   o None      │
│          │    └──────┬────────┘
│          │           │
│          │           ▼
│          │    ┌───────────────┐
│          │    │  has_role     │
│          │    │ resource_access→
│          │    │ client.roles  │
│          │    │ → bool        │
│          │    └───────────────┘
└──────────┘
```

## Flujo de validación

```
1. verify_token(token, settings)

   1.1 Extraer header (kid) sin verificar
   1.2 JWKSProvider.get_key(kid)
       │
       ├─ ¿Cache expiró? → GET /certs → actualiza cache
       ├─ ¿Key match? → retorna RSA public key
       └─ ¿No match? → retorna None
    │
   1.3 jwt.decode(token, rsa_key, RS256)
       ├─ Verificar firma RS256
       ├─ Verificar exp (vencimiento)
       ├─ Verificar iss (emisor = {url}/realms/{realm})
       └─ Verificar aud (opcional, client_id)
    │
   1.4 → Retorna payload (dict) o None

2. has_role(payload, client_id, role)

   2.1 payload.resource_access[client_id].roles
   2.2 ¿role in roles? → True / False

3. validate_ws_token(token, settings, client_id, role)

   3.1 verify_token(token, settings)
   3.2 Si token inválido → raise InvalidTokenError
   3.3 Si falta rol → raise RoleRequiredError
   3.4 → Retorna payload
```

## Estructura

```
upload_security/
  __init__.py
  config.py           KeycloakSettings (pydantic-settings, env_prefix=KEYCLOAK_)
  jwks.py             JWKSProvider (cache thread-safe con TTL)
  token.py            verify_token() + has_role()
  ws.py               validate_ws_token() → payload o excepción
  exceptions.py       InvalidTokenError, RoleRequiredError, JWKSFetchError
  requirements.txt    python-jose[cryptography], requests, pydantic-settings
  README.md
```

---

## Cómo usar en cualquier proyecto

### 1. Instalar dependencias

```bash
pip install python-jose[cryptography] requests pydantic-settings
```

O copiar `upload_security/` al proyecto y:

```bash
pip install -r upload_security/requirements.txt
```

### 2. Configurar variables de entorno

```bash
# .env o variables del sistema
KEYCLOAK_URL=http://keycloak.example.com
KEYCLOAK_REALM=myrealm
KEYCLOAK_CLIENT_ID=my-client
KEYCLOAK_VERIFY_AUDIENCE=false
KEYCLOAK_JWKS_REFRESH_SECONDS=3600
```

O crear el settings directo en código:

```python
from upload_security.config import KeycloakSettings

settings = KeycloakSettings(
    url="http://localhost:8080",
    realm="myrealm",
    client_id="my-client",
)
```

### 3. Validar un token JWT

```python
from upload_security.config import KeycloakSettings
from upload_security.token import verify_token

settings = KeycloakSettings()
payload = verify_token("eyJhbGciOiJSUzI1NiIs...", settings)

if payload:
    print("Usuario:", payload.get("preferred_username"))
    print("Roles:", payload.get("resource_access"))
else:
    print("Token inválido o expirado")
```

### 4. Verificar roles

```python
from upload_security.token import has_role

payload = verify_token(token, settings)
if payload and has_role(payload, "my-client", "admin"):
    print("Acceso concedido")
else:
    print("Acceso denegado")
```

### 5. Validar token en WebSocket

```python
from upload_security.ws import validate_ws_token
from upload_security.exceptions import InvalidTokenError, RoleRequiredError

try:
    payload = validate_ws_token(
        token, settings,
        required_client_id="my-client",
        required_role="upload",
    )
    print("WS token válido para", payload.get("preferred_username"))
except InvalidTokenError:
    print("Token inválido, cerrar WS con código 4001")
except RoleRequiredError as e:
    print(f"Rol faltante: {e.message}")
```

---

## Integración con FastAPI

`upload_security` no depende de FastAPI. La integración se hace en el proyecto que usa FastAPI.

### Dependencias de seguridad

```python
# dependencies.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer
from upload_security.config import KeycloakSettings
from upload_security.token import has_role, verify_token

_security = HTTPBearer()
_settings = KeycloakSettings()

def get_current_user(credentials = Depends(_security)) -> dict:
    payload = verify_token(credentials.credentials, _settings)
    if not payload:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Token invalido")
    return payload

def require_role(client_id: str, role: str):
    def checker(payload: dict = Depends(get_current_user)) -> dict:
        if not has_role(payload, client_id, role):
            raise HTTPException(status.HTTP_403_FORBIDDEN,
                detail=f"Rol '{role}' requerido")
        return payload
    return checker
```

### Proteger endpoints REST

```python
# routers/upload.py
@router.post("/upload")
def upload_file(
    ...,
    _user: dict = Depends(require_role("my-client", "upload")),
):
    ...
```

### Proteger WebSocket

```python
# routers/ws.py
from fastapi import Query, WebSocket
from upload_security.config import KeycloakSettings
from upload_security.exceptions import InvalidTokenError, RoleRequiredError
from upload_security.ws import validate_ws_token

_settings = KeycloakSettings()

@router.websocket("/upload/{task_id}/ws")
async def upload_ws(websocket: WebSocket, task_id: str, token: str = Query(...)):
    try:
        validate_ws_token(token, _settings, "my-client", "upload")
    except InvalidTokenError:
        await websocket.close(code=4001, reason="Token invalido")
        return
    except RoleRequiredError as e:
        await websocket.close(code=4002, reason=e.message)
        return

    await websocket.accept()
    # ... lógica del WS
```

---

## Integración con otros frameworks

### Flask

```python
from flask import request, jsonify
from upload_security.token import verify_token

@app.route("/api/upload", methods=["POST"])
def upload():
    auth = request.headers.get("Authorization", "")
    token = auth.replace("Bearer ", "")
    payload = verify_token(token, KeycloakSettings())
    if not payload:
        return jsonify({"error": "Unauthorized"}), 401
    if not has_role(payload, "my-client", "upload"):
        return jsonify({"error": "Forbidden"}), 403
    # ... procesar upload
```

### Django

```python
from django.http import JsonResponse
from upload_security.token import verify_token

class TokenRequiredMixin:
    def dispatch(self, request, *args, **kwargs):
        token = request.META.get("HTTP_AUTHORIZATION", "").replace("Bearer ", "")
        payload = verify_token(token, KeycloakSettings())
        if not payload:
            return JsonResponse({"error": "Unauthorized"}, status=401)
        request.user_payload = payload
        return super().dispatch(request, *args, **kwargs)
```

---

## Configuración Keycloak

### Client

| Campo | Valor |
|---|---|
| Client ID | `api-load-files` |
| Access Type | `confidential` o `public` |
| Service Accounts Roles | ✅ Enabled (si es M2M) |
| Standard Flow | ✅ Enabled |
| Direct Access Grants | ✅ Enabled (si es ROPC) |

### Roles del client

Crear rol `load_files.upload` en el client `api-load-files`.

### Asignar roles a usuarios

```
Users → {user} → Role Mappings → Clients → api-load-files → load_files.upload
```

---

## Mejoras sobre security.py original

| Aspecto | `backend/load_files/api/security.py` | `upload_security/` |
|---|---|---|
| JWKS cache | Inmortal (nunca expira) | TTL configurable + refresh automático |
| `verify_iss` | Deshabilitado (`False`) | ✅ Habilitado contra `settings.issuer` |
| Thread-safe | ❌ Variable global | ✅ `threading.Lock` + doble-check |
| Reutilizable | Solo para load-files-proyect | Cualquier proyecto Python |
| Acoplado a framework | ✅ FastAPI | ❌ Puro Python |
| WebSocket | Manual en controller | `validate_ws_token()` unificado |

# solid/ — Módulos reutilizables para transferencia SFTP con progreso vía WebSocket

## Arquitectura

```
solid/
├── shared/       Utilidades transversales (logger, path_utils)
├── sftp/         Cliente SFTP reutilizable (paramiko)
├── ws/           Publicador/suscriptor de progreso vía Redis
└── upload/       Orquestador que valida y sube archivos usando sftp + ws
```

Cada módulo es **completamente independiente**. No tiene dependencias internas entre sí excepto `upload/` que consume `sftp/`. Puedes copiar `solid/sftp/` a cualquier proyecto Python y funcionará.

---

## 1. Módulo SFTP (`solid/sftp`)

### Uso básico

```python
from solid.sftp.config import SFTPSettings
from solid.sftp.paramiko_client import ParamikoSFTPClient

# Configuración vía constructor (ignora env vars)
settings = SFTPSettings(
    host="sftp.example.com",
    port=22,
    username="user",
    password="pass",
    upload_dir="/remote/uploads",
)
client = ParamikoSFTPClient(settings)

client.connect()
client.ensure_directory("/remote/uploads/2026")
client.upload_file("/remote/uploads/2026/reporte.pdf", b"...")
client.disconnect()
```

### Configuración vía variables de entorno

| Variable | Campo | Default |
|----------|-------|---------|
| `SFTP_HOST` | `host` | `localhost` |
| `SFTP_PORT` | `port` | `22` |
| `SFTP_USER` | `user` | `""` |
| `SFTP_PASS` | `password` | `""` |
| `SFTP_UPLOAD_DIR` | `upload_dir` | `/upload` |
| `SFTP_CHUNK_SIZE` | `chunk_size` | `4194304` (4 MB) |

```python
# Lee automáticamente de SFTP_HOST, SFTP_PORT, etc.
client = ParamikoSFTPClient()  # sin argumentos → usa env vars
```

### Subida con progreso

```python
from typing import BinaryIO

with open("archivo.pdf", "rb") as f:
    total = f.seek(0, 2)
    f.seek(0)

    def on_progress(sent: int, total: int):
        pct = sent / total * 100
        print(f"\r{pct:.1f}%", end="")

    client.upload_file_stream("/remote/archivo.pdf", f,
                               progress_callback=on_progress,
                               total_bytes=total)
```

### Interfaz programática

```python
from solid.sftp.interface import ISFTPClient
# Úsala para type hints o para implementar tu propio cliente (mock, boto3, etc.)
```

---

## 2. Módulo WebSocket/Redis (`solid/ws`)

### Publicar progreso (síncrono, para workers Celery)

```python
from solid.ws.redis_publisher import RedisProgressPublisher

pub = RedisProgressPublisher()
pub.publish("upload:abc-123", {
    "type": "progress",
    "task_id": "abc-123",
    "percentage": 50.0,
    "bytes_sent": 512,
    "total_bytes": 1024,
})
pub.save_state("upload:abc-123:state", {"type": "complete"}, ttl=3600)
pub.close()
```

### Suscribirse a progreso (asíncrono, para WebSockets FastAPI)

```python
from solid.ws.redis_subscriber import RedisProgressSubscriber

sub = RedisProgressSubscriber()
await sub.connect()
await sub.subscribe("upload:abc-123")

async for data in sub.listen():
    await websocket.send_json(data)
```

### Estado inicial (tarea ya completada)

```python
state = await sub.get_state("upload:abc-123:state")
if state and state["type"] == "complete":
    await websocket.send_json(state)
```

### Configuración vía variables de entorno

| Variable | Campo | Default |
|----------|-------|---------|
| `WS_REDIS_URL` | `redis_url` | `redis://localhost:6379/0` |
| `WS_CHANNEL_PREFIX` | `channel_prefix` | `upload` |
| `WS_STATE_TTL` | `state_ttl` | `3600` |

```python
# Sin argumentos → lee de env vars
pub = RedisProgressPublisher()
sub = RedisProgressSubscriber()
```

---

## 3. Módulo Upload (`solid/upload`)

### Uso con SFTP

```python
from solid.sftp.paramiko_client import ParamikoSFTPClient
from solid.upload.service import UploadService

sftp = ParamikoSFTPClient()
service = UploadService(sftp, upload_dir="/remote/uploads")

with open("factura.pdf", "rb") as f:
    result = service.upload_file("factura.pdf", f, "FACTURAS", "2026-06-20")

print(result.success, result.upload_path, result.error)
```

### Con callback de progreso

```python
result = service.upload_file(
    "factura.pdf", f, "FACTURAS", "2026-06-20",
    progress_callback=lambda sent, total: print(f"{sent}/{total}"),
)
```

### Solo validación (útil antes de encolar tarea asíncrona)

```python
try:
    tipo, ext, fecha = service.validate_upload_request(
        "factura.pdf", "FACTURAS", "2026-06-20", file_obj=f,
    )
    print(f"Válido: {tipo}, {ext}, {fecha}")
except UploadError as e:
    print(f"Inválido: {e.message}")
```

### Configuración vía variables de entorno

| Variable | Campo | Default |
|----------|-------|---------|
| `ALLOWED_FILE_TYPES` | `allowed_file_types` | `REPOSITORIO` |
| `ALLOWED_EXTENSIONS` | `allowed_extensions` | `.xlsx,.xls,.csv,.pdf` |
| `MAX_UPLOAD_SIZE_MB` | `max_upload_size_mb` | `500` |
| `ENVIRONMENT` | `environment` | `development` |
| `UPLOAD_DIR` | `upload_dir` | `/upload` |

---

## 4. Reutilizar en otro proyecto

Cada módulo es un paquete Python estándar. Para usarlos en otro proyecto:

### Opción A: Copiar el directorio

```bash
cp -r solid/sftp/ tu-proyecto/
```

```python
from sftp.paramiko_client import ParamikoSFTPClient
```

### Opción B: Como submódulo git

```bash
git submodule add https://github.com/tu-repo/solid.git lib/solid
```

### Opción C: Como paquete pip (próximamente)

```bash
pip install solid-sftp
```

---

## 5. Inyección de dependencias (ejemplo con FastAPI)

```python
from solid.sftp.paramiko_client import ParamikoSFTPClient
from solid.upload.service import UploadService
from fastapi import Depends

def get_upload_service() -> UploadService:
    sftp = ParamikoSFTPClient()
    return UploadService(sftp, upload_dir="/data/uploads")

@app.post("/upload")
def upload(file: UploadFile, svc: UploadService = Depends(get_upload_service)):
    result = svc.upload_file(file.filename, file.file, "REPOSITORIO", "2026-06-20")
    return {"ok": result.success, "path": result.upload_path}
```

---

## 6. Mock para testing

```python
from solid.upload.service import UploadService
from solid.upload.exceptions import UploadError

class MockSFTP:
    def connect(self): pass
    def disconnect(self): pass
    def ensure_directory(self, d): pass
    def upload_file_stream(self, path, obj, progress_callback=None, total_bytes=0):
        data = obj.read()
        if progress_callback: progress_callback(len(data), total_bytes or len(data))
        return len(data)
    def upload_file(self, path, data): pass

service = UploadService(MockSFTP())
result = service.upload_file("test.pdf", io.BytesIO(b"data"), "REPOSITORIO", "2026-06-20")
assert result.success
```

# Logger

Logger desacoplado listo para usar en cualquier módulo con una sola importación.

## Uso

```python
from shared.logger import log

log().info("mensaje")
log().warning("avisó")
log().error("algo falló")
```

El nombre del módulo se detecta automáticamente. También se puede pasar explícitamente:

```python
log("auth").info("usuario autenticado")
```

## Variables de entorno (`.env` en la raíz)

| Variable       | Default       | Descripción                                         |
|----------------|---------------|-----------------------------------------------------|
| `APP_ENV`      | `development` | `development` o `production`                        |
| `LOG_LEVEL`    | `INFO`        | Nivel mínimo: `DEBUG`, `INFO`, `WARNING`, `ERROR`   |
| `LOG_DIR`      | `logs`        | Directorio donde se guardan los archivos de log      |
| `ROOT_PACKAGE` | `solid`       | Prefijo raíz a limpiar del nombre auto-detectado    |

Las variables de entorno del sistema siempre tienen prioridad sobre el `.env`.

## Comportamiento

### Development (`APP_ENV=development`)
- **Consola**: imprime desde `LOG_LEVEL` en adelante (`INFO`, `WARNING`, `ERROR`, etc.)
- **Archivo**: rotación diaria a medianoche, guarda **todos** los niveles

### Producción (`APP_ENV=production`)
- **Consola**: solo imprime `ERROR`
- **Archivo**: rotación diaria a medianoche, guarda **todos** los niveles

## Archivos de log

Un solo archivo con rotación diaria:

```
logs/
└── app.log
```

Cada línea incluye el nombre del módulo:
```
2026-06-22 16:50:58 | INFO     | sftp.paramiko_client | Conectando...
2026-06-22 16:50:58 | INFO     | sftp.config          | SFTPSettings loaded...
2026-06-22 16:50:58 | INFO     | upload.service        | Starting upload...
```

Rotación diaria a medianoche con 30 backups de retención.

## Tests

```bash
# instalar dependencias de desarrollo
pip install -r requirements-dev.txt

# ejecutar tests
python -m pytest tests/ -v
```

## Ejemplo `.env`

```env
APP_ENV=development
LOG_LEVEL=DEBUG
LOG_DIR=logs
```

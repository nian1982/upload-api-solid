#!/usr/bin/env python3
"""
Ejemplos de uso de los módulos solid/ — SFTP, WebSocket/Redis y Upload.

Requisitos:
    pip install paramiko redis pydantic-settings

Ejecución:
    python solid/examples.py              # tests unitarios (sin conexión externa)
    python solid/examples.py --live       # requiere SFTP + Redis reales
"""

import io
import os
import sys
import time

#
# ─── EJEMPLO 1: SFTP CLIENT (INDEPENDIENTE) ────────────────────────────────
#

def example_sftp_basic():
    """Uso básico de solid.sftp con un cliente mock."""
    print("─" * 50)
    print("1. SFTP básico (con mock)")
    print("─" * 50)

    from solid.sftp.paramiko_client import ParamikoSFTPClient
    from solid.sftp.config import SFTPSettings

    # Config sin conexión real — solo probamos que la interfaz funciona
    settings = SFTPSettings(
        host="localhost", port=22, user="test", password="test",
    )
    client = ParamikoSFTPClient(settings)

    # Verificar propiedades del settings
    assert settings.host == "localhost"
    assert settings.port == 22
    assert settings.chunk_size == 4194304
    assert settings.window_size == 64 * 1024 * 1024
    print("  ✔ SFTPSettings creado correctamente")
    print("  ✔ ParamikoSFTPClient instanciado")
    print()


def example_sftp_with_progress():
    """Subida con callback de progreso (usando un cliente simulado)."""
    print("─" * 50)
    print("2. SFTP con callback de progreso")
    print("─" * 50)

    from solid.sftp.interface import ISFTPClient
    from typing import BinaryIO, Callable, Optional

    class MockSFTPClient:
        def connect(self):
            print("  · Conectando a SFTP... OK")

        def disconnect(self):
            print("  · Desconectando SFTP... OK")

        def ensure_directory(self, remote_dir: str):
            print(f"  · Creando directorio {remote_dir}... OK")

        def upload_file_stream(
            self,
            remote_path: str,
            file_obj: BinaryIO,
            progress_callback: Optional[Callable[[int, int], None]] = None,
            total_bytes: int = 0,
        ) -> int:
            sent = 0
            chunk = file_obj.read(4096)
            while chunk:
                sent += len(chunk)
                if progress_callback:
                    progress_callback(sent, total_bytes or sent)
                chunk = file_obj.read(4096)
            print(f"  · Subido {remote_path} ({sent} bytes)")
            return sent

        def upload_file(self, remote_path: str, data: bytes):
            pass

    client = MockSFTPClient()
    client.connect()
    client.ensure_directory("/upload/REPOSITORIO/20260620/08")

    calls = []

    def progress(sent: int, total: int):
        pct = sent / total * 100 if total else 0
        calls.append((sent, total))
        print(f"  · Progreso: {pct:.0f}% ({sent}/{total} bytes)")

    data = b"x" * 20000
    client.upload_file_stream(
        "/upload/test.bin", io.BytesIO(data),
        progress_callback=progress, total_bytes=len(data),
    )
    assert len(calls) > 0, "Debe haber al menos una llamada al callback"
    assert calls[-1][0] == len(data), f"Debe enviar {len(data)} bytes"
    print("  ✔ Progreso reportado correctamente")
    client.disconnect()
    print()


#
# ─── EJEMPLO 2: WEB SOCKET / REDIS (INDEPENDIENTE) ────────────────────────
#

def example_ws_publisher():
    """Publicador de progreso vía Redis (solo instanciación si no hay Redis)."""
    print("─" * 50)
    print("3. Redis Progress Publisher")
    print("─" * 50)

    from solid.ws.redis_publisher import RedisProgressPublisher
    from solid.ws.models import ProgressType

    pub = RedisProgressPublisher()
    print("  ✔ RedisProgressPublisher instanciado")

    if "--live" not in sys.argv:
        print("  ⚠  Saltando pruebas de Redis (usa --live para conexión real)")
        print()
        return

    try:
        pub.publish("upload:demo-1", {
            "type": ProgressType.STARTING.value,
            "task_id": "demo-1",
            "file_name": "reporte.xlsx",
            "total_bytes": 10000,
            "size_display": "9.77 KB",
        })
        print("  ✔ Evento STARTING publicado")

        pub.save_state("upload:demo-1:state", {
            "type": "complete", "task_id": "demo-1",
        }, ttl=60)

        state = pub.get_state("upload:demo-1:state")
        assert state is not None
        assert state["type"] == "complete"
        print("  ✔ Estado guardado y recuperado")
    except Exception as e:
        print(f"  ⚠  Redis no disponible: {e}")
    finally:
        pub.close()
    print()


def example_ws_subscriber():
    """Suscriptor de progreso vía Redis."""
    print("─" * 50)
    print("4. Redis Progress Subscriber")
    print("─" * 50)

    from solid.ws.redis_subscriber import RedisProgressSubscriber
    from solid.ws.config import WSSettings

    sub = RedisProgressSubscriber(WSSettings(redis_url="redis://localhost:6379/0"))
    print("  ✔ RedisProgressSubscriber instanciado")
    print("  ⚠  Para test completo de pub/sub: python solid/examples.py --live")
    print()


#
# ─── EJEMPLO 3: UPLOAD SERVICE (ORQUESTADOR) ──────────────────────────────
#

def example_upload_basic():
    """UploadService: subida básica con validación."""
    print("─" * 50)
    print("5. UploadService básico (con mock SFTP)")
    print("─" * 50)

    from solid.upload.service import UploadService
    from solid.upload.config import UploadSettings
    from solid.upload.exceptions import (
        UploadError,
        FileTypeNotAllowedError,
        ExtensionNotAllowedError,
        InvalidDateError,
    )

    class MockSFTP:
        def connect(self): pass
        def disconnect(self): pass
        def ensure_directory(self, d): pass
        def upload_file_stream(self, path, obj, progress_callback=None, total_bytes=0):
            data = obj.read()
            if progress_callback:
                progress_callback(len(data), total_bytes or len(data))
            return len(data)
        def upload_file(self, path, data): pass

    service = UploadService(
        MockSFTP(),
        settings=UploadSettings(
            allowed_file_types="REPOSITORIO,FACTURAS",
            allowed_extensions=".xlsx,.xls,.csv,.pdf",
            max_upload_size_mb=500,
        ),
    )

    # Subida exitosa
    data = io.BytesIO(b"PK\x03\x04" + b"datos" * 100)
    result = service.upload_file("reporte.xlsx", data, "REPOSITORIO", "2026-06-20")
    assert result.success, f"Esperaba éxito: {result.error}"
    assert result.extension == ".xlsx"
    assert result.size_bytes > 0
    assert result.tipo_archivo == "REPOSITORIO"
    assert result.upload_path.startswith("/upload/REPOSITORIO/20260620")
    print(f"  ✔ Archivo subido: {result.upload_path} ({result.size_display})")

    # Validación de tipo incorrecto
    try:
        service.validate_upload_request("test.xlsx", "INVALIDO", "2026-06-20")
        assert False, "Debe rechazar tipo inválido"
    except FileTypeNotAllowedError as e:
        print(f"  ✔ Tipo inválido rechazado: {e.message}")

    # Validación de extensión incorrecta
    try:
        service.validate_upload_request("test.exe", "REPOSITORIO", "2026-06-20")
        assert False, "Debe rechazar extensión inválida"
    except ExtensionNotAllowedError as e:
        print(f"  ✔ Extensión inválida rechazada: {e.message}")

    # Validación de fecha incorrecta
    try:
        service.validate_upload_request("test.xlsx", "REPOSITORIO", "20-06-2026")
        assert False, "Debe rechazar fecha inválida"
    except InvalidDateError as e:
        print(f"  ✔ Fecha inválida rechazada: {e.message}")

    # Validación de magic bytes (xlsx debe empezar con PK)
    bad_data = io.BytesIO(b"%PDF-this-is-labeled-as-xlsx")
    try:
        service.validate_upload_request("test.xlsx", "REPOSITORIO", "2026-06-20", bad_data)
        assert False, "Debe rechazar contenido incorrecto"
    except UploadError as e:
        print(f"  ✔ Magic bytes incorrecto rechazado: {e.message}")

    print()


def example_upload_with_progress():
    """UploadService con callback de progreso."""
    print("─" * 50)
    print("6. UploadService con progreso")
    print("─" * 50)

    from solid.upload.service import UploadService

    class MockSFTP:
        def connect(self): pass
        def disconnect(self): pass
        def ensure_directory(self, d): pass
        def upload_file_stream(self, path, obj, progress_callback=None, total_bytes=0):
            chunk = obj.read(4096)
            sent = 0
            while chunk:
                sent += len(chunk)
                if progress_callback:
                    progress_callback(sent, total_bytes or sent)
                chunk = obj.read(4096)
            return sent
        def upload_file(self, path, data): pass

    service = UploadService(MockSFTP())
    data = io.BytesIO(b"PK\x03\x04" + b"A" * 50000)

    calls = []

    def on_progress(sent: int, total: int):
        calls.append(sent)
        pct = sent / total * 100 if total else 0
        print(f"  · Progreso: {pct:.1f}%  ({sent} / {total})")

    result = service.upload_file(
        "datos.xlsx", data, "REPOSITORIO", "2026-06-20",
        progress_callback=on_progress, total_bytes=50004,
    )
    assert result.success
    assert calls[-1] == 50004
    print(f"  ✔ Subida completada: {result.size_display} en {result.upload_time_seconds}s")
    print()


#
# ─── EJEMPLO 4: UPLOAD + WS INTEGRADOS ────────────────────────────────────
#

def example_upload_with_ws():
    """UploadService + Redis publisher (worker simulado, requiere --live)."""
    print("─" * 50)
    print("7. UploadService + Redis publisher (worker simulado)")
    print("─" * 50)

    from solid.upload.service import UploadService
    from solid.ws.redis_publisher import RedisProgressPublisher
    from solid.ws.models import ProgressType
    from datetime import datetime

    class MockSFTP:
        def connect(self): pass
        def disconnect(self): pass
        def ensure_directory(self, d): pass
        def upload_file_stream(self, path, obj, progress_callback=None, total_bytes=0):
            sent = 0
            for chunk in iter(lambda: obj.read(4096), b""):
                sent += len(chunk)
                if progress_callback:
                    progress_callback(sent, total_bytes or sent)
                time.sleep(0.001)
            return sent
        def upload_file(self, path, data): pass

    task_id = "demo-integration"
    sftp = MockSFTP()
    service = UploadService(sftp)

    def progress(sent, total):
        print(f"  · Progreso: {sent}/{total}")

    data = io.BytesIO(b"PK\x03\x04" + b"B" * 10000)
    result = service.upload_file(
        "integracion.xlsx", data, "REPOSITORIO", "2026-06-20",
        progress_callback=progress, total_bytes=10004,
    )

    if result.success:
        print(f"  ✔ Upload completado: {result.size_display} en {result.upload_time_seconds}s")
        if "--live" in sys.argv:
            publisher = RedisProgressPublisher()
            try:
                publisher.publish(f"upload:{task_id}", {
                    "type": ProgressType.STARTING.value,
                    "task_id": task_id, "file_name": "integracion.xlsx",
                    "total_bytes": 10004, "size_display": "9.77 KB",
                    "timestamp": datetime.now().isoformat(),
                })
                publisher.publish(f"upload:{task_id}", {
                    "type": ProgressType.COMPLETE.value, "task_id": task_id,
                    "result": {"success": True, "file_name": result.file_name},
                })
                print("  ✔ Eventos publicados en Redis")
                publisher.close()
            except Exception as e:
                print(f"  ⚠  Redis no disponible: {e}")
    else:
        print(f"  ✗ Upload falló: {result.error}")
    print()


#
# ─── EJEMPLO 5: CONFIGURACIÓN POR ENV VARS ─────────────────────────────────
#

def example_env_config():
    """Demostración de configuración vía variables de entorno."""
    print("─" * 50)
    print("8. Configuración vía environment variables")
    print("─" * 50)

    from solid.sftp.config import SFTPSettings

    # Sin env vars → defaults
    s = SFTPSettings()
    print(f"  · SFTP host (default): {s.host}")
    print(f"  · SFTP port (default): {s.port}")

    # Con env vars simuladas
    os.environ["SFTP_HOST"] = "produccion.example.com"
    os.environ["SFTP_PORT"] = "4223"
    os.environ["SFTP_USER"] = "deploy"
    os.environ["SFTP_PASS"] = "secret123"

    s2 = SFTPSettings()
    print(f"  · SFTP host (env): {s2.host}")
    print(f"  · SFTP port (env): {s2.port}")
    print(f"  · SFTP user (env): '{s2.user}'")

    del os.environ["SFTP_HOST"]
    del os.environ["SFTP_PORT"]
    del os.environ["SFTP_USER"]
    del os.environ["SFTP_PASS"]
    print()


#
# ─── MAIN ──────────────────────────────────────────────────────────────────
#

def main():
    live = "--live" in sys.argv

    print()
    print("══════════════════════════════════════════════════")
    print("  solid/ — Ejemplos de uso")
    print("══════════════════════════════════════════════════")
    print()

    example_sftp_basic()
    example_sftp_with_progress()
    example_ws_publisher()
    example_ws_subscriber()
    example_upload_basic()
    example_upload_with_progress()
    example_upload_with_ws()
    example_env_config()

    print("═" * 50)
    print("  Todos los ejemplos completados")
    print("═" * 50)


if __name__ == "__main__":
    main()

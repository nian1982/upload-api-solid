import os
import sys
import time
import socket
import paramiko

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from upload import upload_file


def upload_with_implementation():
    file_path = "/home/nian/Downloads/cm-rec/SR2104000_VIGENCIA_CONTRATOADMIN_SIGLA_20260515114823.csv"
    tipo = "REPOSITORIO"
    fecha = "2026-06-20"

    print(f"\nSubiendo: {file_path}")
    print(f"Tipo: {tipo} | Fecha: {fecha}\n")

    from upload.facade import upload_file as _upload
    result = _upload(
        file_path,
        tipo,
        fecha,
        show_progress=True
    )

    print(f"\n{'✓' if result.success else '✗'} {result.file_name}")
    print(f"Ruta remota: {result.upload_path}")
    print(f"Tamaño: {result.size_display}")
    print(f"Tiempo: {result.upload_time_seconds}s")

    if result.error:
        print(f"Error: {result.error}")

    sys.exit(0 if result.success else 1)


def upload_file(
        file_path: str,
        remote_dir: str,
        host: str,
        port: int,
        user: str,
        password: str,
        timeout: int = 30,
    ):
    import socket
    import os
    import time
    import paramiko

    sftp = None
    transport = None

    try:
        print(f"Conectando a {host}:{port}...")

        sock = socket.create_connection((host, port), timeout=timeout)

        transport = paramiko.Transport(sock)
        transport.window_size = 64 * 1024 * 1024

        transport.packetizer.REKEY_BYTES = 2**40
        transport.packetizer.REKEY_PACKETS = 2**40

        transport.connect(username=user, password=password)

        sftp = paramiko.SFTPClient.from_transport(transport)

        print("✓ Conectado\n")

        path = ""
        for part in remote_dir.strip("/").split("/"):
            path += f"/{part}"
            try:
                sftp.mkdir(path)
            except IOError:
                pass

        file_name = os.path.basename(file_path)
        remote_path = f"{remote_dir.rstrip('/')}/{file_name}"

        total_size = os.path.getsize(file_path)
        start = time.perf_counter()

        def progress(transferred, total):
            elapsed = max(time.perf_counter() - start, 0.001)
            pct = (transferred / total) * 100 if total else 0
            speed_mb = (transferred / 1024 / 1024) / elapsed

            bar_size = 40
            filled = int(bar_size * transferred / total) if total else 0

            bar = "█" * filled + "░" * (bar_size - filled)

            print(
                f"\r{bar} {pct:6.2f}% {transferred/1024/1024:8.2f}MB "
                f"{speed_mb:6.2f}MB/s",
                end="",
                flush=True,
            )

        print(f"Subiendo: {file_name}")

        sftp.put(file_path, remote_path, callback=progress, confirm=True)

        elapsed = time.perf_counter() - start
        avg_speed = (total_size / 1024 / 1024) / elapsed

        print(f"\n✓ OK | {elapsed:.2f}s | {avg_speed:.2f} MB/s")
        return True

    except Exception as e:
        print(f"\n✗ Error: {e}")
        return False

    finally:
        if sftp:
            sftp.close()
        if transport:
            transport.close()

if __name__ == "__main__":
    upload_with_implementation()

    # # ─── configurar acá ───
    # creds = dict(
    #     host="10.242.202.138",
    #     port=4227,
    #     user="APbfinan",
    #     password="Bogota2022!",
    # )
    # file_path = "/home/nian/Downloads/cm-rec/SR2104000_CATALOGO_PARTICULARADMIN_SIGLA_20260515114847.csv"
    # remote_dir = "/Deceval/Imagenes/Sucursales/Bogota/Finandina/REPOSITORIO/20260620/17"
    # # ─────────────────────

    # success = upload_file(file_path, remote_dir, timeout=30, **creds)
    # sys.exit(0 if success else 1)

import logging

import pytest


def test_returns_logger():
    from shared.logger import log

    assert isinstance(log(), logging.Logger)


def test_auto_detects_module_name():
    from shared.logger import log

    assert log().name == __name__


def test_custom_name():
    from shared.logger import log

    assert log("auth").name == "auth"
    assert log("sftp.core").name == "sftp.core"


def test_reuses_cached_logger():
    from shared.logger import log

    assert log("solid") is log("solid")
    assert log("other") is log("other")


def test_console_handler_level_dev(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("LOG_LEVEL", "WARNING")
    from shared.logger import log

    logger = log()
    h = _console_handler(logger)
    assert h.level == logging.WARNING


def test_console_handler_level_prod(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    from shared.logger import log

    logger = log()
    h = _console_handler(logger)
    assert h.level == logging.ERROR


def test_file_handler_level(monkeypatch):
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    from shared.logger import log

    logger = log()
    h = _file_handler(logger)
    assert h.level == logging.DEBUG


def test_dev_outputs_all_levels(monkeypatch, capsys):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("LOG_LEVEL", "INFO")
    from shared.logger import log

    logger = log()
    logger.info("info msg")
    logger.warning("warn msg")
    logger.error("err msg")

    out = capsys.readouterr().out
    assert "info msg" in out
    assert "warn msg" in out
    assert "err msg" in out


def test_prod_console_only_error(monkeypatch, capsys):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("LOG_LEVEL", "INFO")
    from shared.logger import log

    logger = log()
    logger.info("info msg")
    logger.warning("warn msg")
    logger.error("err msg")

    out = capsys.readouterr().out
    assert "info msg" not in out
    assert "warn msg" not in out
    assert "err msg" in out


def test_writes_log_file(monkeypatch, tmp_path):
    monkeypatch.setenv("LOG_DIR", str(tmp_path))
    from shared.logger import log

    logger = log("test_module")
    logger.info("hello file")

    log_file = tmp_path / "app.log"
    assert log_file.exists()
    assert "hello file" in log_file.read_text()


def test_file_contains_all_levels(monkeypatch, tmp_path):
    monkeypatch.setenv("LOG_DIR", str(tmp_path))
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("LOG_LEVEL", "INFO")
    from shared.logger import log

    logger = log("all_levels")
    logger.info("info msg")
    logger.warning("warn msg")
    logger.error("err msg")

    content = (tmp_path / "app.log").read_text()
    assert "info msg" in content
    assert "warn msg" in content
    assert "err msg" in content


def test_env_var_overrides_dotenv(monkeypatch, capsys):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("LOG_LEVEL", "INFO")
    from shared.logger import log

    logger = log()
    logger.info("should not appear")
    logger.error("should appear")

    out = capsys.readouterr().out
    assert "should not appear" not in out
    assert "should appear" in out


def _console_handler(logger):
    return next(h for h in logger.handlers if isinstance(h, logging.StreamHandler))


def _file_handler(logger):
    from logging.handlers import TimedRotatingFileHandler

    return next(
        h for h in logger.handlers if isinstance(h, TimedRotatingFileHandler)
    )

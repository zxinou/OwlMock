from __future__ import annotations


def configure_sqlite_connection(dbapi_connection, _connection_record=None) -> None:
    """Apply the durability and integrity settings required by OwlMock."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.close()

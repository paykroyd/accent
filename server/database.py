import sqlite3
from pathlib import Path
from threading import Lock
from logging import info, warning
from oauth2client.client import OAuth2Credentials, Storage
from googleapiclient.http import build_http
from oauth2client.client import HttpAccessTokenRefreshError

# Path to the SQLite database file
DB_FILE = Path(__file__).parent / 'accent.db'

# Database connection lock
_db_lock = Lock()


def get_connection():
    """Get a database connection, creating the database if needed."""
    conn = sqlite3.connect(str(DB_FILE))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize the database schema."""
    with _db_lock:
        conn = get_connection()
        try:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS oauth_credentials (
                    id TEXT PRIMARY KEY,
                    service TEXT NOT NULL,
                    credentials_json TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()
            info('Database initialized')
        finally:
            conn.close()


def get_credentials(service, key='default'):
    """Get OAuth credentials for a service."""
    with _db_lock:
        conn = get_connection()
        try:
            cursor = conn.execute(
                'SELECT credentials_json FROM oauth_credentials WHERE id = ? AND service = ?',
                (key, service)
            )
            row = cursor.fetchone()
            if row:
                return row['credentials_json']
            return None
        finally:
            conn.close()


def save_credentials(service, credentials_json, key='default'):
    """Save OAuth credentials for a service."""
    with _db_lock:
        conn = get_connection()
        try:
            conn.execute('''
                INSERT OR REPLACE INTO oauth_credentials (id, service, credentials_json, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ''', (key, service, credentials_json))
            conn.commit()
            info(f'Saved credentials for {service}')
        finally:
            conn.close()


def delete_credentials(service, key='default'):
    """Delete OAuth credentials for a service."""
    with _db_lock:
        conn = get_connection()
        try:
            conn.execute(
                'DELETE FROM oauth_credentials WHERE id = ? AND service = ?',
                (key, service)
            )
            conn.commit()
            info(f'Deleted credentials for {service}')
        finally:
            conn.close()


class GoogleCalendarStorage(Storage):
    """Credentials storage for the Google Calendar API using SQLite."""

    def __init__(self, key='default'):
        super(GoogleCalendarStorage, self).__init__(lock=Lock())
        self._key = key

    def locked_get(self):
        """Load credentials from SQLite and attach this storage."""
        json_str = get_credentials('google_calendar', self._key)
        if not json_str:
            return None

        try:
            credentials = OAuth2Credentials.from_json(json_str)
            if credentials and not credentials.invalid:
                credentials.set_store(self)
                return credentials

            # Handle expiration
            if credentials and credentials.access_token_expired:
                try:
                    info('Refreshing Google Calendar credentials.')
                    credentials.refresh(build_http())
                    credentials.set_store(self)
                    return credentials
                except HttpAccessTokenRefreshError as e:
                    warning(f'Google Calendar refresh failed: {e}')

            # Credentials are invalid
            warning('Deleting invalid Google Calendar credentials.')
            self.locked_delete()
            return None
        except Exception as e:
            warning(f'Failed to load credentials: {e}')
            return None

    def locked_put(self, credentials):
        """Save credentials to SQLite."""
        save_credentials('google_calendar', credentials.to_json(), self._key)

    def locked_delete(self):
        """Delete credentials from SQLite."""
        delete_credentials('google_calendar', self._key)


class DataError(Exception):
    """An error indicating issues retrieving data."""
    pass


# Initialize database on module load
init_db()

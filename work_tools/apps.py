from django.apps import AppConfig
from django.db.backends.signals import connection_created

class WorkToolsConfig(AppConfig):
    name = "work_tools"

    def ready(self):
        def on_conn(sender, connection, **kwargs):
            try:
                if connection.vendor == "sqlite":
                    with connection.cursor() as c:
                        c.execute("PRAGMA journal_mode=WAL;")
                        c.execute("PRAGMA synchronous=NORMAL;")
                        c.execute("PRAGMA busy_timeout=30000;")
            except Exception:
                pass
        connection_created.connect(on_conn)

from django.db.backends.postgresql.base import DatabaseWrapper as PostgresDatabaseWrapper
from middleware.utils import get_current_tenant_id

class DatabaseWrapper(PostgresDatabaseWrapper):
    def _cursor(self, name=None):
        cursor = super()._cursor(name)
        tenant_id = get_current_tenant_id() or ''
        
        try:
            is_autocommit = self.get_autocommit()
        except Exception:
            is_autocommit = True
            
        cmd_prefix = "SET" if is_autocommit else "SET LOCAL"
        
        # Execute statement timeout and tenant isolation GUC variables
        cursor.execute(f"{cmd_prefix} statement_timeout = '10s';")
        cursor.execute(f"{cmd_prefix} app.current_tenant = '{tenant_id}';")
        
        return cursor

import unittest

from tests.db_fixture import IsolatedDatabaseTestCase
from app.services.audit import clear_audit_logs, list_audit_logs, record_audit_log


class AuditLogTest(IsolatedDatabaseTestCase):
    def test_log_list_and_clear(self) -> None:
        record_audit_log("owner", "POST", "/api/entries", 200)
        record_audit_log("owner", "DELETE", "/api/entries/1", 404)

        rows = list_audit_logs()
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["method"], "DELETE")
        self.assertEqual(clear_audit_logs(), 2)
        self.assertEqual(list_audit_logs(), [])


if __name__ == "__main__":
    unittest.main()

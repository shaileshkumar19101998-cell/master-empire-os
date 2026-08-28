import unittest
from business_master_orchestrator import BusinessMasterOrchestrator
class TestMasterOrchestrator(unittest.TestCase):
    def test_dry_run(self):
        orch = BusinessMasterOrchestrator()
        res = orch.run_dry_run()
        self.assertEqual(res["status"], "DRY_RUN_PASSED")
if __name__ == "__main__":
    unittest.main()

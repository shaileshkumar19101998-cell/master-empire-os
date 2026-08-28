# test_operator_control_plane.py
import unittest
from operator_control_plane import OperatorControlPlane

class TestOperatorControlPlane(unittest.TestCase):
    def setUp(self):
        self.cp = OperatorControlPlane()

    def test_1_status(self):
        res = self.cp.execute_command("status")
        self.assertEqual(res["command"], "status")
        self.assertTrue(res["invariants"]["LIVE_LOCKED"])

    def test_2_health(self):
        res = self.cp.execute_command("health")
        self.assertEqual(res["health_status"], "HEALTHY_SECURE")

    def test_3_preview(self):
        res = self.cp.execute_command("preview")
        self.assertEqual(res["orchestration_status"], "SUCCESS")

    def test_4_live_block(self):
        with self.assertRaises(PermissionError):
            self.cp.execute_command("preview", {"live": True})

    def test_5_auto_apply_block(self):
        with self.assertRaises(ValueError):
            self.cp.execute_command("preview", {"auto_apply": True})

if __name__ == "__main__":
    unittest.main()

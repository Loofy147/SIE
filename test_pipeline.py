import unittest
import os
import tempfile
import sqlite3
import pipeline
import curriculum_store as cs

class TestPipeline(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp_dir.name, "test_curriculum.db")
        self.conn = cs.init_db(self.db_path)

    def tearDown(self):
        self.conn.close()
        self.tmp_dir.cleanup()

    def test_ingest_valid_artifact(self):
        # File artifact
        file_path = os.path.join(self.tmp_dir.name, "test_file.txt")
        with open(file_path, "w") as f:
            f.write("hello")
        art_file = pipeline.ingest_artifact(file_path)
        self.assertEqual(art_file["type"], "file")
        self.assertTrue(art_file["exists"])

        # Directory artifact
        art_dir = pipeline.ingest_artifact(self.tmp_dir.name)
        self.assertEqual(art_dir["type"], "directory")

        # Non-existent artifact raises FileNotFoundError
        with self.assertRaises(FileNotFoundError):
            pipeline.ingest_artifact("/nonexistent/path/12345")

    def test_execute_sandboxed_success(self):
        art = pipeline.ingest_artifact(self.tmp_dir.name)
        res = pipeline.execute_sandboxed(art, ["python3", "-c", "print('hello from sandbox')"])
        self.assertEqual(res["returncode"], 0)
        self.assertIn("hello from sandbox", res["stdout"])
        self.assertFalse(res["timed_out"])

    def test_execute_sandboxed_timeout(self):
        art = pipeline.ingest_artifact(self.tmp_dir.name)
        res = pipeline.execute_sandboxed(art, ["python3", "-c", "import time; time.sleep(2)"], timeout=1)
        self.assertTrue(res["timed_out"])
        self.assertEqual(res["returncode"], -1)

    def test_evaluate_gate_vetted_and_rejected(self):
        # Successful execution evaluate gate
        exec_success = {"command": "echo test", "returncode": 0, "stdout": "test\n", "stderr": "", "timed_out": False}
        gate_vetted = pipeline.evaluate_gate(exec_success, "echo works")
        self.assertEqual(gate_vetted["status"], "vetted")
        self.assertIn("PROMOTED", gate_vetted["vet_note"])

        # Failed execution evaluate gate
        exec_fail = {"command": "false", "returncode": 1, "stdout": "", "stderr": "error message", "timed_out": False}
        gate_rejected = pipeline.evaluate_gate(exec_fail, "claim")
        self.assertEqual(gate_rejected["status"], "rejected")
        self.assertIn("REJECTED", gate_rejected["vet_note"])

        # Timed out execution evaluate gate
        exec_timeout = {"command": "sleep 100", "returncode": -1, "stdout": "", "stderr": "Execution timed out", "timed_out": True}
        gate_timeout = pipeline.evaluate_gate(exec_timeout, "claim")
        self.assertEqual(gate_timeout["status"], "rejected")
        self.assertIn("REJECTED", gate_timeout["vet_note"])

    def test_register_result_db(self):
        exec_res = {"command": "echo pass", "returncode": 0, "stdout": "pass\n", "stderr": "", "timed_out": False}
        gate_res = pipeline.evaluate_gate(exec_res, "test claim")

        lesson_id = pipeline.register_result(self.conn, "Test Lesson", "Test Content", gate_res)
        lesson = cs.get_lesson(self.conn, lesson_id)

        self.assertIsNotNone(lesson)
        self.assertEqual(lesson["title"], "Test Lesson")
        self.assertEqual(lesson["status"], "vetted")
        self.assertIn("PROMOTED", lesson["vet_note"])

if __name__ == "__main__":
    unittest.main()

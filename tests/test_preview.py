import json
import os
from email import policy
from email.parser import BytesParser
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / "examples/application.json"
RESUME = ROOT / "examples/resume.txt"
GUARD = """
import os
import sys

def deny_transport(event, args):
    if event.startswith(("socket.", "smtplib.", "subprocess.")) or event in {
        "os.exec", "os.fork", "os.posix_spawn", "os.spawn", "os.system"
    }:
        os._exit(97)

sys.addaudithook(deny_transport)
print("transport guard installed", file=sys.stderr)
"""


class PreviewTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.directory = Path(temp.name)
        self.output = self.directory / "message.eml"
        (self.directory / "sitecustomize.py").write_text(GUARD, encoding="utf-8")
        self.env = {**os.environ, "PYTHONPATH": temp.name}

    def python(self, *args):
        result = subprocess.run(
            [sys.executable, *args],
            cwd=self.directory,
            env=self.env,
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertIn("transport guard installed", result.stderr)
        return result

    def preview(self, record=RECORD, resume=RESUME):
        return self.python(ROOT / "preview.py", record, resume, "--out", self.output)

    def test_guard_blocks_socket_construction(self):
        result = self.python("-c", "import socket; socket.socket()")
        self.assertEqual(result.returncode, 97)

    def test_cli_builds_a_local_multipart_message_without_transport(self):
        result = self.preview()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Dry run saved to", result.stdout)
        message = BytesParser(policy=policy.default).parsebytes(self.output.read_bytes())
        self.assertFalse(message.defects)
        self.assertEqual(message["To"].addresses[0].addr_spec, "casey@example.org")
        self.assertEqual(message["From"].addresses[0].addr_spec, "alex@example.org")
        self.assertEqual(message["Subject"], "Application for Map Index Assistant")
        body = message.get_body(preferencelist=("plain",)).get_content()
        self.assertIn("Hello Casey Example,", body)
        self.assertIn("Lantern Map Studio", body)
        self.assertIn("twelve hand-drawn grid squares", body)
        attachment, = message.iter_attachments()
        self.assertEqual(attachment.get_filename(), "resume.txt")
        self.assertEqual(attachment.get_payload(decode=True), RESUME.read_bytes())

    def test_refuses_to_overwrite_a_preview(self):
        self.output.write_bytes(b"previous preview")
        result = self.preview()
        self.assertEqual(result.returncode, 1)
        self.assertIn("already exists", result.stderr)
        self.assertEqual(self.output.read_bytes(), b"previous preview")

    def test_invalid_records_leave_no_output(self):
        for key, value in [
            ("to_email", "casey@example.net"),
            ("from_email", "alex@example.net"),
            ("role", "Editor\nBcc: archive@example.org"),
        ]:
            with self.subTest(key=key):
                record = json.loads(RECORD.read_text(encoding="utf-8"))
                record[key] = value
                path = self.directory / "invalid.json"
                path.write_text(json.dumps(record), encoding="utf-8")
                result = self.preview(path)
                self.assertEqual(result.returncode, 1)
                self.assertIn(key, result.stderr)
                self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()

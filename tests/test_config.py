import tempfile
import unittest
from pathlib import Path
from forge_engine.config import ConfigError, load_config

class ConfigTests(unittest.TestCase):
    def config(self, body):
        f = tempfile.NamedTemporaryFile("w", suffix=".conf", delete=False, encoding="utf-8")
        f.write(body)
        f.close()
        path = Path(f.name)
        self.addCleanup(lambda: path.unlink(missing_ok=True))
        return path

    def test_defaults(self):
        cfg = load_config(self.config("[container]\nname=demo\nimage=alpine:latest\n"))
        self.assertEqual(cfg.host_ip, "127.0.0.1")
        self.assertEqual(cfg.restart, "unless-stopped")

    def test_bad_port(self):
        with self.assertRaises(ConfigError):
            load_config(self.config("[container]\nname=demo\nimage=alpine\n[network]\nports=99999:80\n"))

    def test_relative_volume_rejected(self):
        with self.assertRaises(ConfigError):
            load_config(self.config("[container]\nname=demo\nimage=alpine\n[storage]\nvolumes=relative:/data\n"))

    def test_bad_restart_policy(self):
        with self.assertRaises(ConfigError):
            load_config(self.config("[container]\nname=demo\nimage=alpine\nrestart=magical\n"))

if __name__ == "__main__":
    unittest.main()

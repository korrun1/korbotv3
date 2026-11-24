"""Offline regression tests: no broker, network, or trading engine imports."""
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import os
import unittest
from unittest.mock import patch

import yaml
from config_loader import ConfigLoader


class ConfigurationSafetyTests(unittest.TestCase):
    def test_shipped_configuration_loads_from_repository_root(self):
        original = Path.cwd()
        try:
            os.chdir(Path(__file__).resolve().parent)
            with patch.dict(os.environ, {}, clear=True), patch('config_loader.load_dotenv'):
                config = ConfigLoader()
            self.assertEqual(config.get('trading.mode'), 'paper')
            self.assertIn('risk', config.get())
            self.assertIn('logging', config.get())
        finally:
            os.chdir(original)

    def test_save_redacts_secrets_without_mutating_live_configuration(self):
        config = ConfigLoader.__new__(ConfigLoader)
        config.config = {
            'mt5': {'login': 'test-login', 'password': 'test-mt5-secret', 'server': 'demo'},
            'telegram': {'token': 'test-telegram-secret', 'chat_id': 'test-chat-id'},
            'database': {'redis': {'password': 'test-redis-secret', 'host': 'localhost'}},
            'trading': {'mode': 'paper'},
        }
        before = deepcopy(config.config)
        with TemporaryDirectory() as directory:
            destination = Path(directory) / 'config.yaml'
            config.save(destination)
            saved = yaml.safe_load(destination.read_text(encoding='utf-8'))
        self.assertEqual(config.config, before)
        self.assertEqual(saved['mt5']['password'], '***')
        self.assertEqual(saved['mt5']['login'], '***')
        self.assertEqual(saved['telegram']['token'], '***')
        self.assertEqual(saved['telegram']['chat_id'], '***')
        self.assertEqual(saved['database']['redis']['password'], '***')
        self.assertEqual(saved['database']['redis']['host'], 'localhost')

    def test_save_handles_optional_sections_absent(self):
        config = ConfigLoader.__new__(ConfigLoader)
        config.config = {'trading': {'mode': 'paper'}}
        with TemporaryDirectory() as directory:
            destination = Path(directory) / 'config.yaml'
            config.save(destination)
            self.assertEqual(yaml.safe_load(destination.read_text()), config.config)


if __name__ == '__main__':
    unittest.main()

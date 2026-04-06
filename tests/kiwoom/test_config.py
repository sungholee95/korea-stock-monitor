from pathlib import Path

import pytest
import yaml

from ksmonitor.adapters.kiwoom.config import KiwoomConfig


class TestKiwoomConfigFromYaml:
    def _write_temp_yaml(self, tmp_path: Path, data):
        yaml_path = tmp_path / "config.yaml"
        with open(yaml_path, "w") as f:
            yaml.dump(data, f)

        return yaml_path

    def test_load_prod(self, tmp_path: Path):
        data = {
            "my_app_key_name": "paper_app",
            "my_app_sec_name": "paper_sec",
            "my_acct_stock": "99999999",
            "my_acct_future": "88888888",
        }
        config = KiwoomConfig.from_yaml(
            yaml_file=self._write_temp_yaml(tmp_path, data), is_paper=False
        )

        assert config.my_paper_app_key_name is None
        assert config.my_paper_app_sec_name is None
        assert config.my_paper_stock is None
        assert config.my_paper_future is None

        assert config.my_app_key_name == data["my_app_key_name"]
        assert config.my_app_sec_name == data["my_app_sec_name"]
        assert config.my_acct_stock == data["my_acct_stock"]
        assert config.my_acct_future == data["my_acct_future"]

    def test_load_paper(self, tmp_path: Path):
        data = {
            "my_paper_app_key_name": "paper_app",
            "my_paper_app_sec_name": "paper_sec",
            "my_paper_stock": "77777777",
            "my_paper_future": "66666666",
        }
        config = KiwoomConfig.from_yaml(
            yaml_file=self._write_temp_yaml(tmp_path, data), is_paper=True
        )

        assert config.my_app_key_name is None
        assert config.my_app_sec_name is None
        assert config.my_acct_stock is None
        assert config.my_acct_future is None

        assert config.my_paper_app_key_name == data["my_paper_app_key_name"]
        assert config.my_paper_app_sec_name == data["my_paper_app_sec_name"]
        assert config.my_paper_stock == data["my_paper_stock"]
        assert config.my_paper_future == data["my_paper_future"]

    def test_missing_file_raises(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError, match="not found"):
            KiwoomConfig.from_yaml(
                yaml_file=tmp_path / "nonexistent.yaml", is_paper=True
            )

    def test_empty_file_raises(self, tmp_path: Path):
        with pytest.raises(ValueError, match="empty"):
            KiwoomConfig.from_yaml(
                yaml_file=self._write_temp_yaml(tmp_path, data={}), is_paper=True
            )

    def test_missing_required_keys_raises(self, tmp_path: Path):
        data = {"my_app_key_name": "x"}  # missing other prod keys
        with pytest.raises(ValueError, match="Missing required config keys"):
            KiwoomConfig.from_yaml(
                yaml_file=self._write_temp_yaml(tmp_path, data), is_paper=False
            )

    def test_disallowed_keys_rejected(self, tmp_path: Path):
        data = {
            "my_app_key_name": "paper_app",
            "my_app_sec_name": "paper_sec",
            "my_acct_stock": "12345678",
            "my_acct_future": "87654321",
            "url_prod": "https://notallowed.example.com",
        }
        with pytest.raises(ValueError, match="illegal config keys"):
            KiwoomConfig.from_yaml(
                yaml_file=self._write_temp_yaml(tmp_path, data), is_paper=False
            )

    def test_extra_allowed_keys_are_passed_through(self, tmp_path: Path):
        """Paper mode config may include (unused) prod keys and vice versa"""
        data = {
            "my_paper_app_key_name": "paper_app",
            "my_paper_app_sec_name": "paper_sec",
            "my_paper_stock": "99999999",
            "my_paper_future": "88888888",
            # prod keys exist but not required in paper mode
            "my_app_key_name": "prod_app",
            "my_app_sec_name": "prod_sec",
            "my_acct_stock": "77777777",
            "my_acct_future": "66666666",
        }
        cfg = KiwoomConfig.from_yaml(
            yaml_file=self._write_temp_yaml(tmp_path, data), is_paper=True
        )
        assert cfg.my_app_key_name == "prod_app"

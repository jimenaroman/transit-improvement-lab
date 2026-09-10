"""
Regression tests for the seed-data path bug: app/services/data_loader.py and
scripts/seed_scenario_gtfs_links.py used to resolve their JSON files by
climbing parents[] past backend/ into a monorepo-root data/ directory. That
broke on Railway, where only backend/ is built as the service root -- the
climb silently landed inside the production volume mount instead.

Both checks below fail immediately if that pattern is reintroduced.
"""

import shutil
import subprocess
import sys
from pathlib import Path

from app.services import data_loader
from scripts import seed_scenario_gtfs_links

BACKEND_ROOT = Path(__file__).resolve().parents[1]


def test_sample_routes_path_resolves_inside_backend_seed_data():
    assert data_loader.DATA_PATH == BACKEND_ROOT / "seed_data" / "sample-routes.json"
    assert data_loader.DATA_PATH.exists()


def test_scenario_gtfs_links_path_resolves_inside_backend_seed_data():
    assert seed_scenario_gtfs_links.LINKS_PATH == BACKEND_ROOT / "seed_data" / "scenario-gtfs-links.json"
    assert seed_scenario_gtfs_links.LINKS_PATH.exists()


def test_backend_copied_without_monorepo_data_dir_can_still_load_seed_routes(tmp_path):
    """
    Reproduces the actual Railway deployment shape: only backend/'s own
    subdirectories exist, with no sibling ../data anywhere above them.
    """
    copied_backend = tmp_path / "backend"
    ignore_pycache = shutil.ignore_patterns("__pycache__")
    shutil.copytree(BACKEND_ROOT / "app", copied_backend / "app", ignore=ignore_pycache)
    shutil.copytree(BACKEND_ROOT / "seed_data", copied_backend / "seed_data")

    assert not (tmp_path / "data").exists()
    assert not (copied_backend.parent.parent / "data").exists()

    result = subprocess.run(
        [sys.executable, "-c", "from app.services.data_loader import load_routes; print(len(load_routes()))"],
        cwd=copied_backend,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "12"

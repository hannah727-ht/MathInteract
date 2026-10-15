

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def start(**env):

    return subprocess.run([sys.executable, "-c", "import app.config"], cwd=ROOT, capture_output=True, text=True,
                          env={"PATH": os.environ["PATH"], **env})


def test_public_site_needs_a_secret_key():
    result = start(HTTPS_ONLY="true", SECRET_KEY="dev-only-secret")
    assert result.returncode != 0 and "SECRET_KEY must be set" in result.stderr


def test_public_site_starts_with_a_secret_key():
    assert start(HTTPS_ONLY="true", SECRET_KEY="a-long-random-value-0123456789").returncode == 0

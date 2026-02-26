import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ENV = os.environ.copy()


def test_import_resumable_has_no_stdout_side_effects() -> None:
    proc = subprocess.run(
        [sys.executable, "-c", "import resumable"],
        capture_output=True,
        text=True,
        cwd=ROOT,
        env=ENV,
        check=False,
    )
    assert proc.returncode == 0
    assert proc.stdout == ""


def test_import_ast_programs_has_no_stdout_side_effects() -> None:
    proc = subprocess.run(
        [sys.executable, "-c", "import resumable.ast_programs"],
        capture_output=True,
        text=True,
        cwd=ROOT,
        env=ENV,
        check=False,
    )
    assert proc.returncode == 0
    assert proc.stdout == ""

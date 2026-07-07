import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools import get_rollout_revision_count


def test_get_rollout_revision_count_parses_multiple_revisions():
    history_output = (
        "deployment.apps/backend\n"
        "REVISION  CHANGE-CAUSE\n"
        "1         <none>\n"
        "2         <none>\n"
        "3         <none>\n"
    )
    with patch("tools._run", return_value=(history_output, "", 0)):
        assert get_rollout_revision_count("backend", "autohealer") == 3


def test_get_rollout_revision_count_single_revision():
    history_output = (
        "deployment.apps/bad-deploy-simulator\n"
        "REVISION  CHANGE-CAUSE\n"
        "1         <none>\n"
    )
    with patch("tools._run", return_value=(history_output, "", 0)):
        assert get_rollout_revision_count("bad-deploy-simulator", "autohealer") == 1


def test_get_rollout_revision_count_command_failure_returns_zero():
    with patch("tools._run", return_value=("", "error: deployment not found", 1)):
        assert get_rollout_revision_count("missing", "autohealer") == 0

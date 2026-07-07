import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import agent_repairer
from agent_repairer import _pod_status_reason, repair_deployment


def _pod(name, phase="Running", waiting_reason=None, ready=True, restart_count=0):
    return {
        "metadata": {"name": name},
        "spec": {"containers": [{"name": "app"}]},
        "status": {
            "phase": phase,
            "containerStatuses": [
                {
                    "state": {"waiting": {"reason": waiting_reason}} if waiting_reason else {},
                    "restartCount": restart_count,
                }
            ],
            "conditions": [{"type": "Ready", "status": "True" if ready else "False"}],
        },
    }


def test_pod_status_reason_prefers_container_waiting_reason_over_phase():
    # Regression test: Kubernetes often reports Pod phase as "Running" even
    # when the container inside is CrashLoopBackOff. The repairer must not
    # tell Claude "Failure Reason: Running" for a crashing pod.
    pod = _pod("crash-1", phase="Running", waiting_reason="CrashLoopBackOff", ready=False)
    assert _pod_status_reason(pod) == "CrashLoopBackOff"


def test_pod_status_reason_notready_when_no_waiting_reason():
    pod = _pod("readiness-1", phase="Running", ready=False)
    assert _pod_status_reason(pod) == "NotReady"


def test_repair_deployment_downgrades_rollback_to_escalate_when_no_history():
    pods = [_pod("bad-deploy-1", waiting_reason="ImagePullBackOff", ready=False)]

    with patch("agent_repairer.get_rollout_revision_count", return_value=1), \
         patch("agent_repairer.get_pod_logs", return_value=""), \
         patch("agent_repairer.describe_pod", return_value=""), \
         patch("agent_repairer.get_events", return_value=""), \
         patch("agent_repairer.ask_claude", return_value={
             "analysis": "bad image",
             "action": "rollback_deployment",
             "target": "bad-deploy-simulator",
             "reason": "recent image change",
         }), \
         patch("agent_repairer.rollout_undo") as mock_rollout_undo, \
         patch.object(agent_repairer.rag_store, "add_case"):
        result = repair_deployment("bad-deploy-simulator", pods)

    mock_rollout_undo.assert_not_called()
    assert "ESCALATION REQUIRED" in result
    assert "no prior revision available" in result

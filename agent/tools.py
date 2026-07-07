import subprocess
import json


def _run(cmd: list[str]) -> tuple[str, str, int]:
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout, result.stderr, result.returncode


def get_pods(namespace: str = "default") -> dict:
    out, err, code = _run([
        "kubectl", "get", "pods", "-n", namespace,
        "-o", "json"
    ])
    if code != 0:
        return {"error": err}
    return json.loads(out)


def get_pod_logs(pod_name: str, namespace: str = "default", tail: int = 50) -> str:
    out, err, code = _run([
        "kubectl", "logs", pod_name, "-n", namespace,
        f"--tail={tail}", "--previous"
    ])
    if code != 0:
        # try without --previous if pod never started
        out, err, code = _run([
            "kubectl", "logs", pod_name, "-n", namespace, f"--tail={tail}"
        ])
    return out or err


def describe_pod(pod_name: str, namespace: str = "default") -> str:
    out, err, _ = _run(["kubectl", "describe", "pod", pod_name, "-n", namespace])
    return out or err


def restart_pod(pod_name: str, namespace: str = "default") -> str:
    _, err, code = _run(["kubectl", "delete", "pod", pod_name, "-n", namespace])
    if code != 0:
        return f"Failed to delete pod: {err}"
    return f"Pod {pod_name} deleted — Kubernetes will restart it."


def rollout_undo(deployment: str, namespace: str = "default") -> str:
    out, err, code = _run([
        "kubectl", "rollout", "undo", f"deployment/{deployment}", "-n", namespace
    ])
    if code != 0:
        return f"Rollback failed: {err}"
    return out


def rollout_status(deployment: str, namespace: str = "default") -> str:
    out, err, _ = _run([
        "kubectl", "rollout", "status", f"deployment/{deployment}",
        "-n", namespace, "--timeout=30s"
    ])
    return out or err


def deployment_exists(deployment: str, namespace: str = "default") -> bool:
    _, err, code = _run([
        "kubectl", "get", "deployment", deployment, "-n", namespace
    ])
    return code == 0


def get_rollout_revision_count(deployment: str, namespace: str = "default") -> int:
    out, err, code = _run([
        "kubectl", "rollout", "history", f"deployment/{deployment}", "-n", namespace
    ])
    if code != 0:
        return 0
    lines = [line for line in out.strip().splitlines() if line.strip()]
    revisions = [line for line in lines if line[:1].isdigit()]
    return len(revisions)


def get_deployment_replicas(deployment: str, namespace: str = "default") -> int | None:
    out, err, code = _run([
        "kubectl", "get", "deployment", deployment, "-n", namespace,
        "-o", "json"
    ])
    if code != 0:
        return None
    data = json.loads(out)
    return data.get("spec", {}).get("replicas")


def get_deployment_label(deployment: str, label: str, namespace: str = "default") -> str | None:
    out, err, code = _run([
        "kubectl", "get", "deployment", deployment, "-n", namespace,
        "-o", "json"
    ])
    if code != 0:
        return None
    data = json.loads(out)
    return data.get("metadata", {}).get("labels", {}).get(label)


def label_deployment(deployment: str, labels: dict[str, str], namespace: str = "default") -> str:
    args = []
    for key, value in labels.items():
        args.append(f"{key}={value}")
    out, err, code = _run([
        "kubectl", "label", "deployment", deployment, "-n", namespace,
        "--overwrite", *args
    ])
    if code != 0:
        return f"Label deployment failed: {err}"
    return out


def remove_deployment_labels(deployment: str, keys: list[str], namespace: str = "default") -> str:
    args = [f"{key}-" for key in keys]
    out, err, code = _run([
        "kubectl", "label", "deployment", deployment, "-n", namespace,
        "--overwrite", *args
    ])
    if code != 0:
        return f"Remove labels failed: {err}"
    return out


def get_deployments_with_label(label_selector: str, namespace: str = "default") -> list[str]:
    out, err, code = _run([
        "kubectl", "get", "deployments", "-n", namespace,
        "-l", label_selector,
        "-o", "json"
    ])
    if code != 0:
        return []
    data = json.loads(out)
    return [item["metadata"]["name"] for item in data.get("items", [])]


def scale_deployment(deployment: str, replicas: int, namespace: str = "default") -> str:
    out, err, code = _run([
        "kubectl", "scale", "deployment", deployment,
        f"--replicas={replicas}", "-n", namespace
    ])
    if code != 0:
        return f"Scale deployment failed: {err}"
    return out


def get_pods_for_deployment(deployment: str, namespace: str = "default") -> list[dict]:
    data = get_pods(namespace)
    if "error" in data:
        return []
    pods = []
    for pod in data.get("items", []):
        name = pod["metadata"]["name"]
        if get_deployment_from_pod(name, namespace) == deployment:
            pods.append(pod)
    return pods


def get_deployment_from_pod(pod_name: str, namespace: str = "default") -> str | None:
    out, err, code = _run([
        "kubectl", "get", "pod", pod_name, "-n", namespace, "-o", "json"
    ])
    if code != 0:
        return None

    pod = json.loads(out)
    owner_refs = pod.get("metadata", {}).get("ownerReferences", [])
    for owner in owner_refs:
        kind = owner.get("kind")
        name = owner.get("name")
        if kind == "Deployment":
            return name
        if kind == "ReplicaSet":
            rs_out, rs_err, rs_code = _run([
                "kubectl", "get", "replicaset", name, "-n", namespace, "-o", "json"
            ])
            if rs_code != 0:
                continue
            rs = json.loads(rs_out)
            rs_owners = rs.get("metadata", {}).get("ownerReferences", [])
            for rs_owner in rs_owners:
                if rs_owner.get("kind") == "Deployment":
                    return rs_owner.get("name")
    return None


def get_events(namespace: str = "default") -> str:
    out, err, _ = _run([
        "kubectl", "get", "events", "-n", namespace,
        "--sort-by=.lastTimestamp"
    ])
    return out or err


def get_unhealthy_pods(namespace: str = "default") -> list[dict]:
    data = get_pods(namespace)
    if "error" in data:
        return []
    unhealthy = []
    for pod in data.get("items", []):
        name = pod["metadata"]["name"]
        phase = pod["status"].get("phase", "")
        container_statuses = pod["status"].get("containerStatuses", [])
        for cs in container_statuses:
            state = cs.get("state", {})
            waiting = state.get("waiting", {})
            reason = waiting.get("reason", "")
            restart_count = cs.get("restartCount", 0)
            if reason in ("CrashLoopBackOff", "Error", "OOMKilled") or (
                phase == "Pending" and restart_count > 2
            ):
                unhealthy.append({
                    "pod": name,
                    "reason": reason or phase,
                    "restarts": restart_count,
                    "container": cs["name"],
                })
        # check for failed deployments via pod conditions
        conditions = pod["status"].get("conditions", [])
        for cond in conditions:
            if cond.get("type") == "Ready" and cond.get("status") == "False":
                if not any(u["pod"] == name for u in unhealthy):
                    unhealthy.append({
                        "pod": name,
                        "reason": cond.get("reason", "NotReady"),
                        "restarts": 0,
                        "container": "",
                    })
    return unhealthy

import time
import logging
from common import log, NAMESPACE, POLL_INTERVAL
from tools import get_unhealthy_pods, get_deployment_from_pod, restart_pod, label_deployment

MARKER_LABEL = "autohealer/repair-needed"


def mark_for_repair(pod_info: dict) -> None:
    deployment = get_deployment_from_pod(pod_info["pod"], NAMESPACE)
    if not deployment:
        log.warning("No deployment found for pod %s", pod_info["pod"])
        return

    labels = {
        MARKER_LABEL: "true",
        "autohealer/failure-reason": pod_info["reason"],
    }
    result = label_deployment(deployment, labels, NAMESPACE)
    log.info("Marked deployment %s for repair: %s", deployment, result)


def isolate_pod(pod_info: dict) -> None:
    pod_name = pod_info["pod"]
    result = restart_pod(pod_name, NAMESPACE)
    log.info("Isolated pod %s: %s", pod_name, result)


def run_once():
    log.info("Isolator scanning namespace '%s' for unhealthy pods...", NAMESPACE)
    unhealthy = get_unhealthy_pods(NAMESPACE)
    if not unhealthy:
        log.info("No unhealthy pods detected.")
        return

    for pod_info in unhealthy:
        log.warning("Unhealthy pod detected: %s", pod_info)
        isolate_pod(pod_info)
        mark_for_repair(pod_info)


if __name__ == "__main__":
    log.info("Autopilot isolator started. Poll interval: %ds", POLL_INTERVAL)
    while True:
        try:
            run_once()
        except Exception as e:
            log.error("Unexpected error in isolator loop: %s", e)
        time.sleep(POLL_INTERVAL)

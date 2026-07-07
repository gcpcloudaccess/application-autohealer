import os
import time
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from common import log, NAMESPACE, POLL_INTERVAL
from tools import get_unhealthy_pods, get_deployment_from_pod, restart_pod, label_deployment
from event_log import EventLog

MARKER_LABEL = "autohealer/repair-needed"
EVENTS_HTTP_PORT = int(os.getenv("EVENTS_HTTP_PORT", "8002"))
event_log = EventLog()


class EventsRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/events"):
            body = json.dumps(event_log.recent(limit=100)).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)
        elif self.path.startswith("/health"):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status":"ok"}')
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass


def start_events_http_server():
    server = HTTPServer(("0.0.0.0", EVENTS_HTTP_PORT), EventsRequestHandler)
    log.info("Events HTTP server listening on port %d", EVENTS_HTTP_PORT)
    server.serve_forever()


def mark_for_repair(deployment: str, pod_info: dict) -> None:
    if not deployment:
        log.warning("No deployment found to mark for pod %s", pod_info["pod"])
        event_log.add(
            "isolator", "label_failed",
            f"Could not resolve owning deployment for pod {pod_info['pod']} — label not applied.",
            pod=pod_info["pod"],
        )
        return

    labels = {
        MARKER_LABEL: "true",
        "autohealer/failure-reason": pod_info["reason"],
    }
    result = label_deployment(deployment, labels, NAMESPACE)
    log.info("Marked deployment %s for repair: %s", deployment, result)
    event_log.add(
        "isolator", "labeled",
        f"Labeled deployment {deployment} for repair (reason: {pod_info['reason']}).",
        deployment=deployment, reason=pod_info["reason"],
    )


def isolate_pod(pod_info: dict) -> str | None:
    deployment = get_deployment_from_pod(pod_info["pod"], NAMESPACE)
    pod_name = pod_info["pod"]
    result = restart_pod(pod_name, NAMESPACE)
    log.info("Isolated pod %s: %s", pod_name, result)
    event_log.add(
        "isolator", "isolated",
        f"Deleted pod {pod_name} ({pod_info['reason']}); Kubernetes will recreate it.",
        pod=pod_name, deployment=deployment, reason=pod_info["reason"],
    )
    return deployment


def run_once():
    log.info("Isolator scanning namespace '%s' for unhealthy pods...", NAMESPACE)
    unhealthy = get_unhealthy_pods(NAMESPACE)
    if not unhealthy:
        log.info("No unhealthy pods detected.")
        return

    for pod_info in unhealthy:
        log.warning("Unhealthy pod detected: %s", pod_info)
        event_log.add(
            "isolator", "detected",
            f"Unhealthy pod detected: {pod_info['pod']} ({pod_info['reason']}, restarts={pod_info['restarts']}).",
            pod=pod_info["pod"], reason=pod_info["reason"], restarts=pod_info["restarts"],
        )
        deployment = isolate_pod(pod_info)
        mark_for_repair(deployment, pod_info)


if __name__ == "__main__":
    log.info("Autopilot isolator started. Poll interval: %ds", POLL_INTERVAL)
    threading.Thread(target=start_events_http_server, daemon=True).start()
    while True:
        try:
            run_once()
        except Exception as e:
            log.error("Unexpected error in isolator loop: %s", e)
        time.sleep(POLL_INTERVAL)

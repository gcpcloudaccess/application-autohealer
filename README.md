# Application Autohealer

An automated Kubernetes self-healing demo running on GKE. Two agents watch the cluster and use Claude to diagnose and repair failures.

## What's here

- `agent/` — the two agents.
  - `agent_isolator.py` — detects unhealthy pods, isolates them, and flags the deployment for repair.
  - `agent_repairer.py` — diagnoses flagged deployments with Claude and picks one of: `restart_pod`, `rollback_deployment`, `escalate`.
- `backend/` — the Node.js + React admin app (see `backend/README.md`), also the workload used for the rollback demo below.
- `frontend/` — static demo page.
- `k8s/` — manifests for the namespace, app workloads, agents, and the one crash simulator.

## How it works

1. `autopilot-isolator` polls the namespace every `POLL_INTERVAL` seconds and deletes any unhealthy pod it finds.
2. It labels the deployment `autohealer/repair-needed=true`.
3. `autopilot-repairer` sees the label, gathers logs/describe/events, and asks Claude to diagnose it.
4. Claude picks an action:
   - **Recent image/deployment change** → `rollback_deployment` (`kubectl rollout undo`)
   - **Transient crash** → `restart_pod`
   - **Needs a human** (bad config, broken probe, no rollback target, etc.) → `escalate`, label stays for visibility
5. On a successful fix, the label is cleared.

## Demo: 2 scenarios

Endpoint: `http://<backend-EXTERNAL-IP>:8000/` — get the current IP with:
```bash
kubectl get svc -n autohealer backend
```

### 1. Backend rollback (gets fixed)

```bash
kubectl set image deployment/backend backend=gcr.io/auto-app-healer/autopilot-backend:invalidtag -n autohealer

Watch it recover:
```bash
kubectl get pods -n autohealer -l app=backend -w
kubectl logs -n autohealer deployment/autopilot-repairer -f --tail=20 | grep -A3 -i backend
```

**Expected**: `ImagePullBackOff` → isolator flags it → repairer picks `rollback_deployment` → pod comes back `Running 1/1` on the prior image.

Revert anytime with:
```bash
kubectl rollout undo deployment/backend -n autohealer
```

### 2. crash-simulator (restart or escalate)

Already running and cycling — no command needed, just watch:
```bash
kubectl get pods -n autohealer -l app=crash-simulator -w
kubectl logs -n autohealer deployment/autopilot-repairer -f --tail=20 | grep -A5 -i crash-simulator
```

**Expected**: either `Restarted pod ... deleted` or a clean `ESCALATION REQUIRED` — the repairer keeps running either way.

## Watching live

[k9s](https://k9scli.io/) shows both pod status and logs in one interface — no separate terminal windows needed:
```bash
k9s -n autohealer
```
Press `l` on a selected pod to view its logs inline, `Esc` to go back, `/` to filter by name.

Or, plain kubectl in split panes:
```bash
kubectl logs -n autohealer deployment/autopilot-isolator -f --tail=20
kubectl logs -n autohealer deployment/autopilot-repairer -f --tail=20
```

## Automated validation

```bash
cd agent
python validate_simulators.py
```

## Notes

- Deployment-managed pods get recreated automatically when deleted or crashed — that's expected, not a bug.
- Images are pushed to `gcr.io/auto-app-healer/...`; make sure your cluster can pull from there.

## Useful commands

```bash
kubectl get pods -n autohealer
kubectl get deployments -n autohealer
kubectl describe pod <pod> -n autohealer
kubectl logs -n autohealer -l app=autopilot-isolator --tail=50
kubectl logs -n autohealer -l app=autopilot-repairer --tail=50
```

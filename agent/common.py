import os
import json
import logging
import anthropic
from prompts import SYSTEM_PROMPT, build_diagnosis_prompt

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("autopilot-agent")

NAMESPACE = os.getenv("NAMESPACE", "default")
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "30"))
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


def ask_claude(pod_info: dict, logs: str, describe: str, events: str) -> dict:
    user_msg = build_diagnosis_prompt(pod_info, logs, describe, events)
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_msg}],
    )
    raw = response.content[0].text.strip()
    if "```" in raw:
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw)

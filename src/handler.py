import json
import os
import urllib.request
from google import genai

# Clients initialized OUTSIDE the handler function, at module load time.
# This matters: Lambda reuses the same execution environment across
# multiple invocations when it's "warm" (no cold start). Anything defined
# outside handler() — like this client — is created once and reused,
# saving the cost of re-initializing it on every single alert.
gemini_client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
SLACK_WEBHOOK_URL = os.environ["SLACK_WEBHOOK_URL"]


def build_prompt(alert):
    """Turn one Alertmanager alert object into a plain-English prompt."""
    labels = alert.get("labels", {})
    annotations = alert.get("annotations", {})
    alertname = labels.get("alertname", "UnknownAlert")
    severity = labels.get("severity", "unknown")
    status = alert.get("status", "unknown")
    summary = annotations.get("summary", "")
    description = annotations.get("description", "")

    return (
        f"An SRE alert fired.\n"
        f"Alert name: {alertname}\n"
        f"Status: {status}\n"
        f"Severity: {severity}\n"
        f"Summary: {summary}\n"
        f"Description: {description}\n\n"
        f"In 3-4 sentences, written for an on-call engineer: "
        f"(1) explain in plain language what this alert means, "
        f"(2) suggest the most likely root cause, "
        f"(3) suggest one concrete first diagnostic command or dashboard to check."
    )


def get_diagnosis(alert):
    prompt = build_prompt(alert)
    response = gemini_client.models.generate_content(
        model="gemini-3.6-flash",
        contents=prompt,
    )
    return response.text


def post_to_slack(alertname, status, diagnosis):
    color = "#e01e5a" if status == "firing" else "#2eb67d"
    payload = {
        "attachments": [{
            "color": color,
            "title": f"🤖 AI Incident Copilot: {alertname} [{status}]",
            "text": diagnosis,
        }]
    }
    req = urllib.request.Request(
        SLACK_WEBHOOK_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    urllib.request.urlopen(req)


def handler(event, context):
    """
    event is what API Gateway (HTTP API) hands us. Its actual alert
    payload is JSON text sitting in event["body"] (a string, not a
    dict) — API Gateway does not parse the client's JSON for you.
    """
    body = json.loads(event.get("body", "{}"))
    alerts = body.get("alerts", [])

    if not alerts:
        return {"statusCode": 400, "body": "No alerts in payload"}

    for alert in alerts:
        diagnosis = get_diagnosis(alert)
        post_to_slack(
            alertname=alert.get("labels", {}).get("alertname", "UnknownAlert"),
            status=alert.get("status", "unknown"),
            diagnosis=diagnosis,
        )

    return {"statusCode": 200, "body": json.dumps({"processed": len(alerts)})}

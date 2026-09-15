import json
import os
import time
import requests
import urllib.request
from google import genai
from google.genai.types import EmbedContentConfig
from langchain_community.vectorstores import FAISS
from langchain_core.embeddings import Embeddings

gemini_client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
SLACK_WEBHOOK_URL = os.environ["SLACK_WEBHOOK_URL"]


class GeminiEmbeddings(Embeddings):
    def embed_documents(self, texts):
        result = gemini_client.models.embed_content(
            model="gemini-embedding-001",
            contents=texts,
            config=EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT", output_dimensionality=768),
        )
        return [e.values for e in result.embeddings]

    def embed_query(self, text):
        result = gemini_client.models.embed_content(
            model="gemini-embedding-001",
            contents=text,
            config=EmbedContentConfig(task_type="RETRIEVAL_QUERY", output_dimensionality=768),
        )
        return result.embeddings[0].values


# Loaded once, outside handler(), at cold start — same reasoning as the
# Gemini client itself: this is a relatively expensive operation
# (reading two files, deserializing a vector index) you don't want to
# repeat on every single warm invocation.
_embeddings = GeminiEmbeddings()
_faiss_index = FAISS.load_local(
    "faiss_index", _embeddings, allow_dangerous_deserialization=True
)


def retrieve_context(alert_text):
    results = _faiss_index.similarity_search(alert_text, k=2)
    context = "\n---\n".join(r.page_content for r in results)
    print(f"Retrieved context: {context}")   # <-- add this line
    return context

def build_prompt(alert):
    labels = alert.get("labels", {})
    annotations = alert.get("annotations", {})
    alertname = labels.get("alertname", "UnknownAlert")
    severity = labels.get("severity", "unknown")
    status = alert.get("status", "unknown")
    summary = annotations.get("summary", "")
    description = annotations.get("description", "")

    alert_text = f"{alertname} {summary} {description}"
    runbook_context = retrieve_context(alert_text)

    return (
        f"An SRE alert fired.\n"
        f"Alert name: {alertname}\n"
        f"Status: {status}\n"
        f"Severity: {severity}\n"
        f"Summary: {summary}\n"
        f"Description: {description}\n\n"
        f"Relevant runbook context (retrieved from our SLO/runbook documentation):\n"
        f"{runbook_context}\n\n"
        f"Using the runbook context above where relevant, in 3-4 sentences written "
        f"for an on-call engineer: (1) explain what this alert means, "
        f"(2) suggest the most likely root cause, "
        f"(3) suggest one concrete first diagnostic command or dashboard to check, "
        f"citing the runbook if it specifies one."
    )

def send_to_slack(message):
    webhook_url = os.environ["SLACK_WEBHOOK_URL"]
    try:
        requests.post(webhook_url, json={"text": message})
    except Exception as e:
        # Log but don't crash if Slack itself fails
        print(f"Failed to send fallback to Slack: {e}")

def get_diagnosis(alert):
    prompt = build_prompt(alert)
    last_error = None
    for attempt in range(3):
        try:
            response = gemini_client.models.generate_content(
                model="gemini-3.6-flash",
                contents=prompt,
                config={"http_options": {"timeout": 15000}},  # 15s per attempt
            )
            return response.text
        except Exception as e:
            last_error = e
            time.sleep(2 * (attempt + 1))  # backoff
    # If all retries fail, send fallback to Slack
    fallback = f"⚠️ Diagnosis unavailable — Gemini API error: {str(last_error)}"
    send_to_slack(fallback)
    return fallback


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

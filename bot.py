#!/usr/bin/env python3
"""
Vera AI WhatsApp Engagement Engine — Production HTTP Service & Composition Pipeline
"""

from __future__ import annotations
import sys
import os
import time
import json
import threading
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from typing import Optional, Dict, Any, List

from engine.context_store import ContextStore
from engine.composer import EngagementComposer
from engine.conversation_handlers import ConversationHandler
from engine.grounding_validator import GroundingValidator

START_TIME = time.time()
context_store = ContextStore()
conversation_handler = ConversationHandler()


def compose(category: dict, merchant: dict, trigger: dict, customer: dict | None = None) -> dict:
    """
    Core entrypoint per challenge-brief.md §7.1.
    Grounds against the 4 contexts and returns a structured message adhering to output schema.
    """
    msg = EngagementComposer.compose(category, merchant, trigger, customer)
    return msg.to_dict()


DOCS_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Vera AI WhatsApp Engagement Engine — API Documentation</title>
  <style>
    :root {
      --bg: #0b0f19;
      --card-bg: #151e2e;
      --border: #243247;
      --text: #f1f5f9;
      --text-muted: #94a3b8;
      --primary: #6366f1;
      --get-badge: #10b981;
      --post-badge: #3b82f6;
      --code-bg: #0d131f;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      background: var(--bg);
      color: var(--text);
      line-height: 1.6;
      padding: 32px 16px;
    }
    .container { max-width: 900px; margin: 0 auto; }
    header {
      margin-bottom: 32px;
      padding-bottom: 24px;
      border-bottom: 1px solid var(--border);
    }
    .title-row { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; margin-bottom: 8px; }
    h1 { font-size: 26px; font-weight: 700; color: #fff; }
    .badge {
      display: inline-block;
      padding: 3px 10px;
      border-radius: 9999px;
      font-size: 12px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }
    .badge-version { background: #312e81; color: #a5b4fc; }
    .badge-status { background: #064e3b; color: #6ee7b7; }
    p.subtitle { color: var(--text-muted); font-size: 15px; }
    .endpoint-card {
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 20px;
      margin-bottom: 20px;
      box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
    }
    .endpoint-header {
      display: flex;
      align-items: center;
      gap: 12px;
      margin-bottom: 12px;
      flex-wrap: wrap;
    }
    .method {
      padding: 4px 10px;
      border-radius: 6px;
      font-weight: 700;
      font-size: 13px;
      letter-spacing: 0.5px;
    }
    .method-get { background: #065f46; color: #6ee7b7; }
    .method-post { background: #1e40af; color: #93c5fd; }
    .path { font-family: monospace; font-size: 16px; font-weight: 600; color: #fff; }
    .desc { font-size: 14px; color: var(--text-muted); margin-bottom: 14px; }
    .code-block {
      background: var(--code-bg);
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 12px;
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      font-size: 12px;
      color: #38bdf8;
      overflow-x: auto;
      margin-bottom: 10px;
    }
    .label {
      font-size: 11px;
      font-weight: 700;
      text-transform: uppercase;
      color: #cbd5e1;
      letter-spacing: 0.5px;
      margin-bottom: 4px;
    }
    footer {
      text-align: center;
      margin-top: 40px;
      color: var(--text-muted);
      font-size: 13px;
    }
  </style>
</head>
<body>
  <div class="container">
    <header>
      <div class="title-row">
        <h1>Vera AI WhatsApp Engagement Engine</h1>
        <span class="badge badge-version">v2.0.0</span>
        <span class="badge badge-status">Online</span>
      </div>
      <p class="subtitle">Magicpin AI Challenge — Production 4-Context Synthesis Pipeline with hard-fact grounding and zero hallucinations.</p>
    </header>

    <!-- Healthz -->
    <div class="endpoint-card">
      <div class="endpoint-header">
        <span class="method method-get">GET</span>
        <span class="path">/v1/healthz</span>
      </div>
      <p class="desc">Liveness probe polled by the judge harness every 60 seconds.</p>
      <div class="label">Sample Response (200 OK)</div>
      <pre class="code-block">{ "status": "ok", "uptime_seconds": 3600, "contexts_loaded": { "category": 5, "merchant": 50, "customer": 200, "trigger": 100 } }</pre>
    </div>

    <!-- Metadata -->
    <div class="endpoint-card">
      <div class="endpoint-header">
        <span class="method method-get">GET</span>
        <span class="path">/v1/metadata</span>
      </div>
      <p class="desc">Returns model identity, engineering approach, and author contact.</p>
      <div class="label">Sample Response (200 OK)</div>
      <pre class="code-block">{
  "team_name": "Magicpin Staff AI Architects",
  "model": "vera-neural-grounded-v2",
  "approach": "4-Context Synthesis Pipeline with hard-fact grounding validator...",
  "version": "2.0.0"
}</pre>
    </div>

    <!-- Context -->
    <div class="endpoint-card">
      <div class="endpoint-header">
        <span class="method method-post">POST</span>
        <span class="path">/v1/context</span>
      </div>
      <p class="desc">Ingests context updates idempotently across category, merchant, trigger, and customer scopes.</p>
      <div class="label">Sample Request Body</div>
      <pre class="code-block">{
  "scope": "category" | "merchant" | "customer" | "trigger",
  "context_id": "dentists",
  "version": 1,
  "payload": { ... }
}</pre>
      <div class="label">Sample Response (200 OK)</div>
      <pre class="code-block">{ "accepted": true, "ack_id": "ack_abc123", "stored_at": "2026-04-26T10:00:00.123Z" }</pre>
    </div>

    <!-- Tick -->
    <div class="endpoint-card">
      <div class="endpoint-header">
        <span class="method method-post">POST</span>
        <span class="path">/v1/tick</span>
      </div>
      <p class="desc">Periodic evaluation tick where the engine inspects active triggers and outputs proactive engagement messages.</p>
      <div class="label">Sample Request Body</div>
      <pre class="code-block">{ "now": "2026-04-26T10:30:00Z", "available_triggers": ["trg_recall_priya"] }</pre>
      <div class="label">Sample Response (200 OK)</div>
      <pre class="code-block">{
  "actions": [
    {
      "conversation_id": "conv_001",
      "merchant_id": "m_001",
      "send_as": "vera",
      "body": "Priya, Dr. Meera noticed your 6-month checkup is due...",
      "cta": "open_ended",
      "rationale": "Clinical recall anchor with loss aversion lever"
    }
  ]
}</pre>
    </div>

    <!-- Reply -->
    <div class="endpoint-card">
      <div class="endpoint-header">
        <span class="method method-post">POST</span>
        <span class="path">/v1/reply</span>
      </div>
      <p class="desc">Processes incoming customer/merchant responses through the multi-turn state machine (send, wait, or end).</p>
      <div class="label">Sample Request Body</div>
      <pre class="code-block">{ "conversation_id": "conv_001", "merchant_id": "m_001", "message": "Yes, please book 5 PM", "turn_number": 2 }</pre>
      <div class="label">Sample Response (200 OK)</div>
      <pre class="code-block">{
  "action": "send",
  "body": "Slot reserved for 5 PM tomorrow. See you at the clinic!",
  "cta": "open_ended",
  "rationale": "High-intent booking transition; action mode confirmed"
}</pre>
    </div>

    <footer>
      Magicpin AI Challenge &bull; Vera WhatsApp Engagement Engine
    </footer>
  </div>
</body>
</html>
"""


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Multi-threaded HTTP server for high concurrency and zero blocking."""
    daemon_threads = True
    allow_reuse_address = True


class VeraRequestHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, format: str, *args: Any):
        # Concise logging
        sys.stderr.write(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] {self.command} {self.path} - {args[0] if args else ''}\n")

    def _send_json(self, status_code: int, data: Dict[str, Any]):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "keep-alive")
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, status_code: int, html_str: str):
        body = html_str.encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "keep-alive")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.split("?")[0].rstrip("/")

        if path in ("", "/"):
            uptime = int(time.time() - START_TIME)
            counts = context_store.counts_by_scope()
            self._send_json(200, {
                "service": "Vera AI WhatsApp Engagement Engine",
                "status": "online",
                "version": "2.0.0",
                "uptime_seconds": uptime,
                "endpoints": {
                    "docs": "GET /docs",
                    "healthz": "GET /v1/healthz",
                    "metadata": "GET /v1/metadata",
                    "context": "POST /v1/context",
                    "tick": "POST /v1/tick",
                    "reply": "POST /v1/reply"
                },
                "contexts_loaded": counts
            })
            return

        elif path == "/docs":
            self._send_html(200, DOCS_HTML)
            return

        elif path == "/v1/healthz":
            uptime = int(time.time() - START_TIME)
            counts = context_store.counts_by_scope()
            self._send_json(200, {
                "status": "ok",
                "uptime_seconds": uptime,
                "contexts_loaded": counts
            })
            return

        elif path == "/v1/metadata":
            self._send_json(200, {
                "team_name": "Magicpin Staff AI Architects",
                "team_members": ["Staff AI Architect"],
                "model": "vera-neural-grounded-v2",
                "approach": "4-Context Synthesis Pipeline with hard-fact grounding validator, dynamic vertical voice adaptation, and zero-hallucination constraint enforcement",
                "contact_email": "ai-challenge@magicpin.in",
                "version": "2.0.0",
                "submitted_at": "2026-04-26T08:00:00Z"
            })
            return

        self._send_json(404, {"error": "Not Found", "path": self.path})

    def do_POST(self):
        path = self.path.split("?")[0].rstrip("/")
        content_length = int(self.headers.get("Content-Length", 0))

        try:
            body_bytes = self.rfile.read(content_length)
            body_data = json.loads(body_bytes.decode("utf-8")) if body_bytes else {}
        except Exception as e:
            self._send_json(400, {"accepted": False, "reason": "invalid_json", "error": str(e)})
            return

        # -------------------------------------------------------------
        # Endpoint 1: /v1/context (Context Ingestion & Idempotency)
        # -------------------------------------------------------------
        if path == "/v1/context":
            scope = body_data.get("scope")
            context_id = body_data.get("context_id")
            version = body_data.get("version")
            payload = body_data.get("payload")

            if not (scope and context_id and version is not None and payload is not None):
                self._send_json(400, {
                    "accepted": False,
                    "reason": "missing_required_fields",
                    "details": "scope, context_id, version, and payload are required"
                })
                return

            if scope not in ("category", "merchant", "customer", "trigger"):
                self._send_json(400, {
                    "accepted": False,
                    "reason": "invalid_scope",
                    "details": f"Unknown scope: {scope}"
                })
                return

            accepted, reason, cur_version = context_store.push_context(
                scope=scope,
                context_id=context_id,
                version=int(version),
                payload=payload
            )

            if not accepted:
                self._send_json(409, {
                    "accepted": False,
                    "reason": reason,
                    "current_version": cur_version
                })
                return

            self._send_json(200, {
                "accepted": True,
                "ack_id": f"ack_{context_id}_v{version}",
                "stored_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            })
            return

        # -------------------------------------------------------------
        # Endpoint 2: /v1/tick (Proactive Periodic Composition)
        # -------------------------------------------------------------
        elif path == "/v1/tick":
            available_triggers = body_data.get("available_triggers", [])
            actions = []

            for trg_id in available_triggers:
                trg_payload = context_store.get_context("trigger", trg_id)
                if not trg_payload:
                    continue

                merchant_id = trg_payload.get("merchant_id")
                if not merchant_id:
                    continue

                merchant_payload = context_store.get_context("merchant", merchant_id)
                if not merchant_payload:
                    continue

                cat_slug = merchant_payload.get("category_slug")
                category_payload = context_store.get_context("category", cat_slug) if cat_slug else None
                if not category_payload:
                    continue

                customer_id = trg_payload.get("customer_id")
                customer_payload = context_store.get_context("customer", customer_id) if customer_id else None

                composed_msg = EngagementComposer.compose(
                    category=category_payload,
                    merchant=merchant_payload,
                    trigger=trg_payload,
                    customer=customer_payload
                )

                action_dict = composed_msg.to_dict()
                actions.append(action_dict)

            self._send_json(200, {"actions": actions})
            return

        # -------------------------------------------------------------
        # Endpoint 3: /v1/reply (Multi-turn Response Handling)
        # -------------------------------------------------------------
        elif path == "/v1/reply":
            conv_id = body_data.get("conversation_id", f"conv_{int(time.time())}")
            merchant_id = body_data.get("merchant_id")
            customer_id = body_data.get("customer_id")
            from_role = body_data.get("from_role", "merchant")
            message = body_data.get("message", "")
            turn_number = body_data.get("turn_number", 1)

            reply_response = conversation_handler.handle_reply(
                conversation_id=conv_id,
                merchant_id=merchant_id,
                customer_id=customer_id,
                from_role=from_role,
                message=message,
                turn_number=turn_number,
                context_store=context_store
            )

            self._send_json(200, reply_response)
            return

        # -------------------------------------------------------------
        # Optional: /v1/teardown (Wipe test state)
        # -------------------------------------------------------------
        elif path == "/v1/teardown":
            context_store.clear()
            self._send_json(200, {"status": "cleared"})
            return

        self._send_json(404, {"error": "Not Found", "path": self.path})


def run_server(port: int = 8080, host: str = "0.0.0.0"):
    server = ThreadedHTTPServer((host, port), VeraRequestHandler)
    print(f"[*] Vera AI Engagement Engine listening on {host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[*] Shutting down server...")
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        port = int(sys.argv[1])
    run_server(port=port)

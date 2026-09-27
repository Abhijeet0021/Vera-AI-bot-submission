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
                    "healthz": "GET /v1/healthz",
                    "metadata": "GET /v1/metadata",
                    "context": "POST /v1/context",
                    "tick": "POST /v1/tick",
                    "reply": "POST /v1/reply"
                },
                "contexts_loaded": counts
            })
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

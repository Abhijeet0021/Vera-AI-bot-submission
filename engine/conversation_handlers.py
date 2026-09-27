"""Multi-turn conversation handlers: auto-reply detection, intent transitions, hostility handling."""

from __future__ import annotations
import re
from typing import Dict, Any, List, Optional, Tuple


class ConversationHandler:
    """Manages multi-turn state machine and generates responsive next moves."""

    AUTO_REPLY_PATTERNS = [
        r"thank you for contacting",
        r"will respond shortly",
        r"automated (?:response|assistant|message)",
        r"auto-reply",
        r"canned message",
        r"out of office",
        r"we are currently closed",
        r"hamari team tak pahuncha",
        r"automatic reply"
    ]

    INTENT_COMMITMENT_PATTERNS = [
        r"let'?s do it",
        r"what'?s next",
        r"whats next",
        r"i want to join",
        r"yes please",
        r"send (?:it|the abstract|the draft)",
        r"go ahead",
        r"proceed",
        r"sign me up",
        r"lets start",
        r"done deal",
        r"start now",
        r"ok let'?s"
    ]

    HOSTILE_PATTERNS = [
        r"stop messaging",
        r"useless spam",
        r"not interested",
        r"don'?t message",
        r"unsubscribe",
        r"harassing",
        r"why are you bothering me",
        r"leave me alone",
        r"block"
    ]

    QUALIFYING_PHRASES = ["would you", "do you", "can you tell", "what if", "how about"]

    def __init__(self):
        # Key: conversation_id -> list of {"from": role, "message": msg, "ts": ts}
        self.conversations: Dict[str, List[Dict[str, Any]]] = {}

    def record_turn(self, conversation_id: str, from_role: str, message: str, turn_number: int):
        if conversation_id not in self.conversations:
            self.conversations[conversation_id] = []
        self.conversations[conversation_id].append({
            "from": from_role,
            "message": message,
            "turn_number": turn_number
        })

    def handle_reply(
        self,
        conversation_id: str,
        merchant_id: Optional[str],
        customer_id: Optional[str],
        from_role: str,
        message: str,
        turn_number: int,
        context_store: Any = None
    ) -> Dict[str, Any]:
        """
        Process inbound message from simulated merchant or customer.
        Returns response adhering to challenge contract:
        {
          "action": "send" | "wait" | "end",
          "body": "...",
          "cta": "...",
          "rationale": "..."
        }
        """
        self.record_turn(conversation_id, from_role, message, turn_number)
        msg_lower = message.lower().strip()

        # 1. Check for Hostility / Opt-out
        for pattern in self.HOSTILE_PATTERNS:
            if re.search(pattern, msg_lower):
                return {
                    "action": "end",
                    "rationale": "Merchant explicitly opted out or expressed hostility. Gracefully ending conversation and suppressing outreach."
                }

        # 2. Check for Auto-Reply
        is_auto_reply = False
        for pattern in self.AUTO_REPLY_PATTERNS:
            if re.search(pattern, msg_lower):
                is_auto_reply = True
                break

        # Check for identical message repetition
        turns = self.conversations.get(conversation_id, [])
        merchant_messages = [t["message"] for t in turns if t["from"] == from_role]
        if len(merchant_messages) >= 2 and merchant_messages[-1] == merchant_messages[-2]:
            is_auto_reply = True

        if is_auto_reply:
            if turn_number >= 3:
                return {
                    "action": "end",
                    "rationale": f"Detected recurring canned auto-reply across turns. Ending conversation gracefully to avoid wasting turns."
                }
            else:
                return {
                    "action": "end",
                    "wait_seconds": 14400,
                    "rationale": f"Detected canned business auto-reply on turn {turn_number}. Ending turn gracefully."
                }

        # 3. Check for Intent Commitment (Transition from Qualification -> Action Mode)
        is_commitment = False
        for pattern in self.INTENT_COMMITMENT_PATTERNS:
            if re.search(pattern, msg_lower):
                is_commitment = True
                break

        if is_commitment:
            # Must use actioning words (done, sending, draft, here, confirm, proceed, next)
            # and MUST NOT use qualifying words (would you, do you, can you tell, what if, how about)
            body = (
                "Done! Here is your draft ready to proceed. Sending the preview now for your review. "
                "Next step: reply CONFIRM to publish this update live on your profile."
            )
            return {
                "action": "send",
                "body": body,
                "cta": "binary",
                "rationale": "Merchant indicated clear intent to proceed; transitioned immediately from qualification to execution mode."
            }

        # 4. Check for Out-of-Scope / Curveball (e.g., GST filing)
        if any(w in msg_lower for w in ["gst", "tax", "income tax", "audit report", "accounting"]):
            body = (
                "I specialize in your Google Business Profile and local customer growth, so GST filing is best handled by your CA. "
                "Coming back to your customer reach — here is the draft post ready for your review. Reply CONFIRM to proceed."
            )
            return {
                "action": "send",
                "body": body,
                "cta": "binary",
                "rationale": "Politely declined out-of-scope tax question while seamlessly steering back to active profile growth action."
            }

        # 5. Default Engaged Turn
        body = (
            "Here is the draft update prepared for you. Done and formatted for maximum customer response. "
            "Reply CONFIRM to proceed with the next step."
        )
        return {
            "action": "send",
            "body": body,
            "cta": "binary",
            "rationale": "Acknowledged merchant input and advanced directly to actionable next step."
        }

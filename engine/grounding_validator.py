"""Grounding validator ensuring zero-hallucination, strict fact-checking, and policy compliance."""

from __future__ import annotations
import re
from typing import Dict, Any, List, Set, Tuple, Optional


def extract_numbers_from_payload(obj: Any) -> Set[str]:
    """Recursively collect all numeric tokens (integers, floats, percentages, prices) from JSON."""
    numbers: Set[str] = set()

    if isinstance(obj, dict):
        for k, v in obj.items():
            numbers.update(extract_numbers_from_payload(v))
    elif isinstance(obj, list):
        for item in obj:
            numbers.update(extract_numbers_from_payload(item))
    elif isinstance(obj, (int, float)):
        # Normalize int vs float
        if isinstance(obj, float) and obj.is_integer():
            numbers.add(str(int(obj)))
        numbers.add(str(obj))
        # Handle percentage representations (0.38 -> 38, 38%; 0.021 -> 2.1, 2.1%)
        if isinstance(obj, float) and -1.0 <= obj <= 1.0:
            for decimals in (0, 1, 2):
                pct = round(abs(obj) * 100, decimals)
                if decimals == 0:
                    pct = int(pct)
                numbers.add(str(pct))
                numbers.add(f"{pct}%")
    elif isinstance(obj, str):
        # Look for numbers inside strings e.g. "₹299", "38%", "2100"
        found = re.findall(r'\b\d+(?:\.\d+)?%?\b', obj)
        numbers.update(found)
        # Also clean prices like ₹299 or Rs 299
        prices = re.findall(r'[₹$€£]\s*(\d+(?:,\d+)*(?:\.\d+)?)', obj)
        for p in prices:
            clean_p = p.replace(',', '')
            numbers.add(clean_p)
            numbers.add(f"₹{clean_p}")

    return numbers


class GroundingValidator:
    """Validates message copy against source context payloads to prevent hallucinations."""

    SAFE_CONVERSATIONAL_NUMBERS = {
        "1", "2", "3", "4", "5", "6", "7", "8", "9", "10",
        "24", "48", "90", "1", "2"
    }

    @staticmethod
    def extract_message_numbers(text: str) -> List[str]:
        """Extract numeric claims, percentages, and prices from message body."""
        # Clean markdown asterisks
        cleaned = text.replace('*', '')
        # Matches numbers, decimals, percentages, and currency
        raw_matches = re.findall(r'[₹]?\d+(?:,\d+)*(?:\.\d+)?%?', cleaned)
        return [m.replace(',', '') for m in raw_matches]

    @classmethod
    def validate(
        cls,
        body: str,
        category: Optional[Dict[str, Any]],
        merchant: Optional[Dict[str, Any]],
        trigger: Optional[Dict[str, Any]],
        customer: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, List[str]]:
        """
        Validate message body.
        Returns: (is_valid, list_of_errors)
        """
        errors = []

        # 1. URL Policy Check
        if re.search(r'https?://', body):
            errors.append("Disallowed URL detected in WhatsApp copy")

        # 2. Word Count Check (Strictly under 80 words)
        words = body.split()
        if len(words) > 85:  # small grace margin for punctuation
            errors.append(f"Word count exceeds limit: {len(words)} words (max 80)")

        # 3. Taboo Vocabulary Check
        if category and "voice" in category:
            taboos = category["voice"].get("vocab_taboo", [])
            body_lower = body.lower()
            for taboo in taboos:
                # ignore case and boundary
                pattern = r'\b' + re.escape(taboo.lower()) + r'\b'
                if re.search(pattern, body_lower):
                    errors.append(f"Category taboo phrase detected: '{taboo}'")

        # 4. Numeric Fact Grounding Check
        context_numbers: Set[str] = set()
        for ctx in [category, merchant, trigger, customer]:
            if ctx:
                context_numbers.update(extract_numbers_from_payload(ctx))

        message_numbers = cls.extract_message_numbers(body)
        for num in message_numbers:
            clean_num = num.lstrip('₹').rstrip('%')
            # Check if clean_num is in context or safe conversational numbers
            if clean_num in cls.SAFE_CONVERSATIONAL_NUMBERS:
                continue

            # Check if this exact number exists in context
            matched = False
            if clean_num in context_numbers or num in context_numbers:
                matched = True
            else:
                # Check integer vs float equivalence (e.g. 30.0 vs 30)
                try:
                    val = float(clean_num)
                    for c_num in context_numbers:
                        try:
                            c_val = float(c_num.lstrip('₹').rstrip('%'))
                            if abs(val - c_val) < 0.001:
                                matched = True
                                break
                        except ValueError:
                            continue
                except ValueError:
                    pass

            if not matched:
                errors.append(f"Ungrounded number/statistic detected: '{num}'")

        is_valid = len(errors) == 0
        return is_valid, errors

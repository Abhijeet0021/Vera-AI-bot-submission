"""Voice and Cultural Adapter for vertical-specific personas and language code-mixing."""

from __future__ import annotations
from typing import Dict, Any, List, Optional


class VoiceAdapter:
    """Adapts tone, vocabulary, salutations, and phrasing according to vertical and language preferences."""

    @staticmethod
    def get_salutation(merchant: Dict[str, Any], category_slug: str, customer: Optional[Dict[str, Any]] = None) -> str:
        """Generate culturally appropriate salutation."""
        # Customer-facing
        if customer:
            cust_name = customer.get("identity", {}).get("name", "there")
            # If customer has a title or senior indicator like 'Sharma ji'
            if "parent:" in cust_name:
                cust_name = cust_name.split("(")[0].strip()
            return f"Hi {cust_name}"

        # Merchant-facing
        identity = merchant.get("identity", {})
        owner_first = identity.get("owner_first_name", "")
        biz_name = identity.get("name", "")

        if category_slug == "dentists":
            if owner_first:
                prefix = "Dr. " if not owner_first.lower().startswith("dr") else ""
                return f"{prefix}{owner_first}"
            return "Doctor"
        elif category_slug == "pharmacies":
            # If Hindi preference and senior/pharmacist, respectful
            langs = identity.get("languages", [])
            if "hi" in langs and owner_first:
                return f"{owner_first} ji"
            return owner_first if owner_first else biz_name
        else:
            return owner_first if owner_first else biz_name

    @staticmethod
    def is_hinglish(merchant: Dict[str, Any], customer: Optional[Dict[str, Any]] = None) -> bool:
        """Determine if Hinglish code-mixing is requested."""
        if customer:
            pref = customer.get("identity", {}).get("language_pref", "").lower()
            return "hi" in pref

        identity = merchant.get("identity", {})
        langs = identity.get("languages", [])
        return "hi" in langs or "hi-en mix" in langs

    @staticmethod
    def get_category_persona(category_slug: str) -> Dict[str, Any]:
        """Vertical-specific style directives."""
        personas = {
            "dentists": {
                "role": "Clinical peer-to-peer collaborator",
                "lexicon": ["clinical recall", "protocol", "caries", "cohort", "abstract", "guidelines"],
                "avoid": ["discount", "flat off", "bazaar", "cheap", "cure", "guaranteed"],
                "format": "Evidence-grounded, citing trials/abstracts with sample size N and official source.",
            },
            "gyms": {
                "role": "Performance coach and fitness operations partner",
                "lexicon": ["active members", "retention", "cohort", "HIIT", "utilization", "conditioning"],
                "avoid": ["guilt", "shame", "lazy", "fat"],
                "format": "High-energy, discipline-focused, supportive momentum capture.",
            },
            "salons": {
                "role": "Aesthetic-first salon growth strategist",
                "lexicon": ["appointment density", "slots", "prep program", "bridal", "styling", "care"],
                "avoid": ["cheap haircut", "discount scheme"],
                "format": "Warm, aesthetic, visually appealing, appointment-focused.",
            },
            "restaurants": {
                "role": "F&B operator-to-operator advisor",
                "lexicon": ["covers", "turnover", "delivery radius", "packaging", "rush hours", "match day"],
                "avoid": ["generic food discount"],
                "format": "Fast-paced, appetite-driven, operational throughput focus.",
            },
            "pharmacies": {
                "role": "Trust-first compliance and pharmacy operations advisor",
                "lexicon": ["chronic-Rx", "refill adherence", "molecule", "batch", "recall", "dosage"],
                "avoid": ["promotional hype", "sale on medicines"],
                "format": "Consultative, precise, compliance-safe, respectful.",
            }
        }
        return personas.get(category_slug, {
            "role": "Local commerce growth partner",
            "lexicon": ["footfall", "conversion", "retention"],
            "avoid": ["spam"],
            "format": "Professional, actionable, high ROI.",
        })

"""Duplicate Watcher Agent - Detects and helps merge duplicate contacts.

Responsibilities:
- Real-time duplicate detection on new contacts
- Daily bulk duplicate scan across entire database
- Fuzzy matching on name + company
- Exact matching on email domain + phone
- Merge recommendations with confidence scores
"""

from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from difflib import SequenceMatcher
from collections import defaultdict

from src.agents.base import BaseAgent
from src.logger import get_logger

logger = get_logger(__name__)


@dataclass
class DuplicatePair:
    """A potential duplicate pair."""
    contact_id_a: str
    contact_id_b: str
    match_score: float  # 0-1 confidence
    match_reasons: List[str]
    recommended_primary: str  # Which one to keep
    merge_actions: List[str]  # What to merge from secondary


class DuplicateWatcherAgent(BaseAgent):
    """Detects duplicate contacts across the database.
    
    Matching Strategies:
    1. Exact email match (100% confidence)
    2. Same domain + similar name (85%+ confidence)
    3. Same phone number (90% confidence)
    4. Same company + similar name (70%+ confidence)
    5. Fuzzy name + fuzzy company (50%+ confidence, needs review)
    """
    
    # Minimum scores for different match types
    MIN_NAME_SIMILARITY = 0.7
    MIN_COMPANY_SIMILARITY = 0.6
    MIN_OVERALL_CONFIDENCE = 0.5
    
    def __init__(self):
        super().__init__(
            name="DuplicateWatcherAgent",
            description="Detects and manages duplicate contacts"
        )
    
    async def validate_input(self, context: Dict[str, Any]) -> bool:
        """Validate input based on action."""
        action = context.get("action", "check_single")
        if action == "check_single":
            return "contact" in context
        elif action == "scan_batch":
            return "contacts" in context and isinstance(context["contacts"], list)
        elif action == "find_duplicates_for":
            return "contact" in context and "all_contacts" in context
        return True
    
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute duplicate detection based on action."""
        action = context.get("action", "check_single")
        
        if action == "check_single":
            # Check if a new contact duplicates any existing
            contact = context.get("contact", {})
            all_contacts = context.get("all_contacts", [])
            duplicates = self._find_duplicates(contact, all_contacts)
            
            return {
                "status": "success",
                "contact_email": contact.get("email"),
                "has_duplicates": len(duplicates) > 0,
                "duplicates": duplicates,
            }
        
        elif action == "scan_batch":
            # Full scan of all contacts for duplicates
            contacts = context.get("contacts", [])
            duplicate_groups = self._scan_for_duplicates(contacts)
            
            return {
                "status": "success",
                "total_contacts": len(contacts),
                "duplicate_groups": len(duplicate_groups),
                "affected_contacts": sum(len(g["contacts"]) for g in duplicate_groups),
                "groups": duplicate_groups,
            }
        
        elif action == "recommend_merge":
            # Recommend which contact to keep and what to merge
            contact_a = context.get("contact_a", {})
            contact_b = context.get("contact_b", {})
            recommendation = self._recommend_merge(contact_a, contact_b)
            
            return {
                "status": "success",
                **recommendation,
            }
        
        return {"status": "error", "error": f"Unknown action: {action}"}
    
    def _find_duplicates(
        self, 
        contact: Dict[str, Any], 
        all_contacts: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Find potential duplicates for a single contact."""
        duplicates = []
        contact_id = contact.get("id", "new")
        email = (contact.get("email") or "").lower()
        phone = self._normalize_phone(contact.get("phone") or "")
        name = self._normalize_name(contact)
        company = (contact.get("company") or "").lower().strip()
        domain = email.split("@")[1] if "@" in email else ""
        
        for other in all_contacts:
            other_id = other.get("id")
            if other_id == contact_id:
                continue
            
            other_email = (other.get("email") or "").lower()
            other_phone = self._normalize_phone(other.get("phone") or "")
            other_name = self._normalize_name(other)
            other_company = (other.get("company") or "").lower().strip()
            other_domain = other_email.split("@")[1] if "@" in other_email else ""
            
            score, reasons = self._calculate_match_score(
                email, other_email,
                phone, other_phone,
                name, other_name,
                company, other_company,
                domain, other_domain,
            )
            
            if score >= self.MIN_OVERALL_CONFIDENCE:
                duplicates.append({
                    "contact_id": other_id,
                    "email": other.get("email"),
                    "name": f"{other.get('firstname', '')} {other.get('lastname', '')}".strip(),
                    "company": other.get("company"),
                    "match_score": round(score, 2),
                    "match_reasons": reasons,
                })
        
        # Sort by score descending
        duplicates.sort(key=lambda x: x["match_score"], reverse=True)
        return duplicates
    
    def _scan_for_duplicates(
        self, 
        contacts: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Scan all contacts for duplicate groups."""
        # Group by email domain for efficiency
        domain_groups = defaultdict(list)
        for contact in contacts:
            email = (contact.get("email") or "").lower()
            domain = email.split("@")[1] if "@" in email else "unknown"
            domain_groups[domain].append(contact)
        
        # Also group by company
        company_groups = defaultdict(list)
        for contact in contacts:
            company = (contact.get("company") or "").lower().strip()
            if company:
                company_groups[company].append(contact)
        
        # Find duplicates within groups
        found_pairs = set()  # (id_a, id_b) tuples to avoid duplicates
        duplicate_groups = []
        
        # Check within domain groups
        for domain, group in domain_groups.items():
            if len(group) < 2:
                continue
            
            for i, contact_a in enumerate(group):
                for contact_b in group[i+1:]:
                    pair_key = tuple(sorted([contact_a.get("id"), contact_b.get("id")]))
                    if pair_key in found_pairs:
                        continue
                    
                    score, reasons = self._compare_contacts(contact_a, contact_b)
                    if score >= self.MIN_OVERALL_CONFIDENCE:
                        found_pairs.add(pair_key)
                        duplicate_groups.append({
                            "contacts": [
                                {
                                    "id": contact_a.get("id"),
                                    "email": contact_a.get("email"),
                                    "name": f"{contact_a.get('firstname', '')} {contact_a.get('lastname', '')}".strip(),
                                },
                                {
                                    "id": contact_b.get("id"),
                                    "email": contact_b.get("email"),
                                    "name": f"{contact_b.get('firstname', '')} {contact_b.get('lastname', '')}".strip(),
                                },
                            ],
                            "match_score": round(score, 2),
                            "match_reasons": reasons,
                        })
        
        # Check within company groups (for different email domains)
        for company, group in company_groups.items():
            if len(group) < 2:
                continue
            
            for i, contact_a in enumerate(group):
                for contact_b in group[i+1:]:
                    pair_key = tuple(sorted([contact_a.get("id"), contact_b.get("id")]))
                    if pair_key in found_pairs:
                        continue
                    
                    score, reasons = self._compare_contacts(contact_a, contact_b)
                    if score >= self.MIN_OVERALL_CONFIDENCE:
                        found_pairs.add(pair_key)
                        duplicate_groups.append({
                            "contacts": [
                                {
                                    "id": contact_a.get("id"),
                                    "email": contact_a.get("email"),
                                    "name": f"{contact_a.get('firstname', '')} {contact_a.get('lastname', '')}".strip(),
                                },
                                {
                                    "id": contact_b.get("id"),
                                    "email": contact_b.get("email"),
                                    "name": f"{contact_b.get('firstname', '')} {contact_b.get('lastname', '')}".strip(),
                                },
                            ],
                            "match_score": round(score, 2),
                            "match_reasons": reasons,
                        })
        
        # Sort by score
        duplicate_groups.sort(key=lambda x: x["match_score"], reverse=True)
        return duplicate_groups
    
    def _compare_contacts(
        self, 
        contact_a: Dict[str, Any], 
        contact_b: Dict[str, Any]
    ) -> Tuple[float, List[str]]:
        """Compare two contacts and return match score + reasons."""
        email_a = (contact_a.get("email") or "").lower()
        email_b = (contact_b.get("email") or "").lower()
        phone_a = self._normalize_phone(contact_a.get("phone") or "")
        phone_b = self._normalize_phone(contact_b.get("phone") or "")
        name_a = self._normalize_name(contact_a)
        name_b = self._normalize_name(contact_b)
        company_a = (contact_a.get("company") or "").lower().strip()
        company_b = (contact_b.get("company") or "").lower().strip()
        domain_a = email_a.split("@")[1] if "@" in email_a else ""
        domain_b = email_b.split("@")[1] if "@" in email_b else ""
        
        return self._calculate_match_score(
            email_a, email_b,
            phone_a, phone_b,
            name_a, name_b,
            company_a, company_b,
            domain_a, domain_b,
        )
    
    def _calculate_match_score(
        self,
        email_a: str, email_b: str,
        phone_a: str, phone_b: str,
        name_a: str, name_b: str,
        company_a: str, company_b: str,
        domain_a: str, domain_b: str,
    ) -> Tuple[float, List[str]]:
        """Calculate match score between two contacts."""
        reasons = []
        scores = []
        
        # Exact email match = definite duplicate
        if email_a and email_b and email_a == email_b:
            return 1.0, ["Exact email match"]
        
        # Same phone = very likely duplicate
        if phone_a and phone_b and phone_a == phone_b:
            scores.append(0.9)
            reasons.append("Same phone number")
        
        # Same domain + similar name
        if domain_a and domain_b and domain_a == domain_b:
            name_sim = self._string_similarity(name_a, name_b)
            if name_sim >= self.MIN_NAME_SIMILARITY:
                scores.append(0.85)
                reasons.append(f"Same email domain + similar name ({name_sim:.0%})")
        
        # Same company + similar name
        if company_a and company_b:
            company_sim = self._string_similarity(company_a, company_b)
            if company_sim >= self.MIN_COMPANY_SIMILARITY:
                name_sim = self._string_similarity(name_a, name_b)
                if name_sim >= self.MIN_NAME_SIMILARITY:
                    combined = (company_sim + name_sim) / 2
                    scores.append(0.7 * combined)
                    reasons.append(f"Similar company ({company_sim:.0%}) + name ({name_sim:.0%})")
        
        if not scores:
            return 0.0, []
        
        return max(scores), reasons
    
    def _normalize_name(self, contact: Dict[str, Any]) -> str:
        """Normalize name for comparison."""
        first = (contact.get("firstname") or "").lower().strip()
        last = (contact.get("lastname") or "").lower().strip()
        return f"{first} {last}".strip()
    
    def _normalize_phone(self, phone: str) -> str:
        """Normalize phone for comparison."""
        import re
        return re.sub(r"[^\d]", "", phone)
    
    def _string_similarity(self, a: str, b: str) -> float:
        """Calculate string similarity (0-1)."""
        if not a or not b:
            return 0.0
        return SequenceMatcher(None, a, b).ratio()
    
    def _recommend_merge(
        self, 
        contact_a: Dict[str, Any], 
        contact_b: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Recommend which contact to keep and what to merge."""
        # Score each contact based on data completeness
        score_a = self._data_completeness_score(contact_a)
        score_b = self._data_completeness_score(contact_b)
        
        # Prefer contact with more activity/engagement
        activity_a = contact_a.get("num_associated_deals", 0) + contact_a.get("notes_count", 0)
        activity_b = contact_b.get("num_associated_deals", 0) + contact_b.get("notes_count", 0)
        
        # Prefer older contact (more history)
        created_a = contact_a.get("createdate", "9999")
        created_b = contact_b.get("createdate", "9999")
        
        # Determine primary
        if activity_a > activity_b:
            primary, secondary = contact_a, contact_b
        elif activity_b > activity_a:
            primary, secondary = contact_b, contact_a
        elif score_a >= score_b:
            primary, secondary = contact_a, contact_b
        else:
            primary, secondary = contact_b, contact_a
        
        # Determine what to merge from secondary
        merge_fields = []
        for field in ["phone", "mobilephone", "jobtitle", "company", "linkedin_url"]:
            if secondary.get(field) and not primary.get(field):
                merge_fields.append(field)
        
        return {
            "primary_contact_id": primary.get("id"),
            "secondary_contact_id": secondary.get("id"),
            "primary_email": primary.get("email"),
            "secondary_email": secondary.get("email"),
            "merge_fields_from_secondary": merge_fields,
            "reason": f"Primary has {'more activity' if activity_a != activity_b else 'more complete data'}",
        }
    
    def _data_completeness_score(self, contact: Dict[str, Any]) -> int:
        """Score contact based on data completeness."""
        score = 0
        fields = ["email", "firstname", "lastname", "phone", "company", 
                  "jobtitle", "linkedin_url", "mobilephone"]
        for field in fields:
            if contact.get(field):
                score += 1
        return score

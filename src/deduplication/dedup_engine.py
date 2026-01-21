"""
Contact Deduplication Engine
=============================
Intelligent duplicate detection and merging for contacts.
Uses fuzzy matching, email domain analysis, and configurable rules.
"""

import re
from dataclasses import dataclass, field
from datetime import datetime
from difflib import SequenceMatcher
from enum import Enum
from typing import Optional
import structlog

logger = structlog.get_logger(__name__)


class MatchConfidence(str, Enum):
    """Confidence level of a duplicate match."""
    EXACT = "exact"           # 100% certain match
    HIGH = "high"             # 90%+ confidence
    MEDIUM = "medium"         # 70-90% confidence
    LOW = "low"               # 50-70% confidence
    POSSIBLE = "possible"     # <50% confidence


@dataclass
class DeduplicationRule:
    """A rule for detecting duplicates."""
    id: str
    name: str
    field: str
    match_type: str  # exact, fuzzy, domain, normalized
    weight: float = 1.0
    threshold: float = 0.8
    is_active: bool = True
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "field": self.field,
            "match_type": self.match_type,
            "weight": self.weight,
            "threshold": self.threshold,
            "is_active": self.is_active,
        }


@dataclass
class DuplicateMatch:
    """A detected duplicate match."""
    contact_id_1: str
    contact_id_2: str
    confidence: MatchConfidence
    score: float  # 0-100
    matched_fields: list[str] = field(default_factory=list)
    match_details: dict = field(default_factory=dict)
    recommended_action: str = "review"  # merge, review, ignore
    master_record_id: Optional[str] = None
    detected_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> dict:
        return {
            "contact_id_1": self.contact_id_1,
            "contact_id_2": self.contact_id_2,
            "confidence": self.confidence.value,
            "score": round(self.score, 2),
            "matched_fields": self.matched_fields,
            "match_details": self.match_details,
            "recommended_action": self.recommended_action,
            "master_record_id": self.master_record_id,
            "detected_at": self.detected_at.isoformat(),
        }


@dataclass
class MergeResult:
    """Result of merging duplicate contacts."""
    master_id: str
    merged_ids: list[str]
    fields_merged: dict
    conflicts: list[dict]
    merged_at: datetime = field(default_factory=datetime.utcnow)
    merged_by: str = "system"
    
    def to_dict(self) -> dict:
        return {
            "master_id": self.master_id,
            "merged_ids": self.merged_ids,
            "fields_merged": self.fields_merged,
            "conflicts": self.conflicts,
            "merged_at": self.merged_at.isoformat(),
            "merged_by": self.merged_by,
        }


class DeduplicationEngine:
    """
    Detects and merges duplicate contacts.
    Uses configurable rules and fuzzy matching.
    """
    
    def __init__(self):
        self.rules: list[DeduplicationRule] = []
        self.pending_matches: list[DuplicateMatch] = []
        self.merge_history: list[MergeResult] = []
        self._setup_default_rules()
    
    def _setup_default_rules(self) -> None:
        """Set up default deduplication rules."""
        self.rules = [
            DeduplicationRule(
                id="email_exact",
                name="Exact Email Match",
                field="email",
                match_type="exact",
                weight=3.0,
                threshold=1.0,
            ),
            DeduplicationRule(
                id="email_normalized",
                name="Normalized Email Match",
                field="email",
                match_type="normalized",
                weight=2.5,
                threshold=1.0,
            ),
            DeduplicationRule(
                id="name_fuzzy",
                name="Fuzzy Name Match",
                field="full_name",
                match_type="fuzzy",
                weight=1.5,
                threshold=0.85,
            ),
            DeduplicationRule(
                id="phone_normalized",
                name="Normalized Phone Match",
                field="phone",
                match_type="normalized",
                weight=2.0,
                threshold=1.0,
            ),
            DeduplicationRule(
                id="company_domain",
                name="Same Company Domain",
                field="company_domain",
                match_type="domain",
                weight=1.0,
                threshold=1.0,
            ),
            DeduplicationRule(
                id="linkedin_exact",
                name="LinkedIn Profile Match",
                field="linkedin_url",
                match_type="normalized",
                weight=2.5,
                threshold=1.0,
            ),
        ]
    
    def find_duplicates(
        self,
        contact: dict,
        existing_contacts: list[dict],
        threshold: float = 70.0,
    ) -> list[DuplicateMatch]:
        """
        Find potential duplicates of a contact.
        
        Args:
            contact: The contact to check for duplicates
            existing_contacts: List of existing contacts to check against
            threshold: Minimum score to consider a match
        
        Returns:
            List of potential duplicate matches
        """
        matches = []
        
        for existing in existing_contacts:
            if contact.get("id") == existing.get("id"):
                continue
            
            match = self._compare_contacts(contact, existing)
            
            if match and match.score >= threshold:
                matches.append(match)
        
        # Sort by score descending
        matches.sort(key=lambda m: m.score, reverse=True)
        
        return matches
    
    def _compare_contacts(
        self,
        contact_1: dict,
        contact_2: dict,
    ) -> Optional[DuplicateMatch]:
        """Compare two contacts for duplicate detection."""
        total_weight = 0
        total_score = 0
        matched_fields = []
        match_details = {}
        
        active_rules = [r for r in self.rules if r.is_active]
        
        for rule in active_rules:
            value_1 = contact_1.get(rule.field, "")
            value_2 = contact_2.get(rule.field, "")
            
            if not value_1 or not value_2:
                continue
            
            score = self._apply_rule(rule, value_1, value_2)
            
            if score >= rule.threshold:
                matched_fields.append(rule.field)
                match_details[rule.field] = {
                    "rule": rule.name,
                    "score": score,
                    "values": [value_1, value_2],
                }
            
            total_weight += rule.weight
            total_score += score * rule.weight
        
        if total_weight == 0:
            return None
        
        final_score = (total_score / total_weight) * 100
        
        if final_score < 30:
            return None
        
        # Determine confidence
        confidence = self._determine_confidence(final_score, matched_fields)
        
        # Determine recommended action
        if confidence == MatchConfidence.EXACT:
            action = "merge"
            master = self._determine_master(contact_1, contact_2)
        elif confidence == MatchConfidence.HIGH:
            action = "review"
            master = self._determine_master(contact_1, contact_2)
        else:
            action = "review"
            master = None
        
        return DuplicateMatch(
            contact_id_1=contact_1.get("id", "unknown"),
            contact_id_2=contact_2.get("id", "unknown"),
            confidence=confidence,
            score=final_score,
            matched_fields=matched_fields,
            match_details=match_details,
            recommended_action=action,
            master_record_id=master,
        )
    
    def _apply_rule(
        self,
        rule: DeduplicationRule,
        value_1: str,
        value_2: str,
    ) -> float:
        """Apply a deduplication rule to two values."""
        if rule.match_type == "exact":
            return 1.0 if value_1.lower() == value_2.lower() else 0.0
        
        elif rule.match_type == "fuzzy":
            return SequenceMatcher(None, value_1.lower(), value_2.lower()).ratio()
        
        elif rule.match_type == "normalized":
            norm_1 = self._normalize_value(value_1, rule.field)
            norm_2 = self._normalize_value(value_2, rule.field)
            return 1.0 if norm_1 == norm_2 else 0.0
        
        elif rule.match_type == "domain":
            domain_1 = self._extract_domain(value_1)
            domain_2 = self._extract_domain(value_2)
            return 1.0 if domain_1 == domain_2 else 0.0
        
        return 0.0
    
    def _normalize_value(self, value: str, field: str) -> str:
        """Normalize a value for comparison."""
        if field == "email":
            # Remove dots before @ (Gmail style), lowercase
            value = value.lower().strip()
            local, _, domain = value.partition("@")
            # Remove + aliases
            local = local.split("+")[0]
            # Remove dots from local part (Gmail ignores dots)
            local = local.replace(".", "")
            return f"{local}@{domain}"
        
        elif field == "phone":
            # Remove all non-digits
            return re.sub(r'\D', '', value)
        
        elif field == "linkedin_url":
            # Extract profile ID
            match = re.search(r'linkedin\.com/in/([^/?]+)', value.lower())
            return match.group(1) if match else value.lower()
        
        elif field == "full_name":
            # Lowercase, remove special chars
            return re.sub(r'[^a-z\s]', '', value.lower()).strip()
        
        return value.lower().strip()
    
    def _extract_domain(self, value: str) -> str:
        """Extract domain from email or URL."""
        if "@" in value:
            return value.split("@")[-1].lower()
        
        # URL
        match = re.search(r'(?:https?://)?(?:www\.)?([^/]+)', value.lower())
        return match.group(1) if match else value.lower()
    
    def _determine_confidence(
        self,
        score: float,
        matched_fields: list[str],
    ) -> MatchConfidence:
        """Determine confidence level based on score and matched fields."""
        # Email match alone is very strong indicator
        if "email" in matched_fields:
            return MatchConfidence.EXACT
        
        if score >= 95:
            return MatchConfidence.EXACT
        elif score >= 85:
            return MatchConfidence.HIGH
        elif score >= 70:
            return MatchConfidence.MEDIUM
        elif score >= 50:
            return MatchConfidence.LOW
        return MatchConfidence.POSSIBLE
    
    def _determine_master(
        self,
        contact_1: dict,
        contact_2: dict,
    ) -> str:
        """Determine which record should be the master."""
        # Prefer the record with more data
        score_1 = sum(1 for v in contact_1.values() if v)
        score_2 = sum(1 for v in contact_2.values() if v)
        
        if score_1 > score_2:
            return contact_1.get("id")
        elif score_2 > score_1:
            return contact_2.get("id")
        
        # Prefer older record (lower ID often means older)
        id_1 = contact_1.get("id", "")
        id_2 = contact_2.get("id", "")
        
        return id_1 if id_1 < id_2 else id_2
    
    def merge_contacts(
        self,
        master_id: str,
        duplicate_ids: list[str],
        contacts: dict[str, dict],
        merge_strategy: str = "keep_master",
        merged_by: str = "system",
    ) -> MergeResult:
        """
        Merge duplicate contacts into a master record.
        
        Args:
            master_id: ID of the master record
            duplicate_ids: IDs of records to merge into master
            contacts: Dict of all contacts by ID
            merge_strategy: How to handle conflicts (keep_master, keep_newest, keep_most_complete)
            merged_by: Who initiated the merge
        
        Returns:
            MergeResult with details of the merge
        """
        master = contacts.get(master_id, {})
        duplicates = [contacts.get(d_id, {}) for d_id in duplicate_ids]
        
        fields_merged = {}
        conflicts = []
        
        # Collect all fields
        all_fields = set(master.keys())
        for dup in duplicates:
            all_fields.update(dup.keys())
        
        # Merge each field
        for field in all_fields:
            if field in ["id", "created_at", "updated_at"]:
                continue
            
            master_value = master.get(field)
            dup_values = [d.get(field) for d in duplicates if d.get(field)]
            
            # No conflict if master has value and dups are same or empty
            if master_value:
                conflicting_values = [v for v in dup_values if v and v != master_value]
                if conflicting_values:
                    conflicts.append({
                        "field": field,
                        "master_value": master_value,
                        "duplicate_values": conflicting_values,
                        "resolution": "kept_master" if merge_strategy == "keep_master" else "auto_resolved",
                    })
            else:
                # Master is empty, take from duplicates
                if dup_values:
                    fields_merged[field] = dup_values[0]
        
        result = MergeResult(
            master_id=master_id,
            merged_ids=duplicate_ids,
            fields_merged=fields_merged,
            conflicts=conflicts,
            merged_by=merged_by,
        )
        
        self.merge_history.append(result)
        
        logger.info(
            "contacts_merged",
            master_id=master_id,
            merged_count=len(duplicate_ids),
            conflicts_count=len(conflicts),
        )
        
        return result
    
    def add_rule(self, rule: DeduplicationRule) -> None:
        """Add a deduplication rule."""
        self.rules.append(rule)
    
    def get_rules(self) -> list[DeduplicationRule]:
        """Get all deduplication rules."""
        return self.rules
    
    def update_rule(self, rule_id: str, updates: dict) -> Optional[DeduplicationRule]:
        """Update a deduplication rule."""
        for rule in self.rules:
            if rule.id == rule_id:
                for key, value in updates.items():
                    if hasattr(rule, key):
                        setattr(rule, key, value)
                return rule
        return None
    
    def run_bulk_deduplication(
        self,
        contacts: list[dict],
        threshold: float = 70.0,
    ) -> list[DuplicateMatch]:
        """
        Run deduplication across all contacts.
        
        Args:
            contacts: List of all contacts
            threshold: Minimum score to consider a match
        
        Returns:
            List of all detected duplicates
        """
        all_matches = []
        checked_pairs = set()
        
        for i, contact in enumerate(contacts):
            for j, other in enumerate(contacts[i + 1:], i + 1):
                pair_key = tuple(sorted([
                    contact.get("id", str(i)),
                    other.get("id", str(j))
                ]))
                
                if pair_key in checked_pairs:
                    continue
                
                checked_pairs.add(pair_key)
                
                match = self._compare_contacts(contact, other)
                if match and match.score >= threshold:
                    all_matches.append(match)
        
        # Sort by score
        all_matches.sort(key=lambda m: m.score, reverse=True)
        
        self.pending_matches = all_matches
        
        logger.info(
            "bulk_deduplication_complete",
            contacts_checked=len(contacts),
            duplicates_found=len(all_matches),
        )
        
        return all_matches
    
    def get_pending_matches(
        self,
        confidence: MatchConfidence = None,
    ) -> list[DuplicateMatch]:
        """Get pending duplicate matches."""
        matches = self.pending_matches
        
        if confidence:
            matches = [m for m in matches if m.confidence == confidence]
        
        return matches
    
    def resolve_match(
        self,
        contact_id_1: str,
        contact_id_2: str,
        action: str,  # merge, not_duplicate, skip
    ) -> bool:
        """Resolve a duplicate match."""
        for i, match in enumerate(self.pending_matches):
            if (match.contact_id_1 == contact_id_1 and match.contact_id_2 == contact_id_2) or \
               (match.contact_id_1 == contact_id_2 and match.contact_id_2 == contact_id_1):
                
                if action == "not_duplicate":
                    # Mark as not duplicate (could store for learning)
                    pass
                
                self.pending_matches.pop(i)
                return True
        
        return False


# Singleton instance
_engine: Optional[DeduplicationEngine] = None


def get_dedup_engine() -> DeduplicationEngine:
    """Get the deduplication engine singleton."""
    global _engine
    if _engine is None:
        _engine = DeduplicationEngine()
    return _engine

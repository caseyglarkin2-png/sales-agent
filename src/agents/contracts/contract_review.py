"""ContractReviewAgent - Review and analyze contracts for risks.

Scans contracts for concerning terms, missing clauses, and compliance issues.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum

from src.agents.base import BaseAgent
from src.logger import get_logger

logger = get_logger(__name__)


class RiskLevel(str, Enum):
    """Contract risk levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ClauseType(str, Enum):
    """Types of contract clauses to review."""
    PAYMENT_TERMS = "payment_terms"
    LIABILITY = "liability"
    INDEMNIFICATION = "indemnification"
    TERMINATION = "termination"
    IP_OWNERSHIP = "ip_ownership"
    CONFIDENTIALITY = "confidentiality"
    NON_COMPETE = "non_compete"
    SCOPE = "scope"
    DELIVERABLES = "deliverables"
    SLA = "sla"
    DISPUTE = "dispute"
    INSURANCE = "insurance"
    DATA_PROTECTION = "data_protection"


class ContractReviewAgent(BaseAgent):
    """Reviews contracts for risks and concerning terms.
    
    Features:
    - Clause identification and extraction
    - Risk assessment by clause type
    - Missing clause detection
    - Redline suggestions
    - Compliance checking (GDPR, etc.)
    
    Example:
        agent = ContractReviewAgent(llm_connector)
        result = await agent.execute({
            "action": "review",
            "contract_text": "...",
            "contract_type": "services_agreement",
        })
    """

    # Red flag phrases to watch for
    RED_FLAGS = {
        "unlimited liability": RiskLevel.CRITICAL,
        "indemnify and hold harmless": RiskLevel.HIGH,
        "sole discretion": RiskLevel.MEDIUM,
        "without limitation": RiskLevel.MEDIUM,
        "perpetual license": RiskLevel.HIGH,
        "exclusive rights": RiskLevel.HIGH,
        "automatic renewal": RiskLevel.MEDIUM,
        "non-refundable": RiskLevel.MEDIUM,
        "waive any claims": RiskLevel.HIGH,
        "governing law": RiskLevel.LOW,  # Not a red flag, but should verify
    }

    # Required clauses by contract type
    REQUIRED_CLAUSES = {
        "services_agreement": [
            ClauseType.PAYMENT_TERMS,
            ClauseType.SCOPE,
            ClauseType.DELIVERABLES,
            ClauseType.TERMINATION,
            ClauseType.LIABILITY,
            ClauseType.IP_OWNERSHIP,
            ClauseType.CONFIDENTIALITY,
        ],
        "nda": [
            ClauseType.CONFIDENTIALITY,
            ClauseType.TERMINATION,
            ClauseType.DISPUTE,
        ],
        "employment": [
            ClauseType.TERMINATION,
            ClauseType.IP_OWNERSHIP,
            ClauseType.NON_COMPETE,
            ClauseType.CONFIDENTIALITY,
        ],
    }

    def __init__(self, llm_connector=None, drive_connector=None):
        """Initialize with connectors."""
        super().__init__(
            name="Contract Review Agent",
            description="Reviews contracts for risks and concerning terms"
        )
        self.llm_connector = llm_connector
        self.drive_connector = drive_connector
        
        # Review history
        self._reviews: Dict[str, Dict[str, Any]] = {}

    async def validate_input(self, context: Dict[str, Any]) -> bool:
        """Validate input."""
        action = context.get("action", "review")
        if action == "review":
            return "contract_text" in context or "contract_file_id" in context
        return True

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute contract review action."""
        action = context.get("action", "review")
        
        if action == "review":
            return await self._review_contract(context)
        elif action == "check_clause":
            return await self._check_specific_clause(context)
        elif action == "suggest_redlines":
            return await self._suggest_redlines(context)
        elif action == "list_reviews":
            return await self._list_reviews(context)
        else:
            return {"status": "error", "error": f"Unknown action: {action}"}

    async def _review_contract(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Perform full contract review."""
        review_id = f"rev-{datetime.utcnow().timestamp()}"
        
        # Get contract text
        contract_text = await self._get_contract_text(context)
        if not contract_text:
            return {"status": "error", "error": "Could not retrieve contract text"}
        
        contract_type = context.get("contract_type", "services_agreement")
        
        # 1. Scan for red flags
        red_flags = self._scan_red_flags(contract_text)
        
        # 2. Identify clauses
        clauses = await self._identify_clauses(contract_text, contract_type)
        
        # 3. Check for missing required clauses
        missing_clauses = self._check_missing_clauses(clauses, contract_type)
        
        # 4. Analyze each clause for risks
        clause_analysis = await self._analyze_clauses(clauses)
        
        # 5. Calculate overall risk score
        risk_score, risk_level = self._calculate_risk(red_flags, missing_clauses, clause_analysis)
        
        review = {
            "id": review_id,
            "contract_type": contract_type,
            "risk_score": risk_score,
            "risk_level": risk_level,
            "red_flags": red_flags,
            "clauses_found": list(clauses.keys()),
            "missing_clauses": missing_clauses,
            "clause_analysis": clause_analysis,
            "summary": self._generate_summary(red_flags, missing_clauses, clause_analysis),
            "recommendations": self._generate_recommendations(red_flags, missing_clauses, clause_analysis),
            "reviewed_at": datetime.utcnow().isoformat(),
        }
        
        self._reviews[review_id] = review
        
        logger.info(f"Contract review completed: {review_id} - Risk: {risk_level}")
        
        return {
            "status": "success",
            "review": review,
        }

    async def _get_contract_text(self, context: Dict[str, Any]) -> Optional[str]:
        """Get contract text from various sources."""
        if "contract_text" in context:
            return context["contract_text"]
        
        if "contract_file_id" in context and self.drive_connector:
            try:
                doc = await self.drive_connector.get_file_content(context["contract_file_id"])
                return doc.get("content", "")
            except Exception as e:
                logger.warning(f"Could not get contract from Drive: {e}")
        
        return None

    def _scan_red_flags(self, contract_text: str) -> List[Dict[str, Any]]:
        """Scan for red flag phrases."""
        red_flags = []
        text_lower = contract_text.lower()
        
        for phrase, level in self.RED_FLAGS.items():
            if phrase in text_lower:
                # Find context around the phrase
                idx = text_lower.find(phrase)
                start = max(0, idx - 100)
                end = min(len(text_lower), idx + len(phrase) + 100)
                context = contract_text[start:end]
                
                red_flags.append({
                    "phrase": phrase,
                    "risk_level": level.value,
                    "context": f"...{context}...",
                })
        
        return red_flags

    async def _identify_clauses(
        self, 
        contract_text: str, 
        contract_type: str
    ) -> Dict[str, str]:
        """Identify clauses in the contract."""
        clauses = {}
        
        if self.llm_connector:
            prompt = f"""Analyze this contract and extract the following clauses if present:
{', '.join([c.value for c in ClauseType])}

For each clause found, provide a brief summary.

CONTRACT TEXT:
{contract_text[:8000]}  # Truncate for token limits

Return in format:
CLAUSE_TYPE: Summary
"""
            try:
                response = await self.llm_connector.generate_text(
                    prompt=prompt,
                    temperature=0.3,
                    max_tokens=1500,
                )
                
                # Parse response
                for line in response.strip().split("\n"):
                    if ":" in line:
                        parts = line.split(":", 1)
                        clause_type = parts[0].strip().lower().replace(" ", "_")
                        summary = parts[1].strip()
                        clauses[clause_type] = summary
                        
            except Exception as e:
                logger.warning(f"Could not identify clauses with LLM: {e}")
        
        # Fallback: Simple keyword matching
        if not clauses:
            clause_keywords = {
                ClauseType.PAYMENT_TERMS: ["payment", "invoice", "net 30", "due upon"],
                ClauseType.TERMINATION: ["termination", "terminate", "cancellation"],
                ClauseType.LIABILITY: ["liability", "liable", "damages"],
                ClauseType.CONFIDENTIALITY: ["confidential", "non-disclosure", "proprietary"],
                ClauseType.IP_OWNERSHIP: ["intellectual property", "ownership", "work product"],
            }
            
            text_lower = contract_text.lower()
            for clause_type, keywords in clause_keywords.items():
                if any(kw in text_lower for kw in keywords):
                    clauses[clause_type.value] = "Clause detected (basic scan)"
        
        return clauses

    def _check_missing_clauses(
        self, 
        found_clauses: Dict[str, str], 
        contract_type: str
    ) -> List[str]:
        """Check for missing required clauses."""
        required = self.REQUIRED_CLAUSES.get(contract_type, [])
        missing = []
        
        for clause in required:
            if clause.value not in found_clauses:
                missing.append(clause.value)
        
        return missing

    async def _analyze_clauses(
        self, 
        clauses: Dict[str, str]
    ) -> List[Dict[str, Any]]:
        """Analyze each clause for risks."""
        analysis = []
        
        # Risk indicators by clause type
        risk_indicators = {
            "payment_terms": {
                "good": ["net 30", "milestone-based"],
                "bad": ["net 90", "upon completion only", "no refund"],
            },
            "liability": {
                "good": ["mutual limitation", "capped at contract value"],
                "bad": ["unlimited", "full liability", "all damages"],
            },
            "termination": {
                "good": ["30 days notice", "mutual termination", "for convenience"],
                "bad": ["no termination", "penalties", "automatic renewal"],
            },
        }
        
        for clause_type, summary in clauses.items():
            risk = RiskLevel.LOW.value
            notes = []
            
            if clause_type in risk_indicators:
                indicators = risk_indicators[clause_type]
                summary_lower = summary.lower()
                
                for bad in indicators.get("bad", []):
                    if bad in summary_lower:
                        risk = RiskLevel.HIGH.value
                        notes.append(f"Contains concerning term: '{bad}'")
                
                for good in indicators.get("good", []):
                    if good in summary_lower:
                        notes.append(f"Contains favorable term: '{good}'")
            
            analysis.append({
                "clause_type": clause_type,
                "summary": summary,
                "risk_level": risk,
                "notes": notes,
            })
        
        return analysis

    def _calculate_risk(
        self,
        red_flags: List[Dict],
        missing_clauses: List[str],
        clause_analysis: List[Dict],
    ) -> tuple[int, str]:
        """Calculate overall risk score and level."""
        score = 0
        
        # Red flags (0-40 points)
        for flag in red_flags:
            if flag["risk_level"] == RiskLevel.CRITICAL.value:
                score += 15
            elif flag["risk_level"] == RiskLevel.HIGH.value:
                score += 10
            elif flag["risk_level"] == RiskLevel.MEDIUM.value:
                score += 5
        score = min(40, score)
        
        # Missing clauses (0-30 points)
        score += min(30, len(missing_clauses) * 10)
        
        # Clause risks (0-30 points)
        for clause in clause_analysis:
            if clause["risk_level"] == RiskLevel.HIGH.value:
                score += 8
            elif clause["risk_level"] == RiskLevel.MEDIUM.value:
                score += 4
        score = min(100, score)
        
        # Determine level
        if score >= 70:
            level = RiskLevel.CRITICAL.value
        elif score >= 50:
            level = RiskLevel.HIGH.value
        elif score >= 25:
            level = RiskLevel.MEDIUM.value
        else:
            level = RiskLevel.LOW.value
        
        return score, level

    def _generate_summary(
        self,
        red_flags: List[Dict],
        missing_clauses: List[str],
        clause_analysis: List[Dict],
    ) -> str:
        """Generate review summary."""
        parts = []
        
        if red_flags:
            parts.append(f"Found {len(red_flags)} concerning terms/phrases.")
        
        if missing_clauses:
            parts.append(f"Missing {len(missing_clauses)} recommended clauses: {', '.join(missing_clauses)}.")
        
        high_risk_clauses = [c for c in clause_analysis if c["risk_level"] == "high"]
        if high_risk_clauses:
            parts.append(f"{len(high_risk_clauses)} clauses require attention.")
        
        if not parts:
            parts.append("Contract appears to be standard with no major concerns identified.")
        
        return " ".join(parts)

    def _generate_recommendations(
        self,
        red_flags: List[Dict],
        missing_clauses: List[str],
        clause_analysis: List[Dict],
    ) -> List[Dict[str, str]]:
        """Generate actionable recommendations."""
        recommendations = []
        
        # Address red flags
        for flag in red_flags:
            if flag["risk_level"] in [RiskLevel.CRITICAL.value, RiskLevel.HIGH.value]:
                recommendations.append({
                    "priority": "high",
                    "action": f"Review and negotiate: '{flag['phrase']}'",
                    "reason": f"Found in context: {flag['context'][:100]}...",
                })
        
        # Address missing clauses
        for clause in missing_clauses:
            recommendations.append({
                "priority": "medium",
                "action": f"Request addition of {clause.replace('_', ' ')} clause",
                "reason": f"Standard contracts should include this protection",
            })
        
        # Address risky clauses
        for clause in clause_analysis:
            if clause["risk_level"] == RiskLevel.HIGH.value:
                recommendations.append({
                    "priority": "high",
                    "action": f"Negotiate {clause['clause_type'].replace('_', ' ')} terms",
                    "reason": "; ".join(clause.get("notes", [])),
                })
        
        return recommendations

    async def _check_specific_clause(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Check a specific clause in detail."""
        clause_text = context.get("clause_text", "")
        clause_type = context.get("clause_type", "general")
        
        # Analyze the specific clause
        red_flags = self._scan_red_flags(clause_text)
        
        return {
            "status": "success",
            "clause_type": clause_type,
            "red_flags": red_flags,
            "word_count": len(clause_text.split()),
        }

    async def _suggest_redlines(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Suggest redline changes to contract."""
        if not self.llm_connector:
            return {"status": "error", "error": "LLM connector required for redlines"}
        
        clause_text = context.get("clause_text", "")
        concern = context.get("concern", "Make this more balanced")
        
        prompt = f"""Suggest a redline revision to this contract clause to address the following concern:

CONCERN: {concern}

ORIGINAL CLAUSE:
{clause_text}

Provide:
1. The revised clause text
2. Brief explanation of changes made

Keep the revision professional and legally appropriate.
"""
        
        try:
            response = await self.llm_connector.generate_text(
                prompt=prompt,
                temperature=0.5,
                max_tokens=500,
            )
            
            return {
                "status": "success",
                "original": clause_text,
                "suggestion": response,
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def _list_reviews(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """List past reviews."""
        return {
            "status": "success",
            "count": len(self._reviews),
            "reviews": list(self._reviews.values()),
        }

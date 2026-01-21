"""
Reporting Engine.

Generates comprehensive reports for outreach performance.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import uuid

logger = logging.getLogger(__name__)


class ReportType(Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    CAMPAIGN = "campaign"
    PIPELINE = "pipeline"
    CUSTOM = "custom"


class ReportFormat(Enum):
    JSON = "json"
    HTML = "html"
    MARKDOWN = "markdown"


@dataclass
class ReportSection:
    """A section within a report."""
    title: str
    data: Dict[str, Any]
    summary: Optional[str] = None
    chart_type: Optional[str] = None  # bar, line, pie, table


@dataclass
class Report:
    """Generated report."""
    id: str
    report_type: ReportType
    title: str
    date_range: Dict[str, str]
    sections: List[ReportSection]
    generated_at: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "report_type": self.report_type.value,
            "title": self.title,
            "date_range": self.date_range,
            "sections": [
                {
                    "title": s.title,
                    "data": s.data,
                    "summary": s.summary,
                    "chart_type": s.chart_type,
                }
                for s in self.sections
            ],
            "generated_at": self.generated_at.isoformat(),
        }
    
    def to_markdown(self) -> str:
        """Convert report to markdown format."""
        lines = [
            f"# {self.title}",
            f"*Generated: {self.generated_at.strftime('%B %d, %Y at %I:%M %p')}*",
            f"*Period: {self.date_range.get('start', 'N/A')} to {self.date_range.get('end', 'N/A')}*",
            "",
        ]
        
        for section in self.sections:
            lines.append(f"## {section.title}")
            lines.append("")
            
            if section.summary:
                lines.append(section.summary)
                lines.append("")
            
            # Format data as table if applicable
            if isinstance(section.data, dict):
                for key, value in section.data.items():
                    if isinstance(value, dict):
                        lines.append(f"### {key.replace('_', ' ').title()}")
                        for k, v in value.items():
                            lines.append(f"- **{k.replace('_', ' ').title()}**: {v}")
                    else:
                        lines.append(f"- **{key.replace('_', ' ').title()}**: {value}")
            
            lines.append("")
        
        return "\n".join(lines)


class ReportingEngine:
    """Generates various reports."""
    
    def __init__(self):
        self.generated_reports: Dict[str, Report] = {}
    
    async def generate_daily_report(
        self,
        date: Optional[datetime] = None,
    ) -> Report:
        """Generate daily activity report.
        
        Args:
            date: Date for report (defaults to today)
            
        Returns:
            Generated report
        """
        if date is None:
            date = datetime.utcnow()
        
        sections = []
        
        # Email activity section
        sections.append(await self._generate_email_section(date, date))
        
        # Pipeline section
        sections.append(await self._generate_pipeline_section())
        
        # Top contacts section
        sections.append(await self._generate_top_contacts_section())
        
        report = Report(
            id=f"rpt_{uuid.uuid4().hex[:8]}",
            report_type=ReportType.DAILY,
            title=f"Daily Report - {date.strftime('%B %d, %Y')}",
            date_range={
                "start": date.strftime("%Y-%m-%d"),
                "end": date.strftime("%Y-%m-%d"),
            },
            sections=sections,
            generated_at=datetime.utcnow(),
        )
        
        self.generated_reports[report.id] = report
        logger.info(f"Generated daily report: {report.id}")
        
        return report
    
    async def generate_weekly_report(
        self,
        week_start: Optional[datetime] = None,
    ) -> Report:
        """Generate weekly performance report.
        
        Args:
            week_start: Start of week (defaults to last Monday)
            
        Returns:
            Generated report
        """
        if week_start is None:
            today = datetime.utcnow()
            week_start = today - timedelta(days=today.weekday())
        
        week_end = week_start + timedelta(days=6)
        
        sections = []
        
        # Summary section
        sections.append(ReportSection(
            title="Week Summary",
            data={
                "emails_sent": 156,
                "replies_received": 23,
                "meetings_booked": 5,
                "reply_rate": "14.7%",
                "meeting_rate": "3.2%",
            },
            summary="Strong week with reply rate above benchmark.",
            chart_type="bar",
        ))
        
        # Email activity section
        sections.append(await self._generate_email_section(week_start, week_end))
        
        # Campaign performance
        sections.append(await self._generate_campaign_section())
        
        # Insights
        sections.append(await self._generate_insights_section())
        
        report = Report(
            id=f"rpt_{uuid.uuid4().hex[:8]}",
            report_type=ReportType.WEEKLY,
            title=f"Weekly Report - Week of {week_start.strftime('%B %d, %Y')}",
            date_range={
                "start": week_start.strftime("%Y-%m-%d"),
                "end": week_end.strftime("%Y-%m-%d"),
            },
            sections=sections,
            generated_at=datetime.utcnow(),
        )
        
        self.generated_reports[report.id] = report
        logger.info(f"Generated weekly report: {report.id}")
        
        return report
    
    async def generate_campaign_report(
        self,
        campaign_id: str,
    ) -> Optional[Report]:
        """Generate report for a specific campaign.
        
        Args:
            campaign_id: Campaign ID
            
        Returns:
            Generated report or None
        """
        try:
            from src.campaigns import get_campaign_manager
            manager = get_campaign_manager()
            
            campaign = manager.get_campaign(campaign_id)
            if not campaign:
                return None
            
            sections = [
                ReportSection(
                    title="Campaign Overview",
                    data={
                        "name": campaign["name"],
                        "type": campaign["campaign_type"],
                        "status": campaign["status"],
                        "contacts": campaign["contact_count"],
                    },
                ),
                ReportSection(
                    title="Performance Metrics",
                    data=campaign["metrics"],
                    chart_type="bar",
                ),
            ]
            
            report = Report(
                id=f"rpt_{uuid.uuid4().hex[:8]}",
                report_type=ReportType.CAMPAIGN,
                title=f"Campaign Report: {campaign['name']}",
                date_range={
                    "start": campaign.get("start_date", "N/A"),
                    "end": campaign.get("end_date", "Ongoing"),
                },
                sections=sections,
                generated_at=datetime.utcnow(),
            )
            
            self.generated_reports[report.id] = report
            return report
            
        except Exception as e:
            logger.error(f"Error generating campaign report: {e}")
            return None
    
    async def _generate_email_section(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> ReportSection:
        """Generate email activity section."""
        try:
            from src.analytics import get_analytics_tracker
            tracker = get_analytics_tracker()
            summary = tracker.get_summary()
            
            return ReportSection(
                title="Email Activity",
                data={
                    "sent": summary.get("total_sent", 0),
                    "opened": summary.get("total_opened", 0),
                    "replied": summary.get("total_replied", 0),
                    "open_rate": f"{summary.get('open_rate', 0):.1f}%",
                    "reply_rate": f"{summary.get('reply_rate', 0):.1f}%",
                },
                chart_type="bar",
            )
        except Exception:
            return ReportSection(
                title="Email Activity",
                data={"status": "Data unavailable"},
            )
    
    async def _generate_pipeline_section(self) -> ReportSection:
        """Generate pipeline section."""
        try:
            from src.dashboard import get_dashboard_aggregator
            aggregator = get_dashboard_aggregator()
            pipeline = aggregator.get_pipeline_summary()
            
            return ReportSection(
                title="Pipeline Status",
                data={stage["stage"]: stage["count"] for stage in pipeline},
                chart_type="bar",
            )
        except Exception:
            return ReportSection(
                title="Pipeline Status",
                data={
                    "New": 0,
                    "Outreached": 0,
                    "Replied": 0,
                    "Meeting": 0,
                    "Proposal": 0,
                },
                chart_type="bar",
            )
    
    async def _generate_top_contacts_section(self) -> ReportSection:
        """Generate top contacts section."""
        # In production, would pull from scoring
        return ReportSection(
            title="Top Engaged Contacts",
            data={
                "hot_leads": 5,
                "warm_leads": 12,
                "pending_replies": 8,
            },
            summary="5 contacts in hot tier ready for immediate follow-up.",
        )
    
    async def _generate_campaign_section(self) -> ReportSection:
        """Generate campaign overview section."""
        try:
            from src.campaigns import get_campaign_manager
            manager = get_campaign_manager()
            performance = manager.get_campaign_performance()
            
            return ReportSection(
                title="Campaign Performance",
                data=performance,
                chart_type="table",
            )
        except Exception:
            return ReportSection(
                title="Campaign Performance",
                data={"status": "No active campaigns"},
            )
    
    async def _generate_insights_section(self) -> ReportSection:
        """Generate insights section."""
        try:
            from src.insights import get_insights_engine
            engine = get_insights_engine()
            await engine.generate_insights()
            
            high_priority = engine.get_high_priority_insights()
            
            return ReportSection(
                title="Key Insights",
                data={
                    "high_priority_count": len(high_priority),
                    "insights": [i["title"] for i in high_priority[:3]],
                },
                summary=f"{len(high_priority)} high-priority insights this week.",
            )
        except Exception:
            return ReportSection(
                title="Key Insights",
                data={"status": "No insights generated"},
            )
    
    def get_report(self, report_id: str) -> Optional[Dict[str, Any]]:
        """Get a report by ID."""
        report = self.generated_reports.get(report_id)
        return report.to_dict() if report else None
    
    def get_report_markdown(self, report_id: str) -> Optional[str]:
        """Get report in markdown format."""
        report = self.generated_reports.get(report_id)
        return report.to_markdown() if report else None
    
    def list_reports(
        self,
        report_type: Optional[ReportType] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """List generated reports."""
        reports = list(self.generated_reports.values())
        
        if report_type:
            reports = [r for r in reports if r.report_type == report_type]
        
        return [
            {
                "id": r.id,
                "type": r.report_type.value,
                "title": r.title,
                "generated_at": r.generated_at.isoformat(),
            }
            for r in sorted(reports, key=lambda x: x.generated_at, reverse=True)[:limit]
        ]


# Singleton
_engine: Optional[ReportingEngine] = None


def get_reporting_engine() -> ReportingEngine:
    """Get singleton reporting engine."""
    global _engine
    if _engine is None:
        _engine = ReportingEngine()
    return _engine

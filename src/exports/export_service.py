"""
Export Service - Data Export Functionality
==========================================
Export contacts, companies, deals, and other data.
"""

import asyncio
import csv
import io
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


class ExportFormat(str, Enum):
    """Supported export formats."""
    CSV = "csv"
    JSON = "json"
    EXCEL = "excel"


class ExportType(str, Enum):
    """Types of data that can be exported."""
    CONTACTS = "contacts"
    COMPANIES = "companies"
    DEALS = "deals"
    ACTIVITIES = "activities"
    EMAILS = "emails"
    TASKS = "tasks"
    CAMPAIGNS = "campaigns"
    SEQUENCES = "sequences"
    REPORTS = "reports"
    AUDIT_LOGS = "audit_logs"
    CUSTOM = "custom"


class ExportStatus(str, Enum):
    """Status of an export job."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"


@dataclass
class ExportFilter:
    """Filters for export data."""
    field: str
    operator: str  # eq, ne, gt, lt, gte, lte, contains, in
    value: Any


@dataclass
class ExportColumn:
    """Column definition for export."""
    field: str
    header: str
    format: Optional[str] = None  # date, currency, percent


@dataclass
class ExportJob:
    """Export job record."""
    id: str
    export_type: ExportType
    format: ExportFormat
    status: ExportStatus
    
    # Configuration
    columns: Optional[list[ExportColumn]] = None
    filters: list[ExportFilter] = field(default_factory=list)
    include_headers: bool = True
    
    # Results
    file_name: Optional[str] = None
    file_size: Optional[int] = None
    file_url: Optional[str] = None
    file_content: Optional[str] = None  # For small exports
    record_count: Optional[int] = None
    
    # Metadata
    created_by: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    error_message: Optional[str] = None
    
    # Progress
    progress_percent: int = 0


class ExportService:
    """Service for data exports."""
    
    def __init__(self):
        self.jobs: dict[str, ExportJob] = {}
        self._export_ttl_hours = 24
    
    async def create_export(
        self,
        export_type: ExportType,
        format: ExportFormat,
        columns: Optional[list[dict]] = None,
        filters: Optional[list[dict]] = None,
        include_headers: bool = True,
        created_by: Optional[str] = None
    ) -> ExportJob:
        """Create a new export job."""
        job_id = f"exp_{uuid4().hex[:12]}"
        
        # Parse columns
        export_columns = None
        if columns:
            export_columns = [
                ExportColumn(
                    field=c["field"],
                    header=c.get("header", c["field"]),
                    format=c.get("format")
                )
                for c in columns
            ]
        
        # Parse filters
        export_filters = []
        if filters:
            export_filters = [
                ExportFilter(
                    field=f["field"],
                    operator=f["operator"],
                    value=f["value"]
                )
                for f in filters
            ]
        
        job = ExportJob(
            id=job_id,
            export_type=export_type,
            format=format,
            status=ExportStatus.PENDING,
            columns=export_columns,
            filters=export_filters,
            include_headers=include_headers,
            created_by=created_by,
            expires_at=datetime.utcnow() + timedelta(hours=self._export_ttl_hours)
        )
        
        self.jobs[job_id] = job
        
        logger.info(f"Created export job: {job_id} ({export_type.value} -> {format.value})")
        
        return job
    
    async def process_export(self, job_id: str) -> Optional[ExportJob]:
        """Process an export job."""
        job = self.jobs.get(job_id)
        if not job:
            return None
        
        if job.status != ExportStatus.PENDING:
            return job
        
        job.status = ExportStatus.PROCESSING
        job.started_at = datetime.utcnow()
        
        try:
            # Get sample data based on export type
            data = await self._get_export_data(job.export_type, job.filters)
            
            # Apply column selection
            if job.columns:
                column_fields = [c.field for c in job.columns]
                data = [
                    {k: v for k, v in row.items() if k in column_fields}
                    for row in data
                ]
            
            # Format based on export format
            if job.format == ExportFormat.CSV:
                content, file_name = await self._export_to_csv(data, job)
            elif job.format == ExportFormat.JSON:
                content, file_name = await self._export_to_json(data, job)
            elif job.format == ExportFormat.EXCEL:
                content, file_name = await self._export_to_excel(data, job)
            else:
                raise ValueError(f"Unsupported format: {job.format}")
            
            job.file_content = content
            job.file_name = file_name
            job.file_size = len(content.encode() if isinstance(content, str) else content)
            job.record_count = len(data)
            job.status = ExportStatus.COMPLETED
            job.completed_at = datetime.utcnow()
            job.progress_percent = 100
            
            logger.info(f"Completed export job: {job_id} ({job.record_count} records)")
            
        except Exception as e:
            job.status = ExportStatus.FAILED
            job.error_message = str(e)
            job.completed_at = datetime.utcnow()
            
            logger.error(f"Export job failed: {job_id} - {e}")
        
        return job
    
    async def _get_export_data(
        self,
        export_type: ExportType,
        filters: list[ExportFilter]
    ) -> list[dict]:
        """Get data for export based on type."""
        # Generate sample data
        if export_type == ExportType.CONTACTS:
            return [
                {
                    "id": f"contact_{i}",
                    "first_name": f"First{i}",
                    "last_name": f"Last{i}",
                    "email": f"contact{i}@example.com",
                    "company": f"Company {i % 10}",
                    "title": "Manager",
                    "phone": f"+1555000{i:04d}",
                    "city": "San Francisco",
                    "state": "CA",
                    "country": "United States",
                    "score": 50 + (i % 50),
                    "status": "active" if i % 3 != 0 else "inactive",
                    "created_at": (datetime.utcnow() - timedelta(days=i)).isoformat()
                }
                for i in range(1, 101)
            ]
        
        elif export_type == ExportType.COMPANIES:
            return [
                {
                    "id": f"company_{i}",
                    "name": f"Company {i}",
                    "domain": f"company{i}.com",
                    "industry": ["Technology", "Finance", "Healthcare"][i % 3],
                    "size": ["small", "medium", "large"][i % 3],
                    "employee_count": 10 * (i + 1),
                    "annual_revenue": 100000 * (i + 1),
                    "city": "New York",
                    "country": "United States",
                    "contact_count": i % 10,
                    "created_at": (datetime.utcnow() - timedelta(days=i * 2)).isoformat()
                }
                for i in range(1, 51)
            ]
        
        elif export_type == ExportType.DEALS:
            return [
                {
                    "id": f"deal_{i}",
                    "name": f"Deal {i}",
                    "company": f"Company {i % 20}",
                    "value": 10000 * (i + 1),
                    "stage": ["prospecting", "qualification", "proposal", "closed_won", "closed_lost"][i % 5],
                    "probability": [20, 40, 60, 100, 0][i % 5],
                    "owner": f"Rep {i % 5}",
                    "close_date": (datetime.utcnow() + timedelta(days=30 - i)).isoformat(),
                    "created_at": (datetime.utcnow() - timedelta(days=i * 3)).isoformat()
                }
                for i in range(1, 31)
            ]
        
        elif export_type == ExportType.ACTIVITIES:
            return [
                {
                    "id": f"activity_{i}",
                    "type": ["email", "call", "meeting", "note"][i % 4],
                    "subject": f"Activity {i}",
                    "contact": f"contact_{i % 50}",
                    "company": f"company_{i % 20}",
                    "user": f"user_{i % 5}",
                    "timestamp": (datetime.utcnow() - timedelta(hours=i)).isoformat(),
                    "notes": f"Notes for activity {i}"
                }
                for i in range(1, 201)
            ]
        
        elif export_type == ExportType.EMAILS:
            return [
                {
                    "id": f"email_{i}",
                    "subject": f"Email Subject {i}",
                    "from": "sales@example.com",
                    "to": f"contact{i}@example.com",
                    "status": ["sent", "delivered", "opened", "clicked", "replied"][i % 5],
                    "opened_at": (datetime.utcnow() - timedelta(hours=i)).isoformat() if i % 2 == 0 else None,
                    "clicked_at": (datetime.utcnow() - timedelta(hours=i-1)).isoformat() if i % 3 == 0 else None,
                    "sent_at": (datetime.utcnow() - timedelta(hours=i+1)).isoformat()
                }
                for i in range(1, 101)
            ]
        
        else:
            return [
                {"id": f"item_{i}", "data": f"Sample data {i}"}
                for i in range(1, 11)
            ]
    
    async def _export_to_csv(
        self,
        data: list[dict],
        job: ExportJob
    ) -> tuple[str, str]:
        """Export data to CSV format."""
        if not data:
            return "", f"{job.export_type.value}_export.csv"
        
        output = io.StringIO()
        
        # Determine headers
        if job.columns:
            headers = [c.header for c in job.columns]
            fields = [c.field for c in job.columns]
        else:
            fields = list(data[0].keys())
            headers = fields
        
        writer = csv.DictWriter(output, fieldnames=fields)
        
        if job.include_headers:
            # Write custom headers
            writer.writerow(dict(zip(fields, headers)))
        
        for row in data:
            writer.writerow(row)
        
        file_name = f"{job.export_type.value}_export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
        
        return output.getvalue(), file_name
    
    async def _export_to_json(
        self,
        data: list[dict],
        job: ExportJob
    ) -> tuple[str, str]:
        """Export data to JSON format."""
        output = {
            "export_type": job.export_type.value,
            "exported_at": datetime.utcnow().isoformat(),
            "record_count": len(data),
            "data": data
        }
        
        file_name = f"{job.export_type.value}_export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        
        return json.dumps(output, indent=2), file_name
    
    async def _export_to_excel(
        self,
        data: list[dict],
        job: ExportJob
    ) -> tuple[str, str]:
        """Export data to Excel format (simplified as CSV for demo)."""
        # In production, would use openpyxl or xlsxwriter
        content, _ = await self._export_to_csv(data, job)
        file_name = f"{job.export_type.value}_export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        return content, file_name
    
    async def get_job(self, job_id: str) -> Optional[ExportJob]:
        """Get an export job by ID."""
        return self.jobs.get(job_id)
    
    async def list_jobs(
        self,
        status: Optional[ExportStatus] = None,
        export_type: Optional[ExportType] = None,
        created_by: Optional[str] = None,
        limit: int = 50
    ) -> list[ExportJob]:
        """List export jobs."""
        results = list(self.jobs.values())
        
        if status:
            results = [j for j in results if j.status == status]
        
        if export_type:
            results = [j for j in results if j.export_type == export_type]
        
        if created_by:
            results = [j for j in results if j.created_by == created_by]
        
        # Sort by created_at descending
        results.sort(key=lambda j: j.created_at, reverse=True)
        
        return results[:limit]
    
    async def download_export(self, job_id: str) -> Optional[dict]:
        """Get export file content for download."""
        job = self.jobs.get(job_id)
        if not job:
            return None
        
        if job.status != ExportStatus.COMPLETED:
            return None
        
        # Check expiration
        if job.expires_at and datetime.utcnow() > job.expires_at:
            job.status = ExportStatus.EXPIRED
            return None
        
        # Determine content type
        content_types = {
            ExportFormat.CSV: "text/csv",
            ExportFormat.JSON: "application/json",
            ExportFormat.EXCEL: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        }
        
        return {
            "file_name": job.file_name,
            "content_type": content_types.get(job.format, "application/octet-stream"),
            "content": job.file_content,
            "size": job.file_size
        }
    
    async def delete_job(self, job_id: str) -> bool:
        """Delete an export job."""
        if job_id in self.jobs:
            del self.jobs[job_id]
            logger.info(f"Deleted export job: {job_id}")
            return True
        return False
    
    async def cleanup_expired(self) -> int:
        """Clean up expired export jobs."""
        now = datetime.utcnow()
        expired_ids = [
            job_id for job_id, job in self.jobs.items()
            if job.expires_at and job.expires_at < now
        ]
        
        for job_id in expired_ids:
            job = self.jobs.get(job_id)
            if job:
                job.status = ExportStatus.EXPIRED
                job.file_content = None  # Clear content to free memory
        
        return len(expired_ids)
    
    async def get_export_templates(self) -> list[dict]:
        """Get predefined export templates."""
        return [
            {
                "id": "contacts_basic",
                "name": "Contacts - Basic",
                "export_type": "contacts",
                "description": "Export contact names and emails",
                "columns": [
                    {"field": "first_name", "header": "First Name"},
                    {"field": "last_name", "header": "Last Name"},
                    {"field": "email", "header": "Email"},
                    {"field": "company", "header": "Company"}
                ]
            },
            {
                "id": "contacts_full",
                "name": "Contacts - Full",
                "export_type": "contacts",
                "description": "Export all contact fields",
                "columns": None  # All columns
            },
            {
                "id": "companies_overview",
                "name": "Companies - Overview",
                "export_type": "companies",
                "description": "Export company overview",
                "columns": [
                    {"field": "name", "header": "Company Name"},
                    {"field": "industry", "header": "Industry"},
                    {"field": "size", "header": "Size"},
                    {"field": "employee_count", "header": "Employees"},
                    {"field": "contact_count", "header": "Contacts"}
                ]
            },
            {
                "id": "deals_pipeline",
                "name": "Deals - Pipeline",
                "export_type": "deals",
                "description": "Export deal pipeline data",
                "columns": [
                    {"field": "name", "header": "Deal Name"},
                    {"field": "company", "header": "Company"},
                    {"field": "value", "header": "Value", "format": "currency"},
                    {"field": "stage", "header": "Stage"},
                    {"field": "probability", "header": "Probability", "format": "percent"},
                    {"field": "close_date", "header": "Expected Close", "format": "date"}
                ]
            },
            {
                "id": "email_performance",
                "name": "Emails - Performance",
                "export_type": "emails",
                "description": "Export email engagement data",
                "columns": [
                    {"field": "subject", "header": "Subject"},
                    {"field": "to", "header": "Recipient"},
                    {"field": "status", "header": "Status"},
                    {"field": "sent_at", "header": "Sent At", "format": "date"},
                    {"field": "opened_at", "header": "Opened At", "format": "date"}
                ]
            }
        ]


# Global service instance
_export_service: Optional[ExportService] = None


def get_export_service() -> ExportService:
    """Get or create the export service singleton."""
    global _export_service
    if _export_service is None:
        _export_service = ExportService()
    return _export_service

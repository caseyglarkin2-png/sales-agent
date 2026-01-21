"""
Contact Importer.

Handles importing contacts from various sources (CSV, HubSpot lists, etc.)
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
import uuid
import csv
import io

logger = logging.getLogger(__name__)


class ImportSource(Enum):
    CSV = "csv"
    HUBSPOT_LIST = "hubspot_list"
    MANUAL = "manual"
    LINKEDIN_EXPORT = "linkedin_export"
    SALESFORCE = "salesforce"


class ImportStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ImportedContact:
    """A contact to be imported."""
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    company: Optional[str] = None
    job_title: Optional[str] = None
    phone: Optional[str] = None
    linkedin_url: Optional[str] = None
    industry: Optional[str] = None
    company_size: Optional[int] = None
    custom_fields: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "email": self.email,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "name": f"{self.first_name or ''} {self.last_name or ''}".strip(),
            "company": self.company,
            "job_title": self.job_title,
            "phone": self.phone,
            "linkedin_url": self.linkedin_url,
            "industry": self.industry,
            "company_size": self.company_size,
            "custom_fields": self.custom_fields or {},
        }


@dataclass
class ImportJob:
    """An import job tracking progress."""
    id: str
    source: ImportSource
    status: ImportStatus
    total_contacts: int
    imported_count: int
    failed_count: int
    created_at: datetime
    completed_at: Optional[datetime] = None
    errors: List[str] = None
    campaign_id: Optional[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "source": self.source.value,
            "status": self.status.value,
            "total_contacts": self.total_contacts,
            "imported_count": self.imported_count,
            "failed_count": self.failed_count,
            "success_rate": f"{(self.imported_count / self.total_contacts * 100):.1f}%" if self.total_contacts > 0 else "0%",
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "errors": self.errors[:10],  # Limit to first 10 errors
            "campaign_id": self.campaign_id,
        }


# Field mapping for common CSV formats
FIELD_MAPPINGS = {
    "email": ["email", "email_address", "e-mail", "emailaddress"],
    "first_name": ["first_name", "firstname", "first", "given_name"],
    "last_name": ["last_name", "lastname", "last", "surname", "family_name"],
    "company": ["company", "company_name", "organization", "org"],
    "job_title": ["job_title", "title", "position", "jobtitle", "role"],
    "phone": ["phone", "phone_number", "telephone", "mobile"],
    "linkedin_url": ["linkedin", "linkedin_url", "linkedin_profile"],
    "industry": ["industry", "sector"],
}


class ContactImporter:
    """Handles contact imports."""
    
    def __init__(self):
        self.import_jobs: Dict[str, ImportJob] = {}
        self.imported_contacts: List[ImportedContact] = []
    
    def _normalize_headers(self, headers: List[str]) -> Dict[str, str]:
        """Normalize CSV headers to standard field names.
        
        Args:
            headers: Raw CSV headers
            
        Returns:
            Mapping of standard field name to CSV column name
        """
        mapping = {}
        
        for header in headers:
            header_lower = header.lower().strip()
            
            for standard_field, variations in FIELD_MAPPINGS.items():
                if header_lower in variations:
                    mapping[standard_field] = header
                    break
        
        return mapping
    
    async def import_from_csv(
        self,
        csv_content: str,
        campaign_id: Optional[str] = None,
        skip_duplicates: bool = True,
    ) -> ImportJob:
        """Import contacts from CSV content.
        
        Args:
            csv_content: CSV file content as string
            campaign_id: Optional campaign to add contacts to
            skip_duplicates: Skip duplicate emails
            
        Returns:
            Import job with results
        """
        job_id = f"import_{uuid.uuid4().hex[:8]}"
        
        job = ImportJob(
            id=job_id,
            source=ImportSource.CSV,
            status=ImportStatus.PROCESSING,
            total_contacts=0,
            imported_count=0,
            failed_count=0,
            created_at=datetime.utcnow(),
            campaign_id=campaign_id,
        )
        
        self.import_jobs[job_id] = job
        
        try:
            reader = csv.DictReader(io.StringIO(csv_content))
            headers = reader.fieldnames or []
            
            field_mapping = self._normalize_headers(headers)
            
            if "email" not in field_mapping:
                job.status = ImportStatus.FAILED
                job.errors.append("No email column found in CSV")
                return job
            
            existing_emails = {c.email for c in self.imported_contacts}
            contacts = []
            
            for row in reader:
                job.total_contacts += 1
                
                try:
                    email = row.get(field_mapping.get("email", ""), "").strip().lower()
                    
                    if not email or "@" not in email:
                        job.failed_count += 1
                        job.errors.append(f"Invalid email at row {job.total_contacts}")
                        continue
                    
                    if skip_duplicates and email in existing_emails:
                        job.failed_count += 1
                        continue
                    
                    contact = ImportedContact(
                        email=email,
                        first_name=row.get(field_mapping.get("first_name", ""), "").strip(),
                        last_name=row.get(field_mapping.get("last_name", ""), "").strip(),
                        company=row.get(field_mapping.get("company", ""), "").strip(),
                        job_title=row.get(field_mapping.get("job_title", ""), "").strip(),
                        phone=row.get(field_mapping.get("phone", ""), "").strip(),
                        linkedin_url=row.get(field_mapping.get("linkedin_url", ""), "").strip(),
                        industry=row.get(field_mapping.get("industry", ""), "").strip(),
                    )
                    
                    contacts.append(contact)
                    existing_emails.add(email)
                    job.imported_count += 1
                    
                except Exception as e:
                    job.failed_count += 1
                    job.errors.append(f"Error at row {job.total_contacts}: {str(e)}")
            
            self.imported_contacts.extend(contacts)
            
            # Add to campaign if specified
            if campaign_id:
                await self._add_to_campaign(campaign_id, contacts)
            
            job.status = ImportStatus.COMPLETED
            job.completed_at = datetime.utcnow()
            
            logger.info(f"Import completed: {job.imported_count}/{job.total_contacts} contacts")
            
        except Exception as e:
            job.status = ImportStatus.FAILED
            job.errors.append(f"Import failed: {str(e)}")
            logger.error(f"Import failed: {e}")
        
        return job
    
    async def import_from_hubspot_list(
        self,
        list_id: str,
        campaign_id: Optional[str] = None,
    ) -> ImportJob:
        """Import contacts from a HubSpot list.
        
        Args:
            list_id: HubSpot list ID
            campaign_id: Optional campaign to add contacts to
            
        Returns:
            Import job with results
        """
        job_id = f"import_{uuid.uuid4().hex[:8]}"
        
        job = ImportJob(
            id=job_id,
            source=ImportSource.HUBSPOT_LIST,
            status=ImportStatus.PROCESSING,
            total_contacts=0,
            imported_count=0,
            failed_count=0,
            created_at=datetime.utcnow(),
            campaign_id=campaign_id,
        )
        
        self.import_jobs[job_id] = job
        
        try:
            from src.connectors.hubspot import get_hubspot_connector
            hubspot = get_hubspot_connector()
            
            # Get contacts from list
            # Note: This is a simplified implementation
            contacts_data = await hubspot.get_list_contacts(list_id) if hasattr(hubspot, 'get_list_contacts') else []
            
            job.total_contacts = len(contacts_data)
            
            for contact_data in contacts_data:
                try:
                    props = contact_data.get("properties", {})
                    
                    contact = ImportedContact(
                        email=props.get("email", ""),
                        first_name=props.get("firstname", ""),
                        last_name=props.get("lastname", ""),
                        company=props.get("company", ""),
                        job_title=props.get("jobtitle", ""),
                        phone=props.get("phone", ""),
                        industry=props.get("industry", ""),
                    )
                    
                    self.imported_contacts.append(contact)
                    job.imported_count += 1
                    
                except Exception as e:
                    job.failed_count += 1
                    job.errors.append(str(e))
            
            job.status = ImportStatus.COMPLETED
            job.completed_at = datetime.utcnow()
            
        except Exception as e:
            job.status = ImportStatus.FAILED
            job.errors.append(f"HubSpot import failed: {str(e)}")
        
        return job
    
    async def import_manual(
        self,
        contacts: List[Dict[str, Any]],
        campaign_id: Optional[str] = None,
    ) -> ImportJob:
        """Import contacts from a manual list.
        
        Args:
            contacts: List of contact dictionaries
            campaign_id: Optional campaign
            
        Returns:
            Import job
        """
        job_id = f"import_{uuid.uuid4().hex[:8]}"
        
        job = ImportJob(
            id=job_id,
            source=ImportSource.MANUAL,
            status=ImportStatus.PROCESSING,
            total_contacts=len(contacts),
            imported_count=0,
            failed_count=0,
            created_at=datetime.utcnow(),
            campaign_id=campaign_id,
        )
        
        self.import_jobs[job_id] = job
        
        imported = []
        
        for contact_data in contacts:
            try:
                email = contact_data.get("email", "").strip().lower()
                
                if not email:
                    job.failed_count += 1
                    continue
                
                contact = ImportedContact(
                    email=email,
                    first_name=contact_data.get("first_name", ""),
                    last_name=contact_data.get("last_name", ""),
                    company=contact_data.get("company", ""),
                    job_title=contact_data.get("job_title", ""),
                    phone=contact_data.get("phone", ""),
                    linkedin_url=contact_data.get("linkedin_url", ""),
                    industry=contact_data.get("industry", ""),
                )
                
                imported.append(contact)
                job.imported_count += 1
                
            except Exception as e:
                job.failed_count += 1
                job.errors.append(str(e))
        
        self.imported_contacts.extend(imported)
        
        if campaign_id:
            await self._add_to_campaign(campaign_id, imported)
        
        job.status = ImportStatus.COMPLETED
        job.completed_at = datetime.utcnow()
        
        return job
    
    async def _add_to_campaign(
        self,
        campaign_id: str,
        contacts: List[ImportedContact],
    ):
        """Add imported contacts to a campaign."""
        try:
            from src.campaigns import get_campaign_manager
            manager = get_campaign_manager()
            
            emails = [c.email for c in contacts]
            manager.add_contacts(campaign_id, emails)
            
        except Exception as e:
            logger.error(f"Error adding contacts to campaign: {e}")
    
    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get import job by ID."""
        job = self.import_jobs.get(job_id)
        return job.to_dict() if job else None
    
    def list_jobs(self, limit: int = 20) -> List[Dict[str, Any]]:
        """List import jobs."""
        jobs = sorted(
            self.import_jobs.values(),
            key=lambda x: x.created_at,
            reverse=True
        )
        return [j.to_dict() for j in jobs[:limit]]
    
    def get_imported_contacts(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Get imported contacts."""
        return [c.to_dict() for c in self.imported_contacts[offset:offset + limit]]
    
    def get_import_stats(self) -> Dict[str, Any]:
        """Get import statistics."""
        return {
            "total_imported": len(self.imported_contacts),
            "total_jobs": len(self.import_jobs),
            "by_source": {
                source.value: sum(
                    1 for j in self.import_jobs.values()
                    if j.source == source
                )
                for source in ImportSource
            },
        }


# Singleton
_importer: Optional[ContactImporter] = None


def get_contact_importer() -> ContactImporter:
    """Get singleton contact importer."""
    global _importer
    if _importer is None:
        _importer = ContactImporter()
    return _importer

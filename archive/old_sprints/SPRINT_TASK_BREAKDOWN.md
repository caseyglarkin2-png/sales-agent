# Sales Agent Platform - Sprint & Task Breakdown

## Executive Summary

This document provides a comprehensive, atomic breakdown of the Sales Agent platform into sprints and tasks. Each task is designed to be:
- **Atomic**: A single, committable unit of work
- **Testable**: Includes tests or validation criteria
- **Incremental**: Builds on previous work
- **Demoable**: Each sprint results in working, demonstrable software

## Sprint 0: Foundation & Infrastructure (Pre-Development)

**Sprint Goal**: Establish development environment, CI/CD pipeline, and core infrastructure

### Task 0.1: Development Environment Setup
**Description**: Configure local development environment with all required dependencies
**Acceptance Criteria**:
- Python 3.12+ installed
- PostgreSQL 15+ with pgvector extension
- Redis 7+ running
- Docker and docker-compose configured
**Tests/Validation**:
```bash
python --version  # >= 3.12
psql --version    # >= 15
redis-cli ping    # PONG
docker --version  # >= 24
```
**Deliverable**: `SETUP.md` with environment setup instructions

### Task 0.2: Project Structure & Build System
**Description**: Initialize Python project with pyproject.toml, proper package structure
**Acceptance Criteria**:
- `pyproject.toml` with all dependencies
- `src/` package structure
- `tests/` directory with __init__.py
- `.gitignore` configured
**Tests/Validation**:
```bash
pip install -e .  # Successfully installs
python -c "import src; print(src.__version__)"
```
**Deliverable**: Installable Python package

### Task 0.3: Database Schema Design
**Description**: Design and document complete database schema for all entities
**Acceptance Criteria**:
- Entity-Relationship Diagram (ERD)
- Schema documentation with field types
- Index strategy documented
- Migration strategy defined
**Tests/Validation**:
- ERD review meeting
- Schema validation against requirements
**Deliverable**: `docs/DATABASE_SCHEMA.md`, ERD diagram

### Task 0.4: Alembic Migrations Setup
**Description**: Configure Alembic for database migrations
**Acceptance Criteria**:
- Alembic initialized in `infra/migrations/`
- `alembic.ini` configured for environments
- Initial migration creates all base tables
- Migration testing script
**Tests/Validation**:
```bash
alembic upgrade head  # Creates all tables
alembic downgrade base  # Drops all tables
alembic upgrade head  # Re-creates successfully
```
**Deliverable**: Working database migration system

### Task 0.5: CI/CD Pipeline - GitHub Actions
**Description**: Set up GitHub Actions for CI/CD
**Acceptance Criteria**:
- `.github/workflows/ci.yml` for PR checks
- Runs linting (ruff, black)
- Runs type checking (mypy)
- Runs all tests
- Coverage report generated
**Tests/Validation**:
- Create test PR, verify all checks pass
- Break a test, verify pipeline fails
**Deliverable**: Working CI pipeline

### Task 0.6: Docker Development Environment
**Description**: Create Docker development environment
**Acceptance Criteria**:
- `Dockerfile` for application
- `docker-compose.yml` with app, postgres, redis
- Development and production configurations
- Health checks configured
**Tests/Validation**:
```bash
docker-compose up -d
docker-compose ps  # All containers healthy
curl http://localhost:8000/health  # OK
```
**Deliverable**: Dockerized development environment

### Task 0.7: Logging & Observability Setup
**Description**: Configure structured logging with structlog
**Acceptance Criteria**:
- Structured JSON logging
- Log levels configurable via environment
- Trace ID middleware for request tracking
- Log aggregation configuration (CloudWatch/DataDog)
**Tests/Validation**:
```python
def test_logging():
    logger.info("test", key="value")
    # Verify JSON format with trace_id
```
**Deliverable**: Production-ready logging system

### Task 0.8: Configuration Management
**Description**: Environment-based configuration system
**Acceptance Criteria**:
- Pydantic Settings for type-safe config
- `.env.example` with all required variables
- Secrets management strategy (AWS Secrets Manager/Vault)
- Config validation on startup
**Tests/Validation**:
```python
def test_config():
    settings = get_settings()
    assert settings.database_url
    assert settings.redis_url
```
**Deliverable**: `src/config.py` with validated settings

**Sprint 0 Demo**: 
- Run application in Docker
- Show structured logs
- Execute database migrations
- CI pipeline passing

---

## Sprint 1: Core Domain Models & Database Layer

**Sprint Goal**: Implement all core domain models with database persistence

### Task 1.1: Prospect Model & Repository
**Description**: Create Prospect entity with CRUD operations
**Acceptance Criteria**:
- `src/models/prospect.py` with Pydantic model
- `src/db/repositories/prospect_repo.py` with async CRUD
- SQLAlchemy ORM model
- Database indices on email, company
**Tests/Validation**:
```python
async def test_prospect_crud():
    prospect = await repo.create(prospect_data)
    assert prospect.id
    found = await repo.get_by_email(prospect.email)
    assert found.id == prospect.id
```
**Deliverable**: Working Prospect persistence layer

### Task 1.2: Contact Model & Repository
**Description**: Enhanced Contact model with enrichment fields
**Acceptance Criteria**:
- Full contact model with all fields (name, email, company, title, phone, linkedin, etc.)
- Enrichment data fields (industry, company size, technologies)
- Deduplication logic by email
- Audit fields (created_at, updated_at, created_by)
**Tests/Validation**:
```python
async def test_contact_enrichment():
    contact = await repo.create_with_enrichment(contact_data)
    assert contact.enrichment_data
    assert contact.enrichment_score > 0
```
**Deliverable**: Contact model with enrichment support

### Task 1.3: Company Model & Repository
**Description**: Company/Account entity with hierarchy support
**Acceptance Criteria**:
- Company model with domain, industry, size, revenue
- Parent-child company relationships
- Company scoring fields
- Automatic domain extraction from emails
**Tests/Validation**:
```python
async def test_company_hierarchy():
    parent = await repo.create(parent_company)
    child = await repo.create(child_company, parent_id=parent.id)
    subsidiaries = await repo.get_subsidiaries(parent.id)
    assert child in subsidiaries
```
**Deliverable**: Company model with hierarchy

### Task 1.4: Campaign Model & Repository
**Description**: Email campaign management
**Acceptance Criteria**:
- Campaign model (name, type, status, dates)
- Campaign-contact association (many-to-many)
- Campaign metrics (sent, opened, clicked, replied)
- Campaign templates association
**Tests/Validation**:
```python
async def test_campaign_workflow():
    campaign = await repo.create(campaign_data)
    await repo.add_contacts(campaign.id, contact_ids)
    stats = await repo.get_stats(campaign.id)
    assert stats.total_contacts == len(contact_ids)
```
**Deliverable**: Campaign management system

### Task 1.5: Email Template Model & Repository
**Description**: Email template system with variables
**Acceptance Criteria**:
- Template model with subject, body, variables
- Variable substitution engine
- Template versioning
- Template categories (prospecting, nurture, follow-up)
**Tests/Validation**:
```python
async def test_template_rendering():
    template = await repo.get(template_id)
    rendered = template.render({"first_name": "John"})
    assert "Hi John" in rendered
```
**Deliverable**: Template system with rendering

### Task 1.6: Email Draft Model & Repository
**Description**: Draft email storage and management
**Acceptance Criteria**:
- Draft model (to, subject, body, status)
- Draft-contact association
- Draft approval workflow states
- Draft scheduling support
**Tests/Validation**:
```python
async def test_draft_lifecycle():
    draft = await repo.create_draft(draft_data)
    await repo.update_status(draft.id, "approved")
    draft = await repo.get(draft.id)
    assert draft.status == "approved"
```
**Deliverable**: Draft management system

### Task 1.7: Task Model & Repository
**Description**: Task/activity tracking
**Acceptance Criteria**:
- Task model (title, description, type, due_date, assignee)
- Task-contact/company association
- Task status workflow (pending, in_progress, complete)
- Task priority levels
**Tests/Validation**:
```python
async def test_task_assignment():
    task = await repo.create(task_data)
    await repo.assign(task.id, user_id)
    my_tasks = await repo.get_by_assignee(user_id)
    assert task in my_tasks
```
**Deliverable**: Task tracking system

### Task 1.8: Voice Profile Model & Repository
**Description**: Voice profile storage for personalization
**Acceptance Criteria**:
- Voice profile model (tone, style notes, constraints)
- Profile-user association
- Default profile handling
- Profile versioning
**Tests/Validation**:
```python
async def test_voice_profile():
    profile = await repo.create(profile_data)
    context = profile.to_prompt_context()
    assert "Tone:" in context
```
**Deliverable**: Voice profile persistence

**Sprint 1 Demo**:
- Create prospects, contacts, companies via API
- Create campaign with contacts
- Generate draft from template
- Create tasks
- Show database persistence (restart app, data persists)

---

## Sprint 2: Authentication & Authorization

**Sprint Goal**: Secure API with authentication and role-based access control

### Task 2.1: User Model & Repository
**Description**: User authentication model
**Acceptance Criteria**:
- User model (email, hashed_password, roles)
- Password hashing with bcrypt
- Email verification support
- Account status (active, suspended, deleted)
**Tests/Validation**:
```python
async def test_user_authentication():
    user = await repo.create_user(email, password)
    assert user.verify_password(password)
    assert not user.verify_password("wrong")
```
**Deliverable**: User model with password security

### Task 2.2: JWT Token Authentication
**Description**: JWT-based authentication
**Acceptance Criteria**:
- JWT token generation and validation
- Access and refresh tokens
- Token expiration handling
- Token blacklist for logout
**Tests/Validation**:
```python
async def test_jwt_tokens():
    token = create_access_token(user_id)
    payload = verify_token(token)
    assert payload["user_id"] == user_id
```
**Deliverable**: JWT authentication system

### Task 2.3: Auth Middleware & Decorators
**Description**: Request authentication middleware
**Acceptance Criteria**:
- `@require_auth` decorator for protected endpoints
- `get_current_user()` dependency
- Bearer token parsing from headers
- 401 responses for invalid/missing tokens
**Tests/Validation**:
```python
async def test_protected_endpoint():
    response = await client.get("/api/protected")
    assert response.status_code == 401
    
    response = await client.get("/api/protected", headers=auth_headers)
    assert response.status_code == 200
```
**Deliverable**: Auth middleware and decorators

### Task 2.4: Role-Based Access Control (RBAC)
**Description**: Permission system with roles
**Acceptance Criteria**:
- Roles: admin, manager, sales_rep, viewer
- Permission model (resource, action)
- Role-permission mappings
- `@require_permission("resource", "action")` decorator
**Tests/Validation**:
```python
async def test_rbac():
    # sales_rep can read contacts but not delete
    response = await client.get("/api/contacts", headers=sales_rep_headers)
    assert response.status_code == 200
    
    response = await client.delete("/api/contacts/123", headers=sales_rep_headers)
    assert response.status_code == 403
```
**Deliverable**: RBAC system

### Task 2.5: OAuth2 Integration - Google
**Description**: Google OAuth2 login
**Acceptance Criteria**:
- Google OAuth2 flow
- User creation/linking on first login
- Email verification via Google
- Scope: email, profile, calendar
**Tests/Validation**:
```python
async def test_google_oauth():
    # Mock Google OAuth response
    response = await client.get("/auth/google/callback?code=mock_code")
    assert response.status_code == 200
    assert "access_token" in response.json()
```
**Deliverable**: Google SSO

### Task 2.6: API Key Management
**Description**: API keys for programmatic access
**Acceptance Criteria**:
- API key model (key, user_id, scopes, expires_at)
- Key generation and hashing
- Key rotation support
- Rate limiting per key
**Tests/Validation**:
```python
async def test_api_key_auth():
    api_key = await repo.create_api_key(user_id, scopes=["read:contacts"])
    response = await client.get("/api/contacts", headers={"X-API-Key": api_key})
    assert response.status_code == 200
```
**Deliverable**: API key system

### Task 2.7: Audit Logging
**Description**: Audit trail for sensitive operations
**Acceptance Criteria**:
- Audit log model (user, action, resource, timestamp, details)
- Automatic logging for create/update/delete
- Audit log API endpoints
- Retention policy
**Tests/Validation**:
```python
async def test_audit_logging():
    await repo.delete_contact(contact_id, user_id)
    logs = await audit_repo.get_logs(resource_type="contact", resource_id=contact_id)
    assert logs[0].action == "delete"
```
**Deliverable**: Audit trail system

### Task 2.8: Rate Limiting
**Description**: Rate limiting to prevent abuse
**Acceptance Criteria**:
- Redis-based rate limiter
- Per-user and per-IP limits
- Configurable limits per endpoint
- 429 responses with Retry-After header
**Tests/Validation**:
```python
async def test_rate_limiting():
    for i in range(101):
        response = await client.get("/api/contacts")
    assert response.status_code == 429
```
**Deliverable**: Rate limiting system

**Sprint 2 Demo**:
- Register user via API
- Login with JWT
- Access protected endpoints
- Show RBAC (different users, different permissions)
- Google OAuth login
- Show audit logs

---

## Sprint 3: HubSpot Integration & CRM Sync

**Sprint Goal**: Bidirectional sync with HubSpot CRM

### Task 3.1: HubSpot API Client - Contacts
**Description**: HubSpot connector for contacts
**Acceptance Criteria**:
- `HubSpotConnector` class with async methods
- `search_contacts(email)` method
- `create_contact(data)` method
- `update_contact(id, data)` method
- `get_contact(id)` method
- Error handling and retries
**Tests/Validation**:
```python
async def test_hubspot_contact_sync():
    # Mock HubSpot API
    contact = await connector.search_contacts("test@example.com")
    assert contact["properties"]["email"] == "test@example.com"
```
**Deliverable**: HubSpot contact integration

### Task 3.2: HubSpot API Client - Companies
**Description**: Company sync with HubSpot
**Acceptance Criteria**:
- `search_companies(domain)` method
- `create_company(data)` method
- `get_company(id)` method
- Company-contact associations
**Tests/Validation**:
```python
async def test_hubspot_company():
    company = await connector.search_companies("example.com")
    assert company["properties"]["domain"] == "example.com"
```
**Deliverable**: HubSpot company integration

### Task 3.3: HubSpot Webhooks - Inbound
**Description**: Receive webhooks from HubSpot
**Acceptance Criteria**:
- Webhook endpoint `/webhooks/hubspot`
- Signature verification
- Event types: contact.created, contact.updated, company.created
- Queue webhook processing (Celery)
**Tests/Validation**:
```python
async def test_hubspot_webhook():
    response = await client.post(
        "/webhooks/hubspot",
        json=webhook_payload,
        headers={"X-HubSpot-Signature": signature}
    )
    assert response.status_code == 200
```
**Deliverable**: HubSpot webhook receiver

### Task 3.4: Sync Engine - Contact Sync
**Description**: Bidirectional contact sync
**Acceptance Criteria**:
- Detect changes in local DB
- Push changes to HubSpot
- Pull changes from HubSpot (via webhooks or polling)
- Conflict resolution (last-write-wins or manual)
- Sync status tracking
**Tests/Validation**:
```python
async def test_contact_sync():
    # Update contact locally
    await local_repo.update(contact_id, {"job_title": "VP Sales"})
    
    # Trigger sync
    await sync_engine.sync_contact(contact_id)
    
    # Verify in HubSpot
    hs_contact = await hubspot.get_contact(hs_id)
    assert hs_contact["properties"]["jobtitle"] == "VP Sales"
```
**Deliverable**: Contact sync engine

### Task 3.5: HubSpot Marketing Emails API
**Description**: Fetch marketing emails/newsletters
**Acceptance Criteria**:
- `get_marketing_emails(search, limit)` method
- Parse email HTML content
- Store newsletters for voice training
**Tests/Validation**:
```python
async def test_fetch_newsletters():
    emails = await connector.get_marketing_emails("freight marketer")
    assert len(emails) > 0
    assert "freight" in emails[0]["subject"].lower()
```
**Deliverable**: Newsletter fetching

### Task 3.6: HubSpot Notes & Tasks
**Description**: Sync notes and tasks
**Acceptance Criteria**:
- Create notes in HubSpot from drafts
- Create tasks in HubSpot
- Associate notes/tasks with contacts
**Tests/Validation**:
```python
async def test_create_note():
    note_id = await connector.create_note(contact_id, "Draft email created")
    assert note_id
```
**Deliverable**: Notes & tasks sync

### Task 3.7: Sync Configuration UI (API)
**Description**: API for sync configuration
**Acceptance Criteria**:
- Configure sync direction (one-way, two-way)
- Field mapping configuration
- Sync frequency settings
- Manual sync trigger endpoint
**Tests/Validation**:
```python
async def test_sync_config():
    config = await sync_service.get_config()
    config["sync_contacts"] = True
    await sync_service.update_config(config)
```
**Deliverable**: Sync configuration API

### Task 3.8: Sync Monitoring & Logging
**Description**: Sync status and error tracking
**Acceptance Criteria**:
- Sync job model (status, started_at, completed_at, records_synced, errors)
- Sync error logging
- Sync metrics (last sync time, success rate)
- Alert on sync failures
**Tests/Validation**:
```python
async def test_sync_monitoring():
    job = await sync_service.start_sync()
    await sync_service.wait_for_completion(job.id)
    job = await sync_service.get_job(job.id)
    assert job.status == "completed"
    assert job.records_synced > 0
```
**Deliverable**: Sync monitoring

**Sprint 3 Demo**:
- Create contact in platform, see it in HubSpot
- Update contact in HubSpot, see update in platform
- Fetch newsletters from HubSpot
- Show sync logs and metrics

---

## Sprint 4: AI/LLM Integration - Email Generation

**Sprint Goal**: OpenAI integration for email generation and voice training

### Task 4.1: OpenAI Client Wrapper
**Description**: Async OpenAI client with error handling
**Acceptance Criteria**:
- `LLMConnector` class wrapping OpenAI client
- Retry logic with exponential backoff
- Rate limiting handling
- Token counting and budgeting
- Multiple model support (GPT-4, GPT-3.5-turbo)
**Tests/Validation**:
```python
async def test_llm_generation():
    response = await llm.generate_text("Write a greeting", max_tokens=100)
    assert len(response) > 0
    assert response.startswith("Hi") or response.startswith("Hello")
```
**Deliverable**: LLM client wrapper

### Task 4.2: Prompt Engineering - Base Templates
**Description**: Prompt templates for email generation
**Acceptance Criteria**:
- Prompt template system
- Templates for: cold outreach, follow-up, nurture
- Variable substitution
- Few-shot examples in prompts
**Tests/Validation**:
```python
def test_prompt_template():
    template = get_prompt_template("cold_outreach")
    prompt = template.render(contact=contact_data, voice=voice_profile)
    assert "{{first_name}}" not in prompt  # Variables substituted
```
**Deliverable**: Prompt template library

### Task 4.3: Prospecting Agent
**Description**: AI agent for prospecting email generation
**Acceptance Criteria**:
- `ProspectingAgent` class
- Generate personalized emails from contact data
- Apply voice profile constraints
- Generate multiple variants
- Include calendar slots if provided
**Tests/Validation**:
```python
async def test_prospecting_agent():
    email = await agent.generate_message(
        prospect=prospect,
        voice_profile_id="casey_larkin",
        available_slots=slots
    )
    assert "Hi " + prospect.first_name in email
    assert len(email) < 500  # Follows constraint
```
**Deliverable**: Prospecting email generator

### Task 4.4: Voice Profile Training - Analysis
**Description**: Analyze email samples to extract voice patterns
**Acceptance Criteria**:
- `VoiceProfileTrainer` class
- Analyze tone, formality, sentence length
- Extract common phrases and greetings
- Identify prohibited patterns
- Generate style notes
**Tests/Validation**:
```python
async def test_voice_analysis():
    trainer.add_sample(email_text_1)
    trainer.add_sample(email_text_2)
    analysis = await trainer.analyze_samples()
    assert analysis.tone in ["professional", "casual", "formal"]
    assert 0 <= analysis.formality_level <= 1
```
**Deliverable**: Voice analysis engine

### Task 4.5: Voice Profile Training - Video Transcription
**Description**: YouTube video transcription for voice training
**Acceptance Criteria**:
- `YouTubeTranscriber` class
- Extract video IDs from URLs
- Fetch YouTube captions (youtube-transcript-api)
- Fallback to Whisper API if no captions
- Handle multiple videos in batch
**Tests/Validation**:
```python
async def test_youtube_transcription():
    transcript = await transcriber.transcribe_from_url(youtube_url)
    assert transcript.transcript_text
    assert len(transcript.transcript_text) > 100
```
**Deliverable**: Video transcription service

### Task 4.6: Voice Profile Training - Newsletter Fetching
**Description**: Fetch newsletters from HubSpot for voice training
**Acceptance Criteria**:
- Fetch marketing emails from HubSpot
- Extract text content from HTML
- Filter by search query
- Add to training samples
**Tests/Validation**:
```python
async def test_newsletter_training():
    samples = await trainer.fetch_hubspot_newsletters("freight marketer")
    assert len(samples) > 0
    assert all(s.source == "hubspot_newsletter" for s in samples)
```
**Deliverable**: Newsletter training integration

### Task 4.7: Voice Profile Training - Profile Creation
**Description**: Generate voice profile from analyzed samples
**Acceptance Criteria**:
- Create `VoiceProfile` from `VoiceAnalysis`
- Save profile to database
- Apply profile to email generation
- Profile versioning support
**Tests/Validation**:
```python
async def test_profile_creation():
    analysis = await trainer.analyze_samples()
    profile = await trainer.create_profile_from_analysis("custom", analysis)
    assert profile.tone == analysis.tone
    assert profile.use_contractions == analysis.uses_contractions
```
**Deliverable**: Profile creation from training

### Task 4.8: AI Agent - Nurturing
**Description**: Nurturing email agent for warm leads
**Acceptance Criteria**:
- `NurturingAgent` class
- Context-aware email generation
- Reference previous interactions
- Provide value-add content
**Tests/Validation**:
```python
async def test_nurturing_agent():
    email = await agent.generate_nurture_email(
        contact=contact,
        previous_emails=thread,
        context={"last_interaction": "demo"}
    )
    assert "following our demo" in email.lower()
```
**Deliverable**: Nurturing email agent

**Sprint 4 Demo**:
- Train voice on YouTube videos
- Train voice on HubSpot newsletters
- Generate prospecting email with trained voice
- Show multiple variants
- Generate nurturing email with context

---

## Sprint 5: Contact Queue & Research Workflow

**Sprint Goal**: Contact queue management with AI-powered research

### Task 5.1: Contact Queue Model & Repository
**Description**: Queue system for managing outreach contacts
**Acceptance Criteria**:
- Queue model (contact_id, status, priority, research_data)
- Status workflow: pending → researching → ready → draft_created → sent
- Priority levels (0=normal, 1=high, 2=urgent)
- Queue filtering and sorting
**Tests/Validation**:
```python
async def test_contact_queue():
    queue_entry = await repo.add_to_queue(contact_id, priority=1)
    assert queue_entry.status == "pending"
    
    entries = await repo.list_queue(status="pending", limit=10)
    assert queue_entry in entries
```
**Deliverable**: Contact queue persistence

### Task 5.2: Contact Queue API - CRUD
**Description**: API endpoints for queue management
**Acceptance Criteria**:
- `POST /api/contact-queue/add` - Add contact
- `POST /api/contact-queue/add-bulk` - Add multiple
- `GET /api/contact-queue/list` - List with filters
- `PATCH /api/contact-queue/{id}/status` - Update status
- `DELETE /api/contact-queue/{id}` - Remove
**Tests/Validation**:
```python
async def test_queue_api():
    response = await client.post("/api/contact-queue/add", json=contact_data)
    assert response.status_code == 200
    queue_id = response.json()["contact_id"]
    
    response = await client.get("/api/contact-queue/list")
    assert any(c["id"] == queue_id for c in response.json()["contacts"])
```
**Deliverable**: Queue API endpoints

### Task 5.3: Account Analyzer - Company Research
**Description**: AI-powered company research
**Acceptance Criteria**:
- `AccountAnalyzer` class
- Fetch company data (from HubSpot, enrichment APIs)
- Analyze company size, industry, tech stack
- Identify pain points and opportunities
- Generate messaging recommendations
**Tests/Validation**:
```python
async def test_account_analyzer():
    analysis = await analyzer.analyze_company(company_domain)
    assert analysis.industry
    assert analysis.size_range
    assert len(analysis.insights) > 0
    assert analysis.recommended_angle
```
**Deliverable**: Company research engine

### Task 5.4: Contact Research Endpoint
**Description**: Trigger research for queued contact
**Acceptance Criteria**:
- `POST /api/contact-queue/{id}/research` endpoint
- Update queue status to "researching"
- Run account analysis
- Store research data
- Update status to "ready"
**Tests/Validation**:
```python
async def test_research_endpoint():
    response = await client.post(f"/api/contact-queue/{queue_id}/research")
    assert response.status_code == 200
    
    # Wait for completion
    queue_entry = await repo.get(queue_id)
    assert queue_entry.status == "ready"
    assert queue_entry.research_data
```
**Deliverable**: Research API endpoint

### Task 5.5: Email Proposal Generation
**Description**: Generate email proposals from research
**Acceptance Criteria**:
- `POST /api/contact-queue/{id}/propose-email` endpoint
- Generate multiple variants (default 2-3)
- Include reasoning for each approach
- Personalization notes
- Apply voice profile
**Tests/Validation**:
```python
async def test_email_proposals():
    response = await client.post(
        f"/api/contact-queue/{queue_id}/propose-email?num_variants=3"
    )
    proposals = response.json()["proposals"]
    assert len(proposals) == 3
    assert all("subject" in p and "body" in p for p in proposals)
```
**Deliverable**: Email proposal API

### Task 5.6: Proposal Storage & Retrieval
**Description**: Store and manage email proposals
**Acceptance Criteria**:
- Proposal model (variant, subject, body, reasoning, personalization_notes)
- Associate proposals with queue entry
- `GET /api/contact-queue/{id}` returns proposals
- Proposal selection/approval
**Tests/Validation**:
```python
async def test_proposal_storage():
    response = await client.get(f"/api/contact-queue/{queue_id}")
    data = response.json()
    assert data["proposal_count"] > 0
    assert len(data["proposals"]) > 0
```
**Deliverable**: Proposal storage system

### Task 5.7: Bulk Queue Operations
**Description**: Process multiple contacts efficiently
**Acceptance Criteria**:
- Bulk add to queue
- Bulk research (async job)
- Bulk proposal generation
- Progress tracking
**Tests/Validation**:
```python
async def test_bulk_operations():
    response = await client.post("/api/contact-queue/add-bulk", json={
        "contacts": [contact1, contact2, contact3]
    })
    contact_ids = response.json()["contact_ids"]
    assert len(contact_ids) == 3
```
**Deliverable**: Bulk operations API

### Task 5.8: Queue Metrics & Analytics
**Description**: Queue performance metrics
**Acceptance Criteria**:
- Queue size by status
- Average time in each status
- Research success rate
- Proposal generation success rate
- Dashboard endpoint: `GET /api/contact-queue/metrics`
**Tests/Validation**:
```python
async def test_queue_metrics():
    response = await client.get("/api/contact-queue/metrics")
    metrics = response.json()
    assert "total_in_queue" in metrics
    assert "by_status" in metrics
```
**Deliverable**: Queue analytics

**Sprint 5 Demo**:
- Add 10 contacts to queue (bulk)
- Research all contacts
- Generate email proposals (3 variants each)
- Show proposals with reasoning
- Display queue metrics

---

## Sprint 6: Email Sending & Tracking

**Sprint Goal**: Send emails and track engagement

### Task 6.1: Gmail API Integration - Send
**Description**: Send emails via Gmail API
**Acceptance Criteria**:
- `GmailConnector` class
- `send_email(to, subject, body, from_address)` method
- HTML email support
- Attachment support (future)
- OAuth2 authentication
**Tests/Validation**:
```python
async def test_gmail_send():
    # Mock Gmail API
    message_id = await gmail.send_email(
        to="test@example.com",
        subject="Test",
        body="Test body"
    )
    assert message_id
```
**Deliverable**: Gmail sending integration

### Task 6.2: Email Sending Workflow
**Description**: Send approved emails from queue
**Acceptance Criteria**:
- `POST /api/contact-queue/{id}/send` endpoint
- Select proposal variant to send
- Create draft in Gmail
- Send email
- Update queue status to "sent"
- Store sent email record
**Tests/Validation**:
```python
async def test_send_workflow():
    response = await client.post(
        f"/api/contact-queue/{queue_id}/send",
        json={"proposal_id": proposal_id}
    )
    assert response.status_code == 200
    
    queue_entry = await repo.get(queue_id)
    assert queue_entry.status == "sent"
```
**Deliverable**: Email sending workflow

### Task 6.3: Email Tracking Model
**Description**: Track sent emails
**Acceptance Criteria**:
- SentEmail model (message_id, to, subject, sent_at, status)
- Link to contact and queue entry
- Track: sent, delivered, opened, clicked, replied, bounced
**Tests/Validation**:
```python
async def test_email_tracking():
    sent_email = await repo.create_sent_email(sent_data)
    assert sent_email.status == "sent"
    
    await repo.update_status(sent_email.id, "opened")
    sent_email = await repo.get(sent_email.id)
    assert sent_email.status == "opened"
```
**Deliverable**: Email tracking model

### Task 6.4: Gmail Webhooks - Push Notifications
**Description**: Receive Gmail push notifications
**Acceptance Criteria**:
- Set up Gmail pub/sub watch
- `/webhooks/gmail` endpoint
- Process notification messages
- Fetch message details
- Update tracking status
**Tests/Validation**:
```python
async def test_gmail_webhook():
    response = await client.post("/webhooks/gmail", json=pubsub_message)
    assert response.status_code == 200
    
    # Verify tracking updated
    sent_email = await repo.get_by_message_id(message_id)
    assert sent_email.status == "replied"
```
**Deliverable**: Gmail webhook receiver

### Task 6.5: Email Open & Click Tracking
**Description**: Track email opens and clicks
**Acceptance Criteria**:
- Tracking pixel for opens
- Link rewriting for click tracking
- `GET /track/open/{tracking_id}` endpoint
- `GET /track/click/{tracking_id}` redirect endpoint
- Update sent email status
**Tests/Validation**:
```python
async def test_open_tracking():
    response = await client.get(f"/track/open/{tracking_id}")
    assert response.status_code == 200
    
    sent_email = await repo.get_by_tracking_id(tracking_id)
    assert sent_email.opened_at
```
**Deliverable**: Open & click tracking

### Task 6.6: Reply Detection & Processing
**Description**: Detect and process email replies
**Acceptance Criteria**:
- Thread matching (In-Reply-To, References headers)
- Extract reply text (remove quoted text)
- Sentiment analysis on reply
- Update contact status
- Trigger nurture workflow for positive replies
**Tests/Validation**:
```python
async def test_reply_detection():
    await gmail_webhook_handler.process_reply(message_data)
    
    sent_email = await repo.get_by_message_id(original_message_id)
    assert sent_email.replied_at
    assert sent_email.reply_sentiment in ["positive", "neutral", "negative"]
```
**Deliverable**: Reply processing

### Task 6.7: Bounce & Unsubscribe Handling
**Description**: Handle bounces and opt-outs
**Acceptance Criteria**:
- Detect bounce messages
- Parse bounce type (hard, soft)
- Mark contact as bounced
- Unsubscribe link in emails
- Process unsubscribe requests
- Suppress list management
**Tests/Validation**:
```python
async def test_bounce_handling():
    await email_service.handle_bounce(bounce_message)
    
    contact = await contact_repo.get(contact_id)
    assert contact.status == "bounced"
    assert contact.suppressed == True
```
**Deliverable**: Bounce & unsubscribe handling

### Task 6.8: Email Analytics Dashboard API
**Description**: Email performance metrics
**Acceptance Criteria**:
- `GET /api/analytics/email-performance` endpoint
- Metrics: sent, delivered, opened, clicked, replied rates
- Time-series data
- Breakdown by campaign, contact, sender
**Tests/Validation**:
```python
async def test_email_analytics():
    response = await client.get("/api/analytics/email-performance?days=30")
    data = response.json()
    assert "sent_count" in data
    assert "open_rate" in data
    assert 0 <= data["open_rate"] <= 100
```
**Deliverable**: Email analytics API

**Sprint 6 Demo**:
- Send email from queue
- Show tracking pixel and link tracking
- Simulate reply, show detection
- Show email analytics dashboard
- Demo bounce handling

---

## Sprint 7: Campaign Management & Sequences

**Sprint Goal**: Multi-touch email sequences and campaign automation

### Task 7.1: Sequence Model & Repository
**Description**: Email sequence/cadence definition
**Acceptance Criteria**:
- Sequence model (name, steps, delays)
- Step model (type, template_id, delay_days)
- Step types: email, task, wait
- Sequence activation/deactivation
**Tests/Validation**:
```python
async def test_sequence_creation():
    sequence = await repo.create_sequence(
        name="7-day nurture",
        steps=[
            {"type": "email", "template_id": t1, "delay_days": 0},
            {"type": "wait", "delay_days": 3},
            {"type": "email", "template_id": t2, "delay_days": 3},
        ]
    )
    assert len(sequence.steps) == 3
```
**Deliverable**: Sequence model

### Task 7.2: Enrollment Model & Repository
**Description**: Track contact enrollment in sequences
**Acceptance Criteria**:
- Enrollment model (contact_id, sequence_id, current_step, status)
- Status: active, paused, completed, opted_out
- Next action timestamp
- Enrollment history
**Tests/Validation**:
```python
async def test_enrollment():
    enrollment = await repo.enroll_contact(contact_id, sequence_id)
    assert enrollment.current_step == 0
    assert enrollment.status == "active"
```
**Deliverable**: Enrollment tracking

### Task 7.3: Sequence Execution Engine
**Description**: Background job to execute sequence steps
**Acceptance Criteria**:
- Celery task: `execute_sequence_steps`
- Find enrollments where next_action <= now
- Execute current step (send email, create task)
- Advance to next step
- Schedule next action
**Tests/Validation**:
```python
async def test_sequence_execution():
    await enroll_contact(contact_id, sequence_id)
    
    # Run executor
    await sequence_executor.execute_due_steps()
    
    enrollment = await repo.get_enrollment(enrollment_id)
    assert enrollment.current_step == 1  # Advanced
```
**Deliverable**: Sequence executor

### Task 7.4: Sequence API - CRUD
**Description**: API for sequence management
**Acceptance Criteria**:
- `POST /api/sequences` - Create sequence
- `GET /api/sequences` - List sequences
- `GET /api/sequences/{id}` - Get sequence
- `PUT /api/sequences/{id}` - Update sequence
- `DELETE /api/sequences/{id}` - Delete sequence
**Tests/Validation**:
```python
async def test_sequence_crud():
    response = await client.post("/api/sequences", json=sequence_data)
    sequence_id = response.json()["id"]
    
    response = await client.get(f"/api/sequences/{sequence_id}")
    assert response.json()["name"] == sequence_data["name"]
```
**Deliverable**: Sequence CRUD API

### Task 7.5: Enrollment API
**Description**: Enroll/unenroll contacts from sequences
**Acceptance Criteria**:
- `POST /api/sequences/{id}/enroll` - Enroll contacts
- `POST /api/sequences/{id}/enroll-bulk` - Bulk enroll
- `DELETE /api/enrollments/{id}` - Unenroll
- `PATCH /api/enrollments/{id}/pause` - Pause
- `PATCH /api/enrollments/{id}/resume` - Resume
**Tests/Validation**:
```python
async def test_enrollment_api():
    response = await client.post(
        f"/api/sequences/{sequence_id}/enroll",
        json={"contact_ids": [contact1_id, contact2_id]}
    )
    assert response.json()["enrolled_count"] == 2
```
**Deliverable**: Enrollment API

### Task 7.6: Campaign-Sequence Association
**Description**: Link campaigns to sequences
**Acceptance Criteria**:
- Associate campaign with sequence
- Enroll campaign contacts in sequence
- Campaign-level sequence metrics
- Stop sequence when contact replies
**Tests/Validation**:
```python
async def test_campaign_sequence():
    await campaign_service.set_sequence(campaign_id, sequence_id)
    await campaign_service.enroll_all(campaign_id)
    
    campaign = await campaign_repo.get(campaign_id)
    assert campaign.sequence_id == sequence_id
```
**Deliverable**: Campaign-sequence link

### Task 7.7: Exit Conditions & Smart Rules
**Description**: Automatic enrollment exit rules
**Acceptance Criteria**:
- Exit on reply
- Exit on open + link click
- Exit on contact status change
- Custom exit conditions (e.g., deal created)
- Rule evaluation engine
**Tests/Validation**:
```python
async def test_exit_conditions():
    # Enroll with exit rule: exit on reply
    await repo.enroll_contact(contact_id, sequence_id, exit_on_reply=True)
    
    # Simulate reply
    await email_service.process_reply(message_data)
    
    enrollment = await repo.get_enrollment(enrollment_id)
    assert enrollment.status == "completed"
```
**Deliverable**: Smart exit rules

### Task 7.8: Sequence Performance Analytics
**Description**: Sequence effectiveness metrics
**Acceptance Criteria**:
- `GET /api/sequences/{id}/analytics` endpoint
- Metrics per step: sent, opened, clicked, replied
- Drop-off analysis
- Conversion funnel
- A/B test support (future)
**Tests/Validation**:
```python
async def test_sequence_analytics():
    response = await client.get(f"/api/sequences/{sequence_id}/analytics")
    data = response.json()
    assert "steps" in data
    assert data["steps"][0]["sent_count"] > 0
```
**Deliverable**: Sequence analytics

**Sprint 7 Demo**:
- Create 3-step nurture sequence
- Enroll 10 contacts
- Show execution (emails sent at intervals)
- Simulate reply, show auto-exit
- Display sequence analytics (funnel)

---

## Sprint 8: Calendar Integration & Meeting Scheduling

**Sprint Goal**: Calendar sync and meeting scheduling

### Task 8.1: Google Calendar API Integration
**Description**: Calendar connector for Google Calendar
**Acceptance Criteria**:
- `CalendarConnector` class
- `get_availability(start, end)` method
- `create_event(title, start, end, attendees)` method
- OAuth2 with calendar scope
- Timezone handling
**Tests/Validation**:
```python
async def test_calendar_availability():
    slots = await calendar.get_availability(
        start=datetime(2026, 1, 22, 9, 0),
        end=datetime(2026, 1, 22, 17, 0)
    )
    assert len(slots) > 0
    assert all(s.available for s in slots)
```
**Deliverable**: Calendar integration

### Task 8.2: Meeting Slot Generation
**Description**: Generate available meeting slots
**Acceptance Criteria**:
- Find free slots in calendar
- Respect business hours
- Buffer time between meetings
- Configurable meeting duration
- Multiple timezone support
**Tests/Validation**:
```python
def test_slot_generation():
    slots = generate_meeting_slots(
        calendar_events=busy_times,
        num_slots=3,
        duration_minutes=30,
        business_hours=(9, 17),
        timezone="America/New_York"
    )
    assert len(slots) == 3
    assert all(s.duration == 30 for s in slots)
```
**Deliverable**: Slot generation engine

### Task 8.3: Meeting Slot Embedding in Emails
**Description**: Include meeting slots in prospecting emails
**Acceptance Criteria**:
- Fetch available slots
- Format slots in email (readable times)
- Include booking links (Calendly-style)
- Track which slot was selected
**Tests/Validation**:
```python
async def test_email_with_slots():
    email = await prospecting_agent.generate_message(
        prospect=prospect,
        available_slots=slots
    )
    assert "Would any of these times work" in email
    assert all(format_time(s.start) in email for s in slots)
```
**Deliverable**: Meeting slots in emails

### Task 8.4: Meeting Booking Endpoint
**Description**: API for booking meetings from email links
**Acceptance Criteria**:
- `POST /api/meetings/book` endpoint
- Validate slot availability
- Create calendar event
- Send confirmation email
- Update contact status
**Tests/Validation**:
```python
async def test_meeting_booking():
    response = await client.post("/api/meetings/book", json={
        "slot_id": slot_id,
        "contact_id": contact_id,
        "meeting_type": "demo"
    })
    assert response.status_code == 200
    
    # Verify calendar event created
    events = await calendar.list_events(date=slot.start.date())
    assert any(e.summary == "Demo with John Doe" for e in events)
```
**Deliverable**: Meeting booking API

### Task 8.5: Meeting Confirmation & Reminders
**Description**: Automated meeting confirmations and reminders
**Acceptance Criteria**:
- Send confirmation email immediately
- Schedule reminder emails (24h, 1h before)
- Include calendar invite (.ics attachment)
- Reschedule/cancel support
**Tests/Validation**:
```python
async def test_meeting_confirmation():
    await meeting_service.book_meeting(meeting_data)
    
    # Verify confirmation sent
    sent_emails = await email_repo.get_recent_for_contact(contact_id)
    assert any("Confirmed: Demo" in e.subject for e in sent_emails)
```
**Deliverable**: Meeting confirmation system

### Task 8.6: No-Show Tracking & Follow-up
**Description**: Detect and follow up on no-shows
**Acceptance Criteria**:
- Detect meetings that passed without attendance
- Mark as no-show
- Trigger follow-up sequence
- Reschedule workflow
**Tests/Validation**:
```python
async def test_no_show_detection():
    # Create meeting in past
    meeting = await repo.create_meeting(meeting_data_past)
    
    # Run no-show detector
    await meeting_service.detect_no_shows()
    
    meeting = await repo.get(meeting.id)
    assert meeting.status == "no_show"
```
**Deliverable**: No-show handling

### Task 8.7: Meeting Notes & CRM Sync
**Description**: Capture meeting notes and sync to CRM
**Acceptance Criteria**:
- `POST /api/meetings/{id}/notes` endpoint
- Store meeting notes
- Sync notes to HubSpot
- Link to deals/opportunities
**Tests/Validation**:
```python
async def test_meeting_notes():
    response = await client.post(
        f"/api/meetings/{meeting_id}/notes",
        json={"notes": "Great demo, interested in pricing"}
    )
    assert response.status_code == 200
    
    # Verify synced to HubSpot
    hs_note = await hubspot.get_notes_for_contact(contact_id)
    assert any("Great demo" in n["body"] for n in hs_note)
```
**Deliverable**: Meeting notes system

### Task 8.8: Calendly-Style Booking Page
**Description**: Self-service booking page
**Acceptance Criteria**:
- `GET /book/{user_id}` public booking page
- Display available slots
- Select meeting type and duration
- Collect contact info
- Book meeting
**Tests/Validation**:
```python
async def test_booking_page():
    response = await client.get(f"/book/{user_id}")
    assert response.status_code == 200
    assert "Select a time" in response.text
```
**Deliverable**: Booking page

**Sprint 8 Demo**:
- Generate email with 3 meeting slots
- Click booking link
- Book meeting
- Show calendar event created
- Show confirmation email sent
- Demo meeting notes sync to HubSpot

---

## Sprint 9: Analytics & Reporting

**Sprint Goal**: Comprehensive analytics and reporting

### Task 9.1: Analytics Data Model
**Description**: Time-series metrics storage
**Acceptance Criteria**:
- Metric model (name, value, timestamp, dimensions)
- Aggregated metrics table
- Retention policy (90 days raw, 1 year aggregated)
- Efficient querying with indices
**Tests/Validation**:
```python
async def test_metric_storage():
    await metrics_repo.record("emails_sent", value=1, dimensions={"campaign_id": c_id})
    
    daily_total = await metrics_repo.get_aggregate(
        metric="emails_sent",
        aggregation="sum",
        start_date=date.today(),
        end_date=date.today()
    )
    assert daily_total >= 1
```
**Deliverable**: Metrics data model

### Task 9.2: Activity Tracking Middleware
**Description**: Automatic activity tracking
**Acceptance Criteria**:
- Middleware to log all API requests
- Track: endpoint, user, status_code, duration
- Store in analytics DB
- Sampling for high-volume endpoints
**Tests/Validation**:
```python
async def test_activity_tracking():
    response = await client.get("/api/contacts", headers=auth_headers)
    
    activities = await analytics_repo.get_activities(user_id=user_id)
    assert any(a.endpoint == "/api/contacts" for a in activities)
```
**Deliverable**: Activity tracking middleware

### Task 9.3: Email Performance Reports
**Description**: Email metrics and reports
**Acceptance Criteria**:
- `GET /api/reports/email-performance` endpoint
- Metrics: sent, delivered, open rate, click rate, reply rate, bounce rate
- Time range filtering
- Breakdown by campaign, sequence, sender
- Export to CSV/PDF
**Tests/Validation**:
```python
async def test_email_performance_report():
    response = await client.get("/api/reports/email-performance?start_date=2026-01-01")
    data = response.json()
    assert "open_rate" in data
    assert "time_series" in data
```
**Deliverable**: Email performance reports

### Task 9.4: Contact Funnel Analytics
**Description**: Conversion funnel tracking
**Acceptance Criteria**:
- Funnel stages: added → contacted → opened → replied → meeting → opportunity
- Conversion rates between stages
- Time in each stage
- Drop-off analysis
**Tests/Validation**:
```python
async def test_funnel_analytics():
    response = await client.get("/api/analytics/funnel?campaign_id={campaign_id}")
    funnel = response.json()
    assert funnel["stages"][0]["name"] == "added"
    assert funnel["stages"][0]["count"] >= funnel["stages"][1]["count"]  # Decreasing
```
**Deliverable**: Funnel analytics

### Task 9.5: A/B Testing Framework
**Description**: A/B test email variants
**Acceptance Criteria**:
- AB Test model (name, variants, metric, winner)
- Assign contacts to variants
- Track performance per variant
- Statistical significance calculation
- Auto-declare winner
**Tests/Validation**:
```python
async def test_ab_testing():
    test = await ab_service.create_test(
        name="Subject line test",
        variants=[{"subject": "A"}, {"subject": "B"}],
        metric="open_rate",
        sample_size=100
    )
    
    await ab_service.assign_contacts(test.id, contact_ids)
    
    # Simulate opens
    await ab_service.record_metric(test.id, variant_id="A", metric="open", count=45)
    await ab_service.record_metric(test.id, variant_id="B", metric="open", count=55)
    
    test = await ab_service.get_test(test.id)
    assert test.winner == "B"
```
**Deliverable**: A/B testing framework

### Task 9.6: Leaderboard & Gamification
**Description**: Leaderboards for sales team
**Acceptance Criteria**:
- `GET /api/analytics/leaderboard` endpoint
- Rank by: emails sent, meetings booked, deals closed
- Time period filtering (day, week, month)
- Team and individual rankings
**Tests/Validation**:
```python
async def test_leaderboard():
    response = await client.get("/api/analytics/leaderboard?metric=meetings_booked&period=month")
    leaderboard = response.json()
    assert len(leaderboard["rankings"]) > 0
    assert leaderboard["rankings"][0]["rank"] == 1
```
**Deliverable**: Leaderboard API

### Task 9.7: Custom Dashboard Builder API
**Description**: API for building custom dashboards
**Acceptance Criteria**:
- Dashboard model (user_id, name, widgets)
- Widget types: metric, chart, table
- `POST /api/dashboards` - Create dashboard
- `GET /api/dashboards` - List user's dashboards
- `GET /api/dashboards/{id}/data` - Fetch dashboard data
**Tests/Validation**:
```python
async def test_custom_dashboard():
    dashboard = await dashboard_service.create(
        name="My Dashboard",
        widgets=[
            {"type": "metric", "metric": "emails_sent"},
            {"type": "chart", "metric": "open_rate", "chart_type": "line"}
        ]
    )
    
    data = await dashboard_service.get_data(dashboard.id)
    assert len(data["widgets"]) == 2
```
**Deliverable**: Dashboard builder API

### Task 9.8: Scheduled Reports
**Description**: Automated email reports
**Acceptance Criteria**:
- Report schedule model (user_id, report_type, frequency, recipients)
- Celery task to generate and email reports
- Report types: daily summary, weekly performance, monthly overview
- PDF generation
**Tests/Validation**:
```python
async def test_scheduled_report():
    schedule = await report_service.create_schedule(
        report_type="weekly_performance",
        recipients=["user@example.com"],
        frequency="weekly",
        day_of_week=1  # Monday
    )
    
    # Trigger report generation
    await report_service.generate_report(schedule.id)
    
    # Verify email sent
    assert mock_email_sent
```
**Deliverable**: Scheduled reporting

**Sprint 9 Demo**:
- Show email performance dashboard
- Demonstrate conversion funnel
- Create A/B test for subject lines
- Show leaderboard
- Schedule weekly report
- Export report to PDF

---

## Sprint 10: Voice Training & Personalization

**Sprint Goal**: Advanced voice training and email personalization

### Task 10.1: Voice Training CLI Tool
**Description**: Command-line tool for voice training
**Acceptance Criteria**:
- `python -m src.cli.train_voice --videos <urls>` command
- `python -m src.cli.train_voice --newsletters <query>` command
- Progress bar for transcription
- Success/failure reporting
**Tests/Validation**:
```bash
python -m src.cli.train_voice --videos "https://youtube.com/..." --profile-name "test"
# Should output: ✅ Transcribed 1 video, ✅ Profile created
```
**Deliverable**: Voice training CLI

### Task 10.2: Voice Training API Routes
**Description**: API endpoints for voice training
**Acceptance Criteria**:
- `POST /api/voice/training/youtube-videos` - Train from videos
- `POST /api/voice/training/hubspot-newsletters` - Train from newsletters
- `POST /api/voice/training/samples` - Add text samples
- `POST /api/voice/training/analyze` - Analyze samples
- `POST /api/voice/training/create-profile` - Create profile
**Tests/Validation**:
```python
async def test_voice_training_api():
    response = await client.post(
        "/api/voice/training/youtube-videos",
        json={"video_urls": [url1, url2]}
    )
    assert response.json()["transcripts_added"] == 2
```
**Deliverable**: Voice training API

### Task 10.3: Persona-Based Messaging
**Description**: Tailor messaging by contact persona
**Acceptance Criteria**:
- Persona detection from job title
- Persona types: C-level, mid-management, individual contributor
- Persona-specific pain points and value props
- Apply persona context to email generation
**Tests/Validation**:
```python
def test_persona_detection():
    persona = detect_persona("VP of Sales")
    assert persona == "c_level"
    
    context = get_messaging_context(persona="c_level", industry="logistics")
    assert "ROI" in context["value_props"]
    assert "strategic" in context["tone"]
```
**Deliverable**: Persona-based messaging

### Task 10.4: Dynamic Variable System
**Description**: Advanced variable substitution in templates
**Acceptance Criteria**:
- Variable syntax: `{{variable_name}}`
- Nested variables: `{{contact.company.industry}}`
- Conditional variables: `{{#if contact.job_title}}...{{/if}}`
- Default values: `{{contact.first_name|default:"there"}}`
- Custom filters: `{{contact.company|titlecase}}`
**Tests/Validation**:
```python
def test_dynamic_variables():
    template = "Hi {{contact.first_name|default:'there'}}"
    rendered = render_template(template, context={})
    assert rendered == "Hi there"
    
    rendered = render_template(template, context={"contact": {"first_name": "John"}})
    assert rendered == "Hi John"
```
**Deliverable**: Dynamic variable system

### Task 10.5: Content Library
**Description**: Reusable content snippets
**Acceptance Criteria**:
- ContentSnippet model (name, content, category, variables)
- Insert snippets into templates
- Categories: intro, value_prop, case_study, cta, sign_off
- `GET /api/content-library` endpoint
**Tests/Validation**:
```python
async def test_content_library():
    snippet = await content_repo.create(
        name="Logistics ROI",
        content="We've helped logistics companies reduce costs by {{percentage}}%",
        category="value_prop"
    )
    
    snippets = await content_repo.get_by_category("value_prop")
    assert snippet in snippets
```
**Deliverable**: Content library

### Task 10.6: Multi-Language Support
**Description**: Generate emails in multiple languages
**Acceptance Criteria**:
- Language detection from contact data
- Translation API integration (Google Translate)
- Language-specific voice profiles
- Generate email in contact's language
**Tests/Validation**:
```python
async def test_multi_language():
    email = await prospecting_agent.generate_message(
        prospect=prospect,
        language="es"  # Spanish
    )
    assert "Hola" in email or "Estimado" in email
```
**Deliverable**: Multi-language support

### Task 10.7: Email Personalization Scoring
**Description**: Score how personalized an email is
**Acceptance Criteria**:
- Analyze email for personalization elements
- Score 0-100 based on: company mentions, role mentions, industry terms, etc.
- Recommendation engine for improvements
- Warn if score < 50
**Tests/Validation**:
```python
def test_personalization_scoring():
    email = "Hi John, I saw you work at Acme Corp in logistics..."
    score = calculate_personalization_score(email, contact=contact_data)
    assert score >= 70  # High personalization
    
    generic_email = "Hi, want to chat?"
    score = calculate_personalization_score(generic_email, contact=contact_data)
    assert score < 30  # Low personalization
```
**Deliverable**: Personalization scoring

### Task 10.8: Email Preview & Testing
**Description**: Preview and test emails before sending
**Acceptance Criteria**:
- `POST /api/emails/preview` endpoint
- Render email with test data
- Spam score check (via SpamAssassin or similar)
- Preview in multiple email clients (litmus-style)
- Send test email to self
**Tests/Validation**:
```python
async def test_email_preview():
    response = await client.post(
        "/api/emails/preview",
        json={
            "template_id": template_id,
            "contact_id": contact_id
        }
    )
    preview = response.json()
    assert "subject" in preview
    assert "body_html" in preview
    assert preview["spam_score"] < 5.0
```
**Deliverable**: Email preview & testing

**Sprint 10 Demo**:
- Train voice on YouTube videos via CLI
- Train voice on newsletters via API
- Generate email with persona-based messaging
- Show personalization score
- Preview email with spam check
- Send test email

---

## Sprint 11: Deliverability & Compliance

**Sprint Goal**: Email deliverability optimization and compliance

### Task 11.1: Email Warmup System
**Description**: Warm up new email accounts
**Acceptance Criteria**:
- Warmup schedule model (account, day, send_limit)
- Gradual sending volume increase
- Warmup sequences with engagement simulation
- Monitor delivery rates during warmup
**Tests/Validation**:
```python
async def test_email_warmup():
    warmup = await warmup_service.start_warmup(email_account_id)
    schedule = await warmup_service.get_schedule(warmup.id)
    assert schedule[0].send_limit == 5  # Day 1: 5 emails
    assert schedule[7].send_limit > schedule[0].send_limit  # Increasing
```
**Deliverable**: Email warmup system

### Task 11.2: SPF/DKIM/DMARC Validation
**Description**: Validate email authentication
**Acceptance Criteria**:
- Check SPF record for sending domain
- Verify DKIM signing
- Check DMARC policy
- `GET /api/deliverability/dns-check` endpoint
- Setup guide for missing records
**Tests/Validation**:
```python
async def test_dns_validation():
    response = await client.get("/api/deliverability/dns-check?domain=example.com")
    validation = response.json()
    assert validation["spf"]["valid"] == True
    assert validation["dkim"]["valid"] == True
    assert validation["dmarc"]["valid"] == True
```
**Deliverable**: DNS validation tool

### Task 11.3: Bounce Rate Monitoring
**Description**: Track and alert on bounce rates
**Acceptance Criteria**:
- Real-time bounce rate calculation
- Alert if bounce rate > 5%
- Breakdown by bounce type (hard, soft, block)
- Automatic sending pause at 10%+ bounce rate
**Tests/Validation**:
```python
async def test_bounce_monitoring():
    # Simulate high bounce rate
    for i in range(15):
        await email_service.record_bounce(f"email{i}", bounce_type="hard")
    
    await bounce_monitor.check_rates()
    
    account = await account_repo.get(account_id)
    assert account.sending_paused == True
```
**Deliverable**: Bounce monitoring

### Task 11.4: Spam Complaint Tracking
**Description**: Track spam complaints and feedback loops
**Acceptance Criteria**:
- Process feedback loop emails (FBL)
- Track complaint rate
- Suppress complainers immediately
- Alert if complaint rate > 0.1%
**Tests/Validation**:
```python
async def test_spam_complaint_handling():
    await spam_service.process_complaint(email_address="complainer@example.com")
    
    contact = await contact_repo.get_by_email("complainer@example.com")
    assert contact.suppressed == True
    assert contact.suppression_reason == "spam_complaint"
```
**Deliverable**: Spam complaint handling

### Task 11.5: Unsubscribe Management
**Description**: One-click unsubscribe compliance
**Acceptance Criteria**:
- List-Unsubscribe header in all emails
- One-click unsubscribe (RFC 8058)
- Unsubscribe landing page
- Resubscribe workflow
- Suppression list export
**Tests/Validation**:
```python
async def test_unsubscribe():
    response = await client.get(f"/unsubscribe?token={unsubscribe_token}")
    assert response.status_code == 200
    
    contact = await contact_repo.get_by_email(email_from_token)
    assert contact.unsubscribed == True
```
**Deliverable**: Unsubscribe system

### Task 11.6: GDPR Compliance Tools
**Description**: GDPR compliance features
**Acceptance Criteria**:
- Data export: `GET /api/gdpr/export?contact_id={id}` (JSON)
- Data deletion: `DELETE /api/gdpr/delete?contact_id={id}`
- Consent tracking (opt-in timestamps)
- Right to access, rectify, erase, port
- Data retention policies
**Tests/Validation**:
```python
async def test_gdpr_export():
    response = await client.get(f"/api/gdpr/export?contact_id={contact_id}")
    data = response.json()
    assert "contact" in data
    assert "emails" in data
    assert "activities" in data
```
**Deliverable**: GDPR compliance

### Task 11.7: CAN-SPAM Compliance
**Description**: CAN-SPAM Act compliance
**Acceptance Criteria**:
- Physical address in all emails
- Clear "unsubscribe" in every email
- Honor opt-outs within 10 business days
- No deceptive subject lines (validation)
- Commercial email labeling
**Tests/Validation**:
```python
def test_can_spam_compliance():
    email = generate_email(template, contact)
    compliance = check_can_spam_compliance(email)
    assert compliance["has_physical_address"]
    assert compliance["has_unsubscribe_link"]
    assert compliance["subject_not_deceptive"]
```
**Deliverable**: CAN-SPAM compliance

### Task 11.8: Email Health Dashboard
**Description**: Deliverability health monitoring
**Acceptance Criteria**:
- `GET /api/deliverability/health` endpoint
- Metrics: delivery rate, bounce rate, complaint rate, inbox rate
- Sender reputation score
- Red/yellow/green health indicators
- Actionable recommendations
**Tests/Validation**:
```python
async def test_deliverability_health():
    response = await client.get("/api/deliverability/health")
    health = response.json()
    assert "delivery_rate" in health
    assert health["overall_health"] in ["healthy", "warning", "critical"]
```
**Deliverable**: Deliverability dashboard

**Sprint 11 Demo**:
- Check DNS records (SPF, DKIM, DMARC)
- Show bounce rate monitoring and alerts
- Process spam complaint
- One-click unsubscribe flow
- GDPR data export
- Show deliverability health dashboard

---

## Sprint 12: Testing, Performance & Production Readiness

**Sprint Goal**: Comprehensive testing, optimization, and production deployment

### Task 12.1: Unit Test Coverage - Models
**Description**: Unit tests for all models
**Acceptance Criteria**:
- Test coverage >= 80% for all models
- Test CRUD operations
- Test validation logic
- Test relationships
- Use pytest with pytest-asyncio
**Tests/Validation**:
```bash
pytest tests/models/ --cov=src/models --cov-report=html
# Coverage >= 80%
```
**Deliverable**: Model test suite

### Task 12.2: Unit Test Coverage - Services
**Description**: Unit tests for all service layer
**Acceptance Criteria**:
- Test coverage >= 80% for all services
- Mock external dependencies (LLM, HubSpot, Gmail)
- Test error handling
- Test edge cases
**Tests/Validation**:
```bash
pytest tests/services/ --cov=src --cov-report=html
# Coverage >= 80%
```
**Deliverable**: Service test suite

### Task 12.3: Integration Tests - API
**Description**: Integration tests for all API endpoints
**Acceptance Criteria**:
- Test all API endpoints
- Test authentication flows
- Test error responses (400, 401, 403, 404, 500)
- Test pagination
- Use TestClient with real database (test container)
**Tests/Validation**:
```bash
pytest tests/integration/ -v
# All tests passing
```
**Deliverable**: API integration tests

### Task 12.4: End-to-End Tests - Critical Paths
**Description**: E2E tests for critical user journeys
**Acceptance Criteria**:
- Test: Register → Login → Add Contact → Queue → Research → Generate Email → Send
- Test: Create Sequence → Enroll → Execute → Track
- Test: Voice Training → Profile Creation → Email Generation
- Use real services (docker-compose test environment)
**Tests/Validation**:
```bash
pytest tests/e2e/ -v
# All critical paths working
```
**Deliverable**: E2E test suite

### Task 12.5: Performance Testing - Load Tests
**Description**: Load testing with Locust
**Acceptance Criteria**:
- Test 100 concurrent users
- Test critical endpoints under load
- Response time < 500ms for 95th percentile
- No memory leaks
- No database connection exhaustion
**Tests/Validation**:
```bash
locust -f tests/performance/locustfile.py --host=http://localhost:8000
# Run for 5 minutes, verify metrics
```
**Deliverable**: Performance test suite

### Task 12.6: Database Optimization
**Description**: Optimize database performance
**Acceptance Criteria**:
- Add indices on frequently queried columns
- Optimize slow queries (EXPLAIN ANALYZE)
- Implement connection pooling
- Add read replicas support (future)
- Database query monitoring
**Tests/Validation**:
```sql
EXPLAIN ANALYZE SELECT * FROM contacts WHERE email = 'test@example.com';
-- Should use index, execution time < 10ms
```
**Deliverable**: Optimized database

### Task 12.7: Caching Layer - Redis
**Description**: Implement caching for expensive operations
**Acceptance Criteria**:
- Cache voice profiles (TTL: 1 hour)
- Cache company research (TTL: 24 hours)
- Cache template renderings (TTL: 5 minutes)
- Cache invalidation on updates
- Cache hit rate monitoring
**Tests/Validation**:
```python
async def test_caching():
    # First call - cache miss
    start = time.time()
    result1 = await expensive_operation()
    duration1 = time.time() - start
    
    # Second call - cache hit
    start = time.time()
    result2 = await expensive_operation()
    duration2 = time.time() - start
    
    assert result1 == result2
    assert duration2 < duration1 * 0.1  # 10x faster
```
**Deliverable**: Redis caching layer

### Task 12.8: Production Deployment - Infrastructure
**Description**: Production infrastructure setup
**Acceptance Criteria**:
- Docker images for all services
- Kubernetes manifests (or ECS task definitions)
- Environment-specific configs (dev, staging, prod)
- SSL certificates (Let's Encrypt)
- CDN setup (CloudFront)
- Monitoring (CloudWatch, DataDog)
**Tests/Validation**:
```bash
# Deploy to staging
kubectl apply -f k8s/staging/
kubectl get pods  # All running
curl https://staging-api.example.com/health  # OK
```
**Deliverable**: Production infrastructure

### Task 12.9: CI/CD - Deployment Pipeline
**Description**: Automated deployment pipeline
**Acceptance Criteria**:
- GitHub Actions workflow for deployments
- Automated tests before deploy
- Blue-green deployments
- Rollback capability
- Deployment notifications (Slack)
**Tests/Validation**:
```yaml
# .github/workflows/deploy.yml
# Trigger deployment, verify:
# 1. Tests pass
# 2. New version deployed
# 3. Health check succeeds
# 4. Slack notification sent
```
**Deliverable**: CD pipeline

### Task 12.10: Documentation - API & System
**Description**: Complete documentation
**Acceptance Criteria**:
- OpenAPI/Swagger docs (auto-generated)
- Architecture diagrams
- Database schema documentation
- API usage examples
- Deployment guide
- Runbook for operations
**Tests/Validation**:
```bash
# Verify Swagger UI accessible
curl http://localhost:8000/docs
# Should return HTML with API docs
```
**Deliverable**: Complete documentation

**Sprint 12 Demo**:
- Show test coverage reports
- Run load test live, show metrics
- Show caching improvement (before/after)
- Deploy to staging via CI/CD
- Browse API documentation
- Show production monitoring dashboard

---

## Summary & Delivery Metrics

### Sprint-by-Sprint Deliverables

| Sprint | Goal | Key Deliverables | Demo |
|--------|------|------------------|------|
| 0 | Foundation | Dev environment, CI/CD, DB migrations | Docker stack running |
| 1 | Core Models | All domain models persisted | CRUD via API |
| 2 | Auth | JWT auth, RBAC, OAuth | Login flows |
| 3 | HubSpot | Bidirectional CRM sync | Contact sync demo |
| 4 | AI/LLM | Email generation, voice training | AI-generated emails |
| 5 | Contact Queue | Research workflow, proposals | Queue workflow |
| 6 | Email Send | Sending, tracking, replies | Send & track |
| 7 | Campaigns | Sequences, automation | Multi-touch sequence |
| 8 | Calendar | Meeting scheduling | Book meeting |
| 9 | Analytics | Reports, dashboards | Performance metrics |
| 10 | Voice & Personalization | Advanced personalization | Persona messaging |
| 11 | Deliverability | Compliance, health monitoring | Deliverability check |
| 12 | Production | Testing, optimization, deploy | Production deployment |

### Total Tasks: 97 atomic tasks across 12 sprints

Each task is:
- ✅ Atomic (single commit)
- ✅ Testable (explicit validation)
- ✅ Incremental (builds on previous)
- ✅ Documented (acceptance criteria)

---

## Next Step: Subagent Review

I'll now pass this sprint plan to a subagent for review and improvement suggestions.

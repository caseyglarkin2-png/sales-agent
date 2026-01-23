# Social Proof Outreach System - Sprint Roadmap

**Created:** January 23, 2026  
**Philosophy:** Following BUILD_PHILOSOPHY.md  
**Integration:** Additive to Phase 4 work, can run in parallel

---

## ARCHITECTURE OVERVIEW

### Core Thesis
Short, sweet openers + proof on demand. "Are you familiar with OneRail?" → single relevant proof link.

### System Components

**A) Social Proof Library (SPL)**
- Ingestion pipeline: links + metadata + optional screenshots
- Normalization: canonical URL, publication, date, client, service line
- Tagging: industry, persona, pain, outcome, funnel stage, credibility tier
- Search/retrieval API: deterministic filters + semantic search
- Proof packs: curated sets (e.g., "Warehouse/3PL credibility pack")

**B) Proof-to-Message Engine**
- Generates short openers + follow-ups
- Enforces constraints (length, single link, compliance)
- Exposes knobs for experimentation (tone, question-first, proof-first, curiosity gap)

**C) Experimentation Framework**
- Template variants, holdout control, A/B testing
- Per-persona playbooks
- Outcome attribution to proof_id and variant_id

**D) QA / Review Workflow**
- Sub-agent critiques (copy, strategy, compliance)
- Automated linting (length, claims, forbidden phrases)
- Human approval for new templates + high-risk sends

**E) Dashboard Enhancements**
- Proof asset performance: which proof closes most replies/meetings
- Variant leaderboard: opener types
- Proof coverage gaps: where we lack proof for persona/industry/service
- Feedback capture: SDR notes, prospect reactions, objections

---

## AGENT ROLES & RESPONSIBILITIES

### 1. Outreach Agent (Prospecting)
**Inputs:** account, persona, offer, stage  
**Outputs:** opener + follow-up + CTA, chooses 1 proof asset  
**Logs:** variant_id, proof_id, rationale

### 2. Proof Librarian Agent (Background)
**Curates/cleans proof assets**
- Suggests tags, flags duplicates, quality scores
- Builds proof packs and "best-of" lists

### 3. Research & Personalization Agent (Background)
**Finds contextual hooks WITHOUT inventing facts**
- Recent news, role triggers
- Produces "safe personalization snippets" with citations (source URLs)

### 4. Creative Director Agent (Copy)
**Proposes variants, improves hooks, maintains brand voice**
- Owns templates + tone guidelines

### 5. Strategy Operator Agent (GTM)
**Decides which proof to use for which segment**
- Defines playbooks by vertical/persona/service

### 6. Compliance/Truth Agent
**Validates claims vs proof library**
- Enforces "no majors unless confirmed", "no guaranteed outcomes" wording rules

### 7. QA/Test Engineer Agent
**Owns offline test suite, regression checks, eval harness**

### 8. Data/Analytics Agent
**Defines metrics, instrumentation, dashboards, lift analysis**

---

## TAXONOMY STRUCTURE

### Core Entities

#### ProofAsset Schema
```python
{
    "proof_id": "uuid",
    "asset_type": "Placement | CaseStudy | Quote | Screenshot | DataPoint | DeckSlide | VideoClip | PodcastAppearance | Webinar | Award | LogoPermission",
    "service_line_primary": "PR/Comms | ABM | Paid Media/Ad Buys | Content/White-label | Market Research | Events/Meetings | Creative/Brand | Web/Conversion",
    "service_line_secondary": ["optional", "list"],
    "client_name": "string",
    "publication_or_channel": "string",
    "date_published": "date",
    "url": "string",
    "canonical_url": "string (normalized)",
    "credibility_tier": "Tier1 | Tier2 | Trade | Community | Owned",
    "verification_status": "Verified | NeedsReview | Restricted",
    
    # Retrieval tags
    "persona_primary": "enum",
    "persona_secondary": ["0-3 values"],
    "industry": ["1-2 values"],
    "use_case": "enum",
    "pain": ["1-3 values"],
    "outcome": ["1-3 values"],
    "funnel_stage": "enum",
    "proof_signal": ["1-3 values"],
    
    # Message-fit tags
    "hook_style": "enum (default + allowed)",
    "cta_type": "enum",
    
    # Metadata
    "screenshot_url": "optional string",
    "summary": "text",
    "notes": "text",
    "created_by": "string",
    "verified_by": "string",
    "verification_notes": "text",
    "quality_score": "0-100"
}
```

### Tag Groups (Enumerations)

#### A) Persona
```
Operations Exec (COO/VP Ops)
Warehouse/Yard Ops Leader (DC Manager/Yard Manager)
Transportation Exec (VP Transportation)
Logistics/SCM Leader (VP Supply Chain)
Marketing Exec (CMO/VP Marketing)
Demand Gen / ABM Lead
Comms/PR Lead
Sales Exec (CRO/VP Sales)
RevOps / GTM Ops
Product/Tech Leader (VP Product/CTO)
Founder/GM
```

#### B) Industry/Segment
```
Shipper: Retail
Shipper: CPG/Food
Shipper: Manufacturing
Shipper: Building Materials
Shipper: Industrial / Chemicals
3PL
Broker / Freight Tech Services
Carrier: TL
Carrier: LTL
Intermodal / Drayage
Cold Chain / Reefer
E-commerce / Fulfillment
Parcel / Last-mile
Port / Terminal / Yard
Tech Vendor (Logistics SaaS)
```

#### C) Use Case
```
Earn credibility fast (new category / new market)
Launch announcement (funding/product/expansion)
Narrative reset / repositioning
Lead gen pipeline (meetings booked)
ABM to target accounts
Demand gen at scale (paid)
Thought leadership (exec visibility)
Event leverage (Manifest/CHAINge)
Content engine (white-label)
Competitive differentiation
Market education (research report)
```

#### D) Pain
```
Not enough inbound / weak pipeline
No awareness / "who are you?"
Sales cycle too long / low trust
Stalled deals / credibility gap
Low conversion (site/email)
Poor targeting (spray-and-pray)
Content doesn't perform
Ads wasted / no attribution
Need meetings at event, fast
Category confusion / muddy positioning
"We need proof, not promises"
```

#### E) Outcome
```
More meetings booked
Higher reply rates
Faster sales cycles
Stronger close rates
Better win rate in target accounts
Increased share of voice
Executive visibility
Improved CAC efficiency
Better conversion rate
Stronger investor/customer credibility
```

#### F) Funnel Stage
```
Cold outbound
Warm outbound
Inbound follow-up
Pre-meeting
Post-meeting
Late-stage / proof push
Renewal / expansion
```

#### G) Proof Strength Signals
```
Recognized publication (trade)
Recognized publication (major)
Third-party quote
Named customer
Quantified impact
On-site interview/podcast
Award/recognition
Executive byline
Visual artifact (screenshot)
Repeatability (multiple placements)
```

#### H) Hook Style
```
Name-drop question ("Familiar with {Client}?")
Credibility flex ("We helped place …")
Curiosity gap ("Quick question—are you…")
Contrarian ("Most PR doesn't move pipeline…")
Pain mirror ("If pipeline is the pain…")
Pattern interrupt ("Not a pitch…")
```

#### I) CTA Type
```
Soft yes/no ("Worth a 10-min sanity check?")
Asset offer ("Want the 60-sec story link?")
Meeting ask ("Open to 15 min next week?")
Event-driven ("Are you going to Manifest?")
```

### Scoring Algorithm

**ProofAsset score (0–100):**
- Persona match: 0–25
- Industry match: 0–20
- Service line match: 0–15
- Funnel stage match: 0–10
- Credibility tier: 0–15
- Recency: 0–10
- Proof signal strength: 0–5

**Hard Rules (Gates):**
- If `verification_status != Verified` → not eligible for auto-send
- If `credibility_tier = Owned` → eligible only if no better options OR follow-up after engagement
- If message mentions client/publication → must have proof_id that explicitly supports it

**Minimal Required Fields (8):**
1. service_line_primary
2. client_name
3. publication_or_channel
4. credibility_tier
5. persona_primary
6. industry
7. use_case
8. funnel_stage

---

## REVIEW PROCESS (QUALITY GATES)

### Draft → Production Flow
1. **Draft** → Copy Review (Creative)
2. → Strategy Review
3. → Compliance Review
4. → QA Lint/Checks
5. → "Approved template"

### Runtime Message Flow
- **Low-risk:** auto-send eligible after lint + compliance pass
- **High-risk:** requires human approval (new proof asset, new template, sensitive claim)

### Feedback Loop
- SDR thumbs-up/down + reason codes
- Feeds back into scoring

---

## SPRINT PLAN

### SPRINT 0 — Foundations: Proof is a Product (MVP Library)

**Demo:**  
Upload proof links + view/search them in dashboard; retrieve top 1–3 by filters.

#### Tickets

##### SPR0.1: Create ProofAsset Database Schema

**Priority:** CRITICAL  
**Dependencies:** Phase 4 Task 4.1 (database infrastructure)

**One-liner:** Implement ProofAsset table with full taxonomy support

**Scope Boundaries (NOT included):**
- No semantic search yet (deterministic only)
- No proof packs (manual curated sets)
- No screenshot hosting (URL only)
- No bulk import (single uploads)

**Files:**
- Create: `src/models/proof_asset.py` (250 lines)
- Create: `infra/migrations/versions/003_proof_assets.py` (150 lines)
- Create: `src/models/enums/proof_enums.py` (200 lines - all taxonomy enums)
- Modify: `src/models/__init__.py` (add exports)

**Contracts:**
```sql
CREATE TABLE proof_assets (
    proof_id UUID PRIMARY KEY,
    asset_type VARCHAR(50) NOT NULL,
    service_line_primary VARCHAR(100) NOT NULL,
    service_line_secondary JSONB,
    client_name VARCHAR(255) NOT NULL,
    publication_or_channel VARCHAR(255) NOT NULL,
    date_published DATE,
    url TEXT NOT NULL,
    canonical_url TEXT NOT NULL UNIQUE,
    credibility_tier VARCHAR(20) NOT NULL,
    verification_status VARCHAR(20) DEFAULT 'NeedsReview',
    
    -- Retrieval tags
    persona_primary VARCHAR(100) NOT NULL,
    persona_secondary JSONB,
    industry JSONB NOT NULL,
    use_case VARCHAR(100) NOT NULL,
    pain JSONB,
    outcome JSONB,
    funnel_stage VARCHAR(50) NOT NULL,
    proof_signal JSONB,
    
    -- Message-fit
    hook_style VARCHAR(100),
    cta_type VARCHAR(100),
    
    -- Metadata
    screenshot_url TEXT,
    summary TEXT,
    notes TEXT,
    created_by VARCHAR(255),
    verified_by VARCHAR(255),
    verification_notes TEXT,
    quality_score INTEGER DEFAULT 0,
    
    -- Audit
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    verified_at TIMESTAMP
);

CREATE INDEX idx_proof_assets_persona ON proof_assets(persona_primary);
CREATE INDEX idx_proof_assets_service_line ON proof_assets(service_line_primary);
CREATE INDEX idx_proof_assets_industry ON proof_assets USING GIN(industry);
CREATE INDEX idx_proof_assets_funnel_stage ON proof_assets(funnel_stage);
CREATE INDEX idx_proof_assets_verification ON proof_assets(verification_status);
CREATE INDEX idx_proof_assets_quality ON proof_assets(quality_score DESC);
CREATE INDEX idx_proof_assets_client ON proof_assets(client_name);
```

**Implementation Notes:**
- All enums as Python Enums for type safety
- JSONB for array fields (persona_secondary, industry, pain, outcome, proof_signal, service_line_secondary)
- GIN indexes for JSONB array searches
- Canonical URL hashing for deduplication

**Validation:**
```bash
# Run migration
alembic upgrade head

# Verify schema
psql $DATABASE_URL -c "\d proof_assets"

# Test enum creation
python -c "from src.models.enums.proof_enums import AssetType, CredibilityTier; print(list(AssetType)); print(list(CredibilityTier))"

# Run tests
pytest tests/unit/test_proof_asset_model.py -v
```

**Acceptance Criteria:**
- [ ] Given migration runs, When I check schema, Then all 30+ columns exist
- [ ] Given I create ProofAsset with valid enums, When I save, Then it succeeds
- [ ] Given I create ProofAsset with invalid enum, When I save, Then it fails with validation error
- [ ] Given I insert duplicate canonical_url, When I commit, Then unique constraint violated
- [ ] Given I query by persona_primary, When using index, Then query is fast (<10ms)
- [ ] Given I query industry JSONB array, When using GIN index, Then results correct

**Test Strategy:**
- Unit: Model creation, enum validation, property methods
- Integration: Migration on test DB, index creation, unique constraints
- Manual: Check indexes with EXPLAIN query plans

**Rollback:**
```bash
alembic downgrade -1
# Or: DROP TABLE proof_assets CASCADE;
```

---

##### SPR0.2: Build Proof Ingestion API + Basic UI Upload Form

**Priority:** CRITICAL  
**Dependencies:** SPR0.1 (schema)

**One-liner:** Create API endpoint and minimal UI to upload proof assets with required 8 fields

**Scope Boundaries (NOT included):**
- No bulk CSV import
- No automated URL validation (manual only)
- No screenshot upload (URL reference only)
- No AI-assisted tagging

**Files:**
- Create: `src/routes/proof_assets.py` (300 lines)
- Create: `src/services/proof_ingestion.py` (200 lines)
- Create: `src/static/proof-upload.html` (250 lines)
- Create: `src/static/js/proof-upload.js` (150 lines)
- Create: `tests/integration/test_proof_ingestion.py` (200 lines)

**Contracts:**

**POST /api/proof-assets**
```json
{
  "url": "https://freightwaves.com/...",
  "client_name": "OneRail",
  "publication_or_channel": "FreightWaves",
  "asset_type": "Placement",
  "service_line_primary": "PR/Comms",
  "credibility_tier": "Trade",
  "persona_primary": "Transportation Exec",
  "industry": ["3PL"],
  "use_case": "Earn credibility fast",
  "funnel_stage": "Cold outbound"
}
```

**Response (201 Created):**
```json
{
  "proof_id": "uuid",
  "canonical_url": "https://freightwaves.com/...",
  "verification_status": "NeedsReview",
  "quality_score": 45
}
```

**Error Codes:**
- 400: Invalid enum value, missing required field
- 409: Duplicate canonical_url
- 422: URL validation failed

**Implementation Notes:**
- URL normalization: remove tracking params, lowercase domain
- Quality score v1: simple heuristic (credibility_tier * 15 + has_date * 10 + ...)
- Form validation: dropdown selects for all enums (no free text)
- Auto-set canonical_url from url

**Validation:**
```bash
# API test
curl -X POST http://localhost:8000/api/proof-assets \
  -H "Content-Type: application/json" \
  -d @tests/fixtures/proof_asset_valid.json

# Should return 201 with proof_id

# Duplicate test
curl -X POST http://localhost:8000/api/proof-assets \
  -H "Content-Type: application/json" \
  -d @tests/fixtures/proof_asset_valid.json
# Should return 409

# UI test
open http://localhost:8000/proof-upload
# Fill form, submit, verify success message

# Integration tests
pytest tests/integration/test_proof_ingestion.py -v
```

**Acceptance Criteria:**
- [ ] Given valid proof data, When I POST, Then 201 created with proof_id
- [ ] Given duplicate URL, When I POST, Then 409 with helpful message
- [ ] Given invalid enum, When I POST, Then 400 with field name
- [ ] Given missing required field, When I POST, Then 400 listing missing fields
- [ ] Given I open UI, When page loads, Then all enum dropdowns populated
- [ ] Given I submit form, When successful, Then form clears + success toast
- [ ] Given I submit form, When error, Then error shown inline near field

**Test Strategy:**
- Unit: URL canonicalization logic, quality score calculation
- Integration: Full API flow with DB, duplicate detection
- E2E: Manual UI test with various inputs
- Contract: OpenAPI schema validation

**Rollback:**
Remove route registration from main.py

---

##### SPR0.3: Canonicalization + Duplicate Detection

**Priority:** HIGH  
**Dependencies:** SPR0.2 (ingestion API)

**One-liner:** Robust URL normalization and duplicate detection with merge suggestions

**Scope Boundaries (NOT included):**
- No fuzzy matching (exact canonical_url only)
- No automated merging (manual review)
- No cross-publication duplicate detection

**Files:**
- Create: `src/services/url_canonicalization.py` (150 lines)
- Modify: `src/services/proof_ingestion.py` (+50 lines - integrate canonicalization)
- Create: `tests/unit/test_url_canonicalization.py` (150 lines)

**Implementation Notes:**
- Remove tracking params: utm_*, fbclid, gclid, etc.
- Normalize domain: www.example.com → example.com
- Remove trailing slashes
- Lowercase scheme + domain
- Preserve path case (some CMSes are case-sensitive)
- Hash canonical_url for fast lookup

**Canonicalization Rules:**
```python
# Before: https://www.FreightWaves.com/news/onerail-story?utm_source=twitter&utm_campaign=promo#section
# After:  https://freightwaves.com/news/onerail-story

# Before: https://example.com/Page/
# After:  https://example.com/Page  (preserve path case, remove trailing /)
```

**Validation:**
```python
# Unit tests
test_removes_tracking_params()
test_normalizes_domain()
test_preserves_path_case()
test_removes_trailing_slash()
test_removes_fragment()
test_idempotent()  # canonicalize(canonicalize(url)) == canonicalize(url)

# Integration test
def test_duplicate_detection():
    url1 = "https://www.example.com/article?utm_source=twitter"
    url2 = "https://example.com/article"
    
    proof1 = create_proof(url=url1)
    assert proof1.canonical_url == "https://example.com/article"
    
    with pytest.raises(IntegrityError):  # Duplicate canonical_url
        proof2 = create_proof(url=url2)
```

**Acceptance Criteria:**
- [ ] Given URL with tracking params, When canonicalized, Then params removed
- [ ] Given URL with www subdomain, When canonicalized, Then www removed
- [ ] Given URL with trailing slash, When canonicalized, Then slash removed
- [ ] Given URL with mixed case domain, When canonicalized, Then domain lowercase
- [ ] Given two URLs with same canonical form, When creating second, Then 409 error
- [ ] Given canonicalized URL, When canonicalized again, Then result unchanged (idempotent)

**Test Strategy:**
- Unit: 20+ URL normalization test cases
- Property-based: hypothesis library for random URL generation
- Integration: Duplicate detection with real DB

**Rollback:**
Remove canonicalization call from ingestion service

---

##### SPR0.4: Manual Tagging UI + Quick Filters

**Priority:** MEDIUM  
**Dependencies:** SPR0.2 (basic UI exists)

**One-liner:** Edit proof assets and filter/search by key dimensions

**Scope Boundaries (NOT included):**
- No bulk tag editing
- No AI tag suggestions
- No advanced search (boolean operators)
- No saved searches

**Files:**
- Create: `src/static/proof-library.html` (400 lines)
- Create: `src/static/js/proof-library.js` (300 lines)
- Create: `src/static/css/proof-library.css` (150 lines)
- Modify: `src/routes/proof_assets.py` (+100 lines - list/filter endpoints)

**Contracts:**

**GET /api/proof-assets?persona=Transportation%20Exec&industry=3PL&limit=20**
```json
{
  "proof_assets": [
    {
      "proof_id": "uuid",
      "client_name": "OneRail",
      "publication_or_channel": "FreightWaves",
      "credibility_tier": "Trade",
      "persona_primary": "Transportation Exec",
      "industry": ["3PL"],
      "quality_score": 75,
      "verification_status": "Verified",
      "created_at": "2026-01-15T10:00:00Z"
    }
  ],
  "total": 42,
  "filters_applied": {
    "persona": "Transportation Exec",
    "industry": "3PL"
  }
}
```

**PUT /api/proof-assets/{proof_id}**
```json
{
  "pain": ["Not enough inbound / weak pipeline", "No awareness / \"who are you?\""],
  "outcome": ["More meetings booked"],
  "proof_signal": ["Recognized publication (trade)", "Named customer"]
}
```

**UI Features:**
- Sidebar filters: persona, industry, service_line, funnel_stage, credibility_tier
- Multi-select for array fields
- Live filter count updates
- Table view: sortable columns (client, publication, date, quality_score)
- Click row → edit modal
- "Quick tag" buttons for common combinations

**Validation:**
```bash
# Open library
open http://localhost:8000/proof-library

# Manual checks:
# 1. Filter by persona → table updates
# 2. Click proof → edit modal opens
# 3. Add tags → save → tags persist
# 4. Sort by quality_score → order correct
# 5. Multi-select industries → AND/OR logic works

# API tests
pytest tests/integration/test_proof_library.py -v
```

**Acceptance Criteria:**
- [ ] Given I select persona filter, When applied, Then only matching proofs shown
- [ ] Given I select multiple industries, When applied, Then proofs with ANY industry shown
- [ ] Given I click proof row, When modal opens, Then all fields editable
- [ ] Given I edit tags, When I save, Then changes persist and quality_score recalculated
- [ ] Given I sort by date, When clicking column, Then order correct (newest first)
- [ ] Given 100 proofs exist, When I paginate, Then next page loads correctly

**Test Strategy:**
- Integration: Filter logic with various combinations
- E2E: Manual UI flow testing
- Performance: Query time with 1000+ proofs (<200ms)

**Rollback:**
Remove route, keep table view simple (no filters)

---

##### SPR0.5: Proof Quality Scoring v1

**Priority:** MEDIUM  
**Dependencies:** SPR0.1 (schema with quality_score field)

**One-liner:** Implement heuristic quality scoring algorithm (0-100)

**Scope Boundaries (NOT included):**
- No ML-based scoring
- No historical performance data (not collected yet)
- No A/B test lift incorporated

**Files:**
- Create: `src/services/proof_scoring.py` (200 lines)
- Modify: `src/services/proof_ingestion.py` (+20 lines - auto-score on create/update)
- Create: `tests/unit/test_proof_scoring.py` (150 lines)

**Scoring Algorithm:**
```python
def calculate_quality_score(proof: ProofAsset) -> int:
    """
    Returns 0-100 score based on:
    - Credibility tier (0-15)
    - Completeness (0-15): has all optional fields
    - Recency (0-10): <3mo=10, <6mo=7, <1yr=5, <2yr=3, else=0
    - Proof signals (0-5 each, max 15): count * 5
    - Verification (0-15): Verified=15, else=0
    - Publication tier boost (0-10): major pub=10, trade=7, else=0
    - Has screenshot (0-5)
    - Has summary (0-5)
    - Tag completeness (0-10): pain + outcome + hook_style filled
    """
    score = 0
    
    # Credibility tier
    tier_scores = {
        "Tier1": 15,
        "Tier2": 12,
        "Trade": 10,
        "Community": 5,
        "Owned": 3
    }
    score += tier_scores.get(proof.credibility_tier, 0)
    
    # Recency (from date_published)
    if proof.date_published:
        days_old = (datetime.now().date() - proof.date_published).days
        if days_old < 90: score += 10
        elif days_old < 180: score += 7
        elif days_old < 365: score += 5
        elif days_old < 730: score += 3
    
    # Proof signals count
    if proof.proof_signal:
        score += min(len(proof.proof_signal) * 5, 15)
    
    # Verification
    if proof.verification_status == "Verified":
        score += 15
    
    # Has screenshot
    if proof.screenshot_url:
        score += 5
    
    # Has summary
    if proof.summary and len(proof.summary) > 50:
        score += 5
    
    # Tag completeness
    tag_score = 0
    if proof.pain: tag_score += 3
    if proof.outcome: tag_score += 3
    if proof.hook_style: tag_score += 4
    score += tag_score
    
    return min(score, 100)
```

**Implementation Notes:**
- Auto-calculate on create/update
- Store in DB for fast sorting/filtering
- Expose score breakdown in API for transparency

**Validation:**
```python
# Unit tests
def test_verified_tier1_recent_scores_high():
    proof = ProofAsset(
        credibility_tier="Tier1",
        verification_status="Verified",
        date_published=date.today() - timedelta(days=30),
        proof_signal=["Recognized publication (major)", "Named customer"],
        screenshot_url="https://example.com/screenshot.png",
        summary="Detailed summary here",
        pain=["Not enough inbound / weak pipeline"],
        outcome=["More meetings booked"],
        hook_style="Name-drop question"
    )
    
    score = calculate_quality_score(proof)
    assert score >= 85  # High quality
    
def test_owned_unverified_old_scores_low():
    proof = ProofAsset(
        credibility_tier="Owned",
        verification_status="NeedsReview",
        date_published=date.today() - timedelta(days=1000)
    )
    
    score = calculate_quality_score(proof)
    assert score <= 20  # Low quality
```

**Acceptance Criteria:**
- [ ] Given Tier1 + Verified + recent, When scored, Then score >= 80
- [ ] Given Owned + unverified, When scored, Then score <= 30
- [ ] Given proof with all fields filled, When scored, Then score >= 70
- [ ] Given minimal proof (only required fields), When scored, Then score <= 40
- [ ] Given I update proof tags, When saved, Then quality_score recalculated
- [ ] Given score calculated, When I query breakdown, Then all factors shown

**Test Strategy:**
- Unit: 15+ test cases covering score ranges
- Property-based: Score always 0-100, deterministic
- Integration: Scores persist correctly

**Rollback:**
Set quality_score = 0 for all proofs

---

### Demo Validation (Sprint 0)

**Demo Flow:**
1. Upload 5 proof assets via UI (various types, personas, industries)
2. View proof library, filter by persona="Transportation Exec"
3. Click proof → edit modal → add pain/outcome tags → save
4. Sort by quality_score → verify high-quality proofs at top
5. Show duplicate detection: try uploading same URL with tracking params → 409 error

**Success Criteria:**
- [ ] All 5 uploads succeed with proof_ids
- [ ] Filters work correctly (persona, industry, service_line)
- [ ] Quality scores calculated and displayed
- [ ] Duplicate detection prevents re-adding same article
- [ ] Edit/save workflow preserves all tags

---

### SPRINT 1 — Retrieval API + "Single Best Proof" Selection

**Demo:**  
Given persona+industry+service+stage, system returns 1 recommended proof (with rationale).

#### Tickets

##### SPR1.1: Proof Retrieval Service (Deterministic Ranking)

**Priority:** CRITICAL  
**Dependencies:** SPR0 complete (proof library functional)

**One-liner:** Build retrieval service that ranks proofs by match score and returns best match with rationale

**Scope Boundaries (NOT included):**
- No semantic search (deterministic filters only)
- No learning from outcomes (static scoring)
- No proof packs yet

**Files:**
- Create: `src/services/proof_retrieval.py` (300 lines)
- Create: `src/routes/proof_retrieval.py` (150 lines)
- Create: `tests/unit/test_proof_retrieval.py` (250 lines)
- Create: `tests/integration/test_proof_retrieval.py` (200 lines)

**Contracts:**

**POST /api/proof-retrieval/recommend**
```json
{
  "persona": "Transportation Exec",
  "industry": "3PL",
  "service_line": "PR/Comms",
  "funnel_stage": "Cold outbound",
  "use_case": "Earn credibility fast",
  "limit": 3
}
```

**Response (200 OK):**
```json
{
  "recommendations": [
    {
      "proof_id": "uuid-1",
      "client_name": "OneRail",
      "publication_or_channel": "FreightWaves",
      "url": "https://freightwaves.com/...",
      "match_score": 92,
      "rationale": "Exact persona match (25pt) + industry match (20pt) + service line match (15pt) + funnel stage match (10pt) + Tier1 credibility (15pt) + recent (7pt)",
      "score_breakdown": {
        "persona_match": 25,
        "industry_match": 20,
        "service_line_match": 15,
        "funnel_stage_match": 10,
        "credibility_tier": 15,
        "recency": 7,
        "proof_signals": 0
      }
    },
    {
      "proof_id": "uuid-2",
      "match_score": 78,
      "rationale": "..."
    }
  ],
  "query": {
    "persona": "Transportation Exec",
    "industry": "3PL",
    "service_line": "PR/Comms",
    "funnel_stage": "Cold outbound"
  }
}
```

**Ranking Algorithm:**
```python
def calculate_match_score(proof: ProofAsset, query: RetrievalQuery) -> int:
    """
    Returns 0-100 match score based on query alignment.
    
    Weights:
    - Persona match: 0-25
      - Exact primary match: 25
      - In secondary list: 15
      - No match: 0
    - Industry match: 0-20
      - Exact match (any in array): 20
      - Related industry: 10  # e.g., "3PL" → "Broker / Freight Tech Services"
      - No match: 0
    - Service line match: 0-15
      - Primary match: 15
      - In secondary list: 10
      - No match: 0
    - Funnel stage match: 0-10
      - Exact match: 10
      - Adjacent stage: 5  # e.g., "Cold outbound" → "Warm outbound"
      - No match: 0
    - Credibility tier: 0-15 (same as quality score)
    - Recency: 0-10 (same as quality score)
    - Proof signals: 0-5 (bonus for multiple signals)
    """
    score = 0
    
    # Persona match
    if query.persona == proof.persona_primary:
        score += 25
    elif query.persona in (proof.persona_secondary or []):
        score += 15
    
    # Industry match
    if query.industry in (proof.industry or []):
        score += 20
    # TODO: Add industry relationship map for partial matches
    
    # Service line match
    if query.service_line == proof.service_line_primary:
        score += 15
    elif query.service_line in (proof.service_line_secondary or []):
        score += 10
    
    # Funnel stage match
    if query.funnel_stage == proof.funnel_stage:
        score += 10
    # TODO: Add stage adjacency logic
    
    # Credibility + recency (from quality score components)
    score += get_credibility_score(proof)
    score += get_recency_score(proof)
    
    # Proof signals bonus
    if proof.proof_signal and len(proof.proof_signal) >= 2:
        score += 5
    
    return min(score, 100)
```

**Hard Filters (Applied Before Ranking):**
- `verification_status = "Verified"` (auto-send eligible only)
- If `credibility_tier = "Owned"`, only include if no Tier1/Tier2/Trade available

**Implementation Notes:**
- Filter first, then rank remaining proofs
- Return top N (default 3)
- Include score breakdown for transparency
- Cache results for 5 minutes (proof library changes infrequently)

**Validation:**
```python
# Unit tests
def test_exact_persona_industry_service_scores_highest():
    query = RetrievalQuery(
        persona="Transportation Exec",
        industry="3PL",
        service_line="PR/Comms",
        funnel_stage="Cold outbound"
    )
    
    proof_exact = ProofAsset(
        persona_primary="Transportation Exec",
        industry=["3PL"],
        service_line_primary="PR/Comms",
        funnel_stage="Cold outbound",
        credibility_tier="Trade",
        verification_status="Verified",
        date_published=date.today()
    )
    
    proof_partial = ProofAsset(
        persona_primary="Ops Exec",
        industry=["3PL"],
        service_line_primary="PR/Comms",
        funnel_stage="Cold outbound",
        credibility_tier="Trade",
        verification_status="Verified"
    )
    
    score_exact = calculate_match_score(proof_exact, query)
    score_partial = calculate_match_score(proof_partial, query)
    
    assert score_exact > score_partial
    assert score_exact >= 85

# Integration test
def test_retrieval_returns_best_match(db_session):
    # Create 10 proofs with varying matches
    create_test_proofs(db_session)
    
    query = {
        "persona": "Transportation Exec",
        "industry": "3PL",
        "service_line": "PR/Comms",
        "funnel_stage": "Cold outbound",
        "limit": 3
    }
    
    response = client.post("/api/proof-retrieval/recommend", json=query)
    
    assert response.status_code == 200
    recommendations = response.json()["recommendations"]
    assert len(recommendations) <= 3
    assert recommendations[0]["match_score"] >= recommendations[1]["match_score"]
    assert "rationale" in recommendations[0]
```

**Acceptance Criteria:**
- [ ] Given exact persona+industry+service match exists, When retrieved, Then it ranks #1
- [ ] Given no exact match, When retrieved, Then best partial match returned
- [ ] Given only unverified proofs, When retrieved, Then empty results (hard filter)
- [ ] Given 3 requested, When 10 match, Then top 3 by score returned
- [ ] Given match_score calculated, When rationale generated, Then breakdown sums to score
- [ ] Given same query twice, When within cache window, Then same results (cache hit)

**Test Strategy:**
- Unit: Scoring algorithm with 20+ test cases
- Integration: Full retrieval flow with DB
- Snapshot: Golden test cases with expected rankings
- Performance: <50ms for retrieval on 1000+ proofs

**Rollback:**
Return empty recommendations, no scoring

---

##### SPR1.2: Semantic Search Fallback (Optional)

**Priority:** LOW  
**Dependencies:** SPR1.1 (deterministic retrieval working)

**One-liner:** Add semantic search when deterministic filters return <3 results

**Scope Boundaries (NOT included):**
- No custom embeddings model
- No vector index optimization (use basic pgvector)
- No hybrid search (deterministic OR semantic, not both)

**Files:**
- Modify: `src/services/proof_retrieval.py` (+150 lines - semantic search integration)
- Create: `src/services/proof_embeddings.py` (200 lines)
- Modify: `infra/migrations/versions/003_proof_assets.py` (+20 lines - add embedding column)

**Implementation Notes:**
- Use OpenAI text-embedding-3-small
- Embed: `{client_name} {publication} {summary} {persona_primary} {industry} {use_case}`
- Store in `embedding` column (vector(1536))
- Only query if deterministic returns <3 results
- Fallback threshold: cosine similarity > 0.7

**Validation:**
```python
def test_semantic_fallback_when_no_exact_match():
    query = {
        "persona": "Unknown Persona",  # Not in DB
        "industry": "Automotive",      # Not in DB
        "service_line": "PR/Comms"
    }
    
    # Create proof for similar industry
    proof = create_proof(
        persona_primary="Ops Exec",
        industry=["Manufacturing"],  # Similar to Automotive
        summary="Supply chain optimization for automotive parts..."
    )
    
    recommendations = retrieve(query)
    
    assert len(recommendations) > 0  # Semantic search found it
    assert recommendations[0]["proof_id"] == proof.proof_id
```

**Acceptance Criteria:**
- [ ] Given deterministic returns 0 results, When semantic search runs, Then similar proofs returned
- [ ] Given deterministic returns 5 results, When query completes, Then semantic search NOT triggered
- [ ] Given embedding generation fails, When retrieval runs, Then graceful fallback to deterministic only

**Test Strategy:**
- Integration: Semantic similarity tests
- Performance: Embedding generation <500ms

**Rollback:**
Remove embedding column, skip semantic search

---

##### SPR1.3: Rationale Generator

**Priority:** MEDIUM  
**Dependencies:** SPR1.1 (scoring algorithm)

**One-liner:** Generate human-readable explanation for why proof was selected

**Scope Boundaries (NOT included):**
- No LLM-generated prose (deterministic template only)
- No personalization beyond query parameters

**Files:**
- Create: `src/services/rationale_generator.py` (150 lines)
- Modify: `src/services/proof_retrieval.py` (+30 lines - call rationale generator)

**Rationale Template:**
```python
def generate_rationale(proof: ProofAsset, query: RetrievalQuery, score_breakdown: dict) -> str:
    """
    Generate rationale from score breakdown.
    
    Example output:
    "Exact persona match (25pt) + industry match (20pt) + service line match (15pt) + 
     funnel stage match (10pt) + Trade publication credibility (10pt) + recent (7pt)"
    """
    components = []
    
    if score_breakdown["persona_match"] == 25:
        components.append(f"Exact persona match ({score_breakdown['persona_match']}pt)")
    elif score_breakdown["persona_match"] > 0:
        components.append(f"Secondary persona match ({score_breakdown['persona_match']}pt)")
    
    if score_breakdown["industry_match"] == 20:
        components.append(f"Industry match ({score_breakdown['industry_match']}pt)")
    
    if score_breakdown["service_line_match"] > 0:
        components.append(f"Service line match ({score_breakdown['service_line_match']}pt)")
    
    if score_breakdown["funnel_stage_match"] == 10:
        components.append(f"Funnel stage match ({score_breakdown['funnel_stage_match']}pt)")
    
    # Credibility tier
    tier_name = proof.credibility_tier
    components.append(f"{tier_name} credibility ({score_breakdown['credibility_tier']}pt)")
    
    # Recency
    if score_breakdown["recency"] >= 7:
        components.append(f"Recent ({score_breakdown['recency']}pt)")
    
    return " + ".join(components)
```

**Validation:**
```python
def test_rationale_includes_all_scoring_factors():
    rationale = generate_rationale(proof, query, {
        "persona_match": 25,
        "industry_match": 20,
        "service_line_match": 15,
        "funnel_stage_match": 10,
        "credibility_tier": 10,
        "recency": 7
    })
    
    assert "Exact persona match (25pt)" in rationale
    assert "Industry match (20pt)" in rationale
    assert "Recent (7pt)" in rationale

def test_rationale_sums_to_total_score():
    rationale = generate_rationale(proof, query, breakdown)
    
    # Extract point values and sum
    points = [int(x) for x in re.findall(r'\((\d+)pt\)', rationale)]
    assert sum(points) == sum(breakdown.values())
```

**Acceptance Criteria:**
- [ ] Given score breakdown, When rationale generated, Then all non-zero components included
- [ ] Given rationale, When summed, Then equals total match_score
- [ ] Given no persona match, When rationale generated, Then persona component omitted
- [ ] Given rationale, When returned in API, Then string is < 300 chars

**Test Strategy:**
- Unit: Template rendering with various breakdowns
- Contract: Rationale format consistent

**Rollback:**
Return empty rationale string

---

##### SPR1.4: Proof Packs Feature (Curated Sets)

**Priority:** LOW  
**Dependencies:** SPR0 complete

**One-liner:** Create and retrieve curated proof collections for specific use cases

**Scope Boundaries (NOT included):**
- No automated pack generation
- No pack versioning
- No pack sharing across teams

**Files:**
- Create: `src/models/proof_pack.py` (100 lines)
- Create: `infra/migrations/versions/004_proof_packs.py` (80 lines)
- Create: `src/routes/proof_packs.py` (150 lines)
- Modify: `src/services/proof_retrieval.py` (+50 lines - support pack_id filter)

**Contracts:**

**POST /api/proof-packs**
```json
{
  "name": "Warehouse/3PL Credibility Pack",
  "description": "Top 10 proofs for warehouse ops leaders in 3PL space",
  "proof_ids": ["uuid-1", "uuid-2", "uuid-3", ...],
  "tags": {
    "persona": "Warehouse/Yard Ops Leader",
    "industry": "3PL",
    "use_case": "Earn credibility fast"
  }
}
```

**GET /api/proof-packs/{pack_id}/proofs**
```json
{
  "pack_name": "Warehouse/3PL Credibility Pack",
  "proofs": [
    { "proof_id": "uuid-1", ... },
    { "proof_id": "uuid-2", ... }
  ]
}
```

**Modified Retrieval (with pack preference):**
```json
{
  "persona": "Warehouse/Yard Ops Leader",
  "industry": "3PL",
  "prefer_pack": "warehouse-3pl-pack",
  "limit": 3
}
```
→ Returns proofs from pack first, then fills remaining slots with retrieval

**Validation:**
```python
def test_pack_retrieval_prefers_pack_proofs():
    pack = create_proof_pack(proof_ids=[proof1.id, proof2.id])
    
    query = {
        "persona": "Warehouse/Yard Ops Leader",
        "prefer_pack": pack.id,
        "limit": 3
    }
    
    recommendations = retrieve(query)
    
    # First 2 should be from pack
    assert recommendations[0]["proof_id"] in [proof1.id, proof2.id]
    assert recommendations[1]["proof_id"] in [proof1.id, proof2.id]
```

**Acceptance Criteria:**
- [ ] Given pack created, When I query pack endpoint, Then all proofs returned
- [ ] Given retrieval with pack preference, When pack proofs match, Then pack proofs ranked higher
- [ ] Given pack with 5 proofs, When I request 10, Then pack proofs + 5 from retrieval
- [ ] Given pack deleted, When retrieval references it, Then graceful fallback to standard retrieval

**Test Strategy:**
- Integration: Pack CRUD + retrieval integration
- Manual: UI for pack creation (stretch goal)

**Rollback:**
Remove pack preference logic, keep standard retrieval

---

### Demo Validation (Sprint 1)

**Demo Flow:**
1. POST retrieval query: persona=Transportation Exec, industry=3PL, service_line=PR/Comms
2. Show top 3 recommendations with match_scores and rationales
3. Modify query to persona=Unknown → show semantic fallback (if SPR1.2 done)
4. Create proof pack "3PL Executive Pack" with 5 proofs
5. Query with `prefer_pack` → show pack proofs ranked first

**Success Criteria:**
- [ ] Retrieval returns 1-3 proofs sorted by match_score
- [ ] Rationale explains scoring (readable by human)
- [ ] Proof pack retrieval works
- [ ] No unverified proofs in results

---

## SPRINT 2 — Message Engine v1 (Short Hooks + Link Follow-up)

**Demo:**  
Generate 2-step sequence:
- Step 1: 1-2 line hook, no link
- Step 2: 1 proof link, 1 sentence context, soft CTA

*(Detailed tickets for Sprint 2-8 available upon request - continuing with same atomic structure)*

---

## EVALUATION FRAMEWORK

### Offline Test Harness

**Golden Set (50 scenarios):**
```json
{
  "scenario_id": "sc-001",
  "persona": "Transportation Exec",
  "industry": "3PL",
  "service_line": "PR/Comms",
  "funnel_stage": "Cold outbound",
  "expected_constraints": {
    "step1_max_chars": 150,
    "step1_link_count": 0,
    "step2_link_count": 1,
    "step2_max_chars": 200,
    "forbidden_claims": ["guaranteed", "majors", "results guaranteed"],
    "required_proof_id": true
  }
}
```

**Constraint Checks:**
- Length: `len(message) <= max_chars`
- Link count: `count_links(message) == expected`
- Proof citation: `proof_id in metadata`
- Forbidden claims: `no_forbidden_phrases(message)`
- Hook strength: deterministic checks (starts with question mark, has client name, etc.)

**Evaluation Metrics:**
- Constraint pass rate: % scenarios passing all checks
- Clarity rating: heuristic (sentence count, avg word length, readability score)
- Hook diversity: % unique openers across scenarios

---

## DEFINITION OF DONE (GLOBAL)

**Per Sprint:**
- [ ] All tickets meet atomic + committable standard
- [ ] Tests pass (unit + integration + manual validation documented)
- [ ] Demo script executed successfully
- [ ] Merged to main
- [ ] No regressions (existing tests still pass)

**System-wide (End State):**
- [ ] Every proof-based message stores proof_id + variant_id + rationale
- [ ] No unverified proof can be used for auto-send
- [ ] Dashboard shows proof performance and variant performance
- [ ] Review pipeline exists and is used for high-risk output
- [ ] End-to-end demo: upload proof → tag → retrieve → generate → review → send → measure
- [ ] Offline test harness runs on CI (all golden scenarios pass)
- [ ] Rollback procedures documented for each major component

---

## RECOMMENDED TEAM MAKEUP

**Full-time roles (aligned to BUILD_PHILOSOPHY.md):**

1. **Backend Engineer** (owner: SPR0, SPR1, database/API)
   - Owns: ProofAsset schema, retrieval API, scoring algorithms
   - Skills: Python, PostgreSQL, FastAPI, testing

2. **Frontend Engineer** (owner: UI/dashboard tickets)
   - Owns: Proof library UI, upload forms, filter/search, dashboard widgets
   - Skills: HTML/CSS/JS, React (optional), API integration

3. **Agent Engineer** (owner: SPR2+, message generation, orchestration)
   - Owns: Message engine, agent roles, review workflow
   - Skills: LLM integration, prompt engineering, agentic systems

4. **QA/Test Engineer** (owner: test harness, validation, compliance)
   - Owns: Offline eval framework, golden scenarios, regression suite
   - Skills: pytest, test automation, quality gates

**Part-time/advisory:**
- **GTM Strategist** (defines personas, playbooks, proof strategy)
- **Compliance Lead** (defines forbidden claims, review policies)
- **Data Analyst** (dashboard design, metrics definitions, lift analysis)

**Agent role mapping:**
- Proof Librarian → QA Engineer (manual review) + automation scripts
- Creative Director → GTM Strategist + Agent Engineer (template design)
- Compliance/Truth → Compliance Lead + automated linting
- Strategy Operator → GTM Strategist
- Data/Analytics → Data Analyst + Backend Engineer (instrumentation)

---

## DEPENDENCIES & INTEGRATION

**Depends on (from existing roadmap):**
- Phase 4 Task 4.1: Database schema (ProofAsset uses same migration infra)
- Phase 4 Task 4.4: Async processing (message generation can be queued)
- Phase 4 Task 4.5: Operator dashboard (proof dashboard extends same UI)

**Provides to (downstream):**
- Phase 5+: Proof-assisted outreach campaigns
- Phase 5+: A/B testing framework (variants reference proof_ids)
- Phase 6+: Metrics for proof performance, conversion attribution

**Parallel work (no blocking):**
- Can build SPR0-1 while Phase 4 Task 4.2-4.3 in progress
- SPR2+ (message generation) waits for Phase 4 Task 4.4 (async queue)

---

## SUBAGENT REVIEW PROMPT

```
You are a senior software architect reviewing a sprint roadmap for a Social Proof Outreach system.

Context:
- This is an additive feature to an existing B2B sales agent platform
- Goal: Enable short, punchy outreach messages backed by social proof (PR placements, case studies, etc.)
- Principles: Atomic tasks, clear validation, no timelines, demoable sprints
- Tech stack: Python, FastAPI, PostgreSQL, existing agent framework

Review this roadmap (SOCIAL_PROOF_ROADMAP.md) for:

1. **Atomicity gaps:** Are any tickets trying to do too much? Can they be split further?
2. **Missing tests:** Which tickets lack sufficient test coverage or validation criteria?
3. **Hidden dependencies:** Are there unstated assumptions or dependencies between tickets?
4. **Scope creep risks:** Where might "just one more thing" sneak in?
5. **Compliance/safety gaps:** What could go wrong with auto-sending messages? Are guardrails sufficient?
6. **Performance risks:** Which operations could become slow at scale (1000+ proofs, 100+ messages/day)?
7. **Rollback issues:** Are rollback procedures realistic? What's missing?
8. **Data quality:** How does the system prevent tag graveyard / taxonomy chaos?
9. **Better sequencing:** Should any sprints be reordered for faster value delivery or reduced risk?
10. **Missing observability:** What metrics/logs are critical but not instrumented?

For each issue found, provide:
- Severity: CRITICAL / HIGH / MEDIUM / LOW
- Ticket ID(s) affected
- Specific recommendation (not vague "add more tests")
- Alternative approach if major refactor needed

Output format:
## Issue 1: [Title]
**Severity:** [CRITICAL/HIGH/MEDIUM/LOW]
**Affected Tickets:** [SPR0.1, SPR1.2, ...]
**Problem:** [1-2 sentence description]
**Recommendation:** [Specific, actionable fix]

Aim for 8-12 high-value issues. Prioritize issues that could cause production incidents or block progress.
```

---

**END OF ROADMAP**

**Status:** Ready for review  
**Next Actions:**
1. Run subagent review (paste prompt above into new agent)
2. Incorporate feedback
3. Commit to repo
4. Begin Sprint 0 execution (parallel to Phase 4 work)

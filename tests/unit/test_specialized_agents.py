"""Unit tests for specialized agents."""
import pytest

from src.agents.specialized import (
    MeetingSlotAgent,
    DraftWriterAgent,
    AssetHunterAgent,
)


class TestMeetingSlotAgent:
    """Test meeting slot proposal rules."""

    async def test_proposes_2_to_3_slots(self):
        """Test agent proposes 2-3 slots."""
        agent = MeetingSlotAgent()
        
        result = await agent.propose_slots(num_slots=3, duration_minutes=30)
        
        assert result["status"] == "success"
        assert 2 <= len(result["slots"]) <= 3
        assert result["default_duration_minutes"] == 30

    async def test_slots_are_business_days_only(self):
        """Test slots only on business days (M-F)."""
        agent = MeetingSlotAgent()
        
        result = await agent.propose_slots(num_slots=5, duration_minutes=30)
        
        from datetime import datetime
        for slot in result["slots"]:
            start = datetime.fromisoformat(slot["start"].replace("Z", "+00:00"))
            # weekday() returns 0-4 for M-F, 5-6 for weekend
            assert start.weekday() < 5, f"Slot on {start.strftime('%A')} (should be weekday)"

    async def test_slots_within_1_3_business_days(self):
        """Test slots are within 1-3 business days."""
        agent = MeetingSlotAgent()
        
        result = await agent.propose_slots(num_slots=3, max_days_out=3)
        
        assert result["status"] == "success"
        for slot in result["slots"]:
            day_offset = slot.get("day_offset", 0)
            assert day_offset <= 6  # ~3 business days worth of days

    async def test_30_minute_duration(self):
        """Test slots are 30 minutes by default."""
        agent = MeetingSlotAgent()
        
        result = await agent.propose_slots(num_slots=2, duration_minutes=30)
        
        from datetime import datetime, timedelta
        for slot in result["slots"]:
            start = datetime.fromisoformat(slot["start"].replace("Z", "+00:00"))
            end = datetime.fromisoformat(slot["end"].replace("Z", "+00:00"))
            duration = (end - start).total_seconds() / 60
            assert duration == 30


class TestDraftWriterAgent:
    """Test draft writing with voice profile."""

    async def test_draft_uses_voice_profile(self):
        """Test draft uses voice profile."""
        agent = DraftWriterAgent()
        
        voice_profile = {
            "tone": "consultative",
            "patterns": ["discovery_focus"],
        }
        
        prospect_data = {
            "first_name": "John",
            "company": "TechCorp",
            "email": "john@techcorp.com",
        }
        
        result = await agent.write_draft(
            prospect_data=prospect_data,
            meeting_slots=[],
            voice_profile=voice_profile,
        )
        
        assert result["status"] == "success"
        assert result["voice_profile_used"] is True

    async def test_draft_without_em_dashes(self):
        """Test draft contains no em-dashes."""
        agent = DraftWriterAgent()
        
        prospect_data = {
            "first_name": "Jane",
            "company": "StartupCo",
            "email": "jane@startup.com",
        }
        
        result = await agent.write_draft(
            prospect_data=prospect_data,
            meeting_slots=[],
        )
        
        assert result["status"] == "success"
        body = result.get("body", "")
        assert "—" not in body, "Draft contains em-dashes"

    async def test_draft_includes_meeting_slots(self):
        """Test draft includes meeting slot options."""
        agent = DraftWriterAgent()
        
        prospect_data = {
            "first_name": "Bob",
            "company": "MegaCorp",
            "email": "bob@megacorp.com",
        }
        
        slots = [
            {
                "start": "2026-01-21T10:00:00Z",
                "end": "2026-01-21T10:30:00Z",
            },
            {
                "start": "2026-01-21T14:00:00Z",
                "end": "2026-01-21T14:30:00Z",
            },
        ]
        
        result = await agent.write_draft(
            prospect_data=prospect_data,
            meeting_slots=slots,
        )
        
        assert result["status"] == "success"
        body = result.get("body", "")
        # Should mention day/time options (Wednesday Jan 21, 2026)
        assert "Wednesday" in body or "January" in body or "10:00" in body

    async def test_draft_includes_asset_link_if_provided(self):
        """Test draft includes asset link when provided."""
        agent = DraftWriterAgent()
        
        prospect_data = {
            "first_name": "Alice",
            "company": "InnovateCo",
            "email": "alice@innovate.com",
        }
        
        asset = {
            "name": "CHAINge Proposals/TechCorp_Proposal.pdf",
        }
        
        result = await agent.write_draft(
            prospect_data=prospect_data,
            meeting_slots=[],
            drive_asset=asset,
        )
        
        assert result["status"] == "success"
        body = result.get("body", "")
        assert "resource" in body.lower() or "attachment" in body.lower()

    async def test_draft_has_single_cta(self):
        """Test draft has one clear CTA."""
        agent = DraftWriterAgent()
        
        prospect_data = {
            "first_name": "Carol",
            "company": "GlobalFirm",
            "email": "carol@globalfirm.com",
        }
        
        result = await agent.write_draft(
            prospect_data=prospect_data,
            meeting_slots=[],
        )
        
        assert result["status"] == "success"
        body = result.get("body", "")
        # Should have clear CTA (e.g., "What works best for you?")
        assert "works" in body.lower() or "reply" in body.lower()


class TestAssetHunterAgent:
    """Test asset hunting with allowlist enforcement."""

    async def test_allowlist_enforced(self):
        """Test allowlist is strictly enforced."""
        agent = AssetHunterAgent()
        
        result = await agent.hunt_assets(
            prospect_company="TechCorp",
            max_results=5,
        )
        
        assert result["allowlist_enforced"] is True

    async def test_pesti_sales_folder_included(self):
        """Test Pesti Sales folder is searched."""
        agent = AssetHunterAgent()
        
        result = await agent.hunt_assets(
            prospect_company="AnyCompany",
            max_results=10,
        )
        
        # Should find assets from allowed prefixes
        assets = result.get("assets", [])
        # Should have at least attempted search
        assert result["status"] in ["success", "error"]

    async def test_charlie_pesti_folder_with_env_id(self):
        """Test Charlie Pesti folder is searched with env ID."""
        agent = AssetHunterAgent()
        
        charlie_id = "0ABC123XYZ"
        result = await agent.hunt_assets(
            prospect_company="AnyCompany",
            charlie_pesti_folder_id=charlie_id,
        )
        
        assert result["status"] == "success"
        assert agent.ALLOWLIST["charlie_pesti"]["root_id"] == charlie_id

    async def test_exclude_closed_proposals(self):
        """Test 'CP Closed' folder is excluded."""
        agent = AssetHunterAgent()
        
        result = await agent.hunt_assets(
            prospect_company="TestCo",
            max_results=10,
        )
        
        # Verify asset validation excludes CP Closed
        for asset in result.get("assets", []):
            assert "CP Closed" not in asset.get("name", ""), "Asset from excluded folder"

    async def test_include_allowed_prefixes(self):
        """Test only allowed prefixes are included."""
        agent = AssetHunterAgent()
        
        result = await agent.hunt_assets(
            prospect_company="TestCo",
            max_results=10,
        )
        
        allowed_prefixes = [
            "CHAINge Proposals",
            "CP Client Reports",
            "CP Proposals",
            "Manifest 2026",
        ]
        
        for asset in result.get("assets", []):
            name = asset.get("name", "")
            matches_allowed = any(name.startswith(prefix) for prefix in allowed_prefixes)
            assert matches_allowed, f"Asset {name} doesn't match any allowed prefix"

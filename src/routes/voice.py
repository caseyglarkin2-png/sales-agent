"""API routes for Voice Profile management and training."""
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import json

from src.logger import get_logger
from src.voice_profile import (
    VoiceProfile,
    get_voice_profile_manager,
    get_voice_profile,
)
from src.voice_trainer import VoiceProfileTrainer, create_trainer

logger = get_logger(__name__)

router = APIRouter(prefix="/api/voice", tags=["voice-profiles"])

# Global trainer instance (will be initialized with connectors at runtime)
_trainer: Optional[VoiceProfileTrainer] = None


def get_trainer() -> VoiceProfileTrainer:
    """Get or create the trainer instance."""
    global _trainer
    if _trainer is None:
        _trainer = create_trainer()
    return _trainer


def set_trainer_connectors(hubspot_connector=None, gmail_connector=None) -> None:
    """Set connectors on the global trainer."""
    global _trainer
    _trainer = create_trainer(
        hubspot_connector=hubspot_connector,
        gmail_connector=gmail_connector,
    )


class CreateProfileRequest(BaseModel):
    """Request to create a voice profile."""
    name: str
    tone: str = "professional"
    style_notes: List[str] = []
    use_contractions: bool = True
    max_paragraphs: int = 3
    include_ps: bool = True
    signature_style: str = "Best"
    slot_count: int = 3


class TrainFromHubSpotRequest(BaseModel):
    """Request to train from HubSpot emails."""
    profile_name: str
    search_query: str = "casey.l@pesti.io"
    limit: int = 20


class TrainFromSentEmailsRequest(BaseModel):
    """Request to train from sent emails in HubSpot."""
    profile_name: str = "casey_larkin"
    owner_email: str = "casey.l@pesti.io"
    limit: int = 50


class ManualTrainingSamplesRequest(BaseModel):
    """Request to add multiple training samples at once."""
    samples: List[str]
    profile_name: str = "casey_trained"


class AddTrainingSampleRequest(BaseModel):
    """Request to add a training sample."""
    text: str
    source: str = "manual"
    subject: str = "Training Sample"


@router.get("/profiles", response_model=List[Dict[str, Any]])
async def list_profiles() -> List[Dict[str, Any]]:
    """List all available voice profiles."""
    try:
        manager = get_voice_profile_manager()
        profiles = []
        
        for name in manager.list_profiles():
            profile = manager.get_profile(name)
            profiles.append({
                "id": name,
                "name": profile.name,
                "tone": profile.tone,
                "style_notes": profile.style_notes,
                "use_contractions": profile.use_contractions,
                "max_paragraphs": profile.max_paragraphs,
                "include_ps": profile.include_ps,
                "signature_style": profile.signature_style,
                "slot_count": profile.slot_count,
            })
        
        return profiles
    except Exception as e:
        logger.error(f"Error listing profiles: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/profiles/{profile_id}", response_model=Dict[str, Any])
async def get_profile(profile_id: str) -> Dict[str, Any]:
    """Get a specific voice profile."""
    try:
        profile = get_voice_profile(profile_id)
        return {
            "id": profile_id,
            "name": profile.name,
            "tone": profile.tone,
            "style_notes": profile.style_notes,
            "use_contractions": profile.use_contractions,
            "max_paragraphs": profile.max_paragraphs,
            "include_ps": profile.include_ps,
            "signature_style": profile.signature_style,
            "slot_count": profile.slot_count,
            "prohibited_words": profile.prohibited_words,
            "prohibited_punctuation": profile.prohibited_punctuation,
            "prompt_context": profile.to_prompt_context(),
        }
    except Exception as e:
        logger.error(f"Error getting profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/profiles", response_model=Dict[str, Any])
async def create_profile(request: CreateProfileRequest) -> Dict[str, Any]:
    """Create a new voice profile."""
    try:
        profile = VoiceProfile(
            name=request.name,
            tone=request.tone,
            style_notes=request.style_notes,
            use_contractions=request.use_contractions,
            max_paragraphs=request.max_paragraphs,
            include_ps=request.include_ps,
            signature_style=request.signature_style,
            slot_count=request.slot_count,
        )
        
        manager = get_voice_profile_manager()
        manager.add_profile(profile)
        
        logger.info(f"Created voice profile: {request.name}")
        return {
            "id": request.name.lower().replace(" ", "_"),
            "name": profile.name,
            "status": "created",
        }
    except Exception as e:
        logger.error(f"Error creating profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/training/status", response_model=Dict[str, Any])
async def get_training_status() -> Dict[str, Any]:
    """Get current training status."""
    try:
        trainer = get_trainer()
        return trainer.get_training_status()
    except Exception as e:
        logger.error(f"Error getting training status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/training/samples", response_model=Dict[str, Any])
async def add_training_sample(request: AddTrainingSampleRequest) -> Dict[str, Any]:
    """Add a training sample manually."""
    try:
        trainer = get_trainer()
        trainer.add_text_sample(
            text=request.text,
            source=request.source,
            subject=request.subject,
        )
        
        return {
            "status": "added",
            "samples_count": len(trainer.training_samples),
        }
    except Exception as e:
        logger.error(f"Error adding training sample: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/training/upload", response_model=Dict[str, Any])
async def upload_training_file(
    file: UploadFile = File(...),
    profile_name: str = Form(default="uploaded"),
) -> Dict[str, Any]:
    """Upload a file for training (txt, json, or email export)."""
    try:
        trainer = get_trainer()
        content = await file.read()
        text = content.decode("utf-8")
        
        # Handle different file types
        if file.filename.endswith(".json"):
            # JSON array of samples
            data = json.loads(text)
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, str):
                        trainer.add_text_sample(item, source="upload")
                    elif isinstance(item, dict):
                        trainer.add_text_sample(
                            text=item.get("body", item.get("text", "")),
                            source="upload",
                            subject=item.get("subject", "Uploaded"),
                        )
            else:
                trainer.add_text_sample(text, source="upload")
        else:
            # Plain text
            trainer.add_text_sample(
                text=text,
                source="upload",
                subject=file.filename or "Uploaded File",
            )
        
        return {
            "status": "uploaded",
            "filename": file.filename,
            "samples_count": len(trainer.training_samples),
        }
    except Exception as e:
        logger.error(f"Error uploading file: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/training/analyze", response_model=Dict[str, Any])
async def analyze_samples() -> Dict[str, Any]:
    """Analyze all training samples."""
    try:
        trainer = get_trainer()
        
        if not trainer.training_samples:
            raise HTTPException(status_code=400, detail="No training samples available")
        
        analysis = await trainer.analyze_samples()
        
        return {
            "status": "analyzed",
            "samples_analyzed": len(trainer.training_samples),
            "analysis": {
                "tone": analysis.tone,
                "formality_level": analysis.formality_level,
                "avg_sentence_length": analysis.avg_sentence_length,
                "common_greetings": analysis.common_greetings,
                "common_sign_offs": analysis.common_sign_offs,
                "common_phrases": analysis.common_phrases,
                "style_notes": analysis.style_notes,
                "uses_contractions": analysis.uses_contractions,
                "uses_questions": analysis.uses_questions,
                "uses_ps": analysis.uses_ps,
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing samples: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/training/create-profile", response_model=Dict[str, Any])
async def create_profile_from_training(profile_name: str) -> Dict[str, Any]:
    """Create a voice profile from analyzed training samples."""
    try:
        trainer = get_trainer()
        
        if not trainer.training_samples:
            raise HTTPException(status_code=400, detail="No training samples available")
        
        # Analyze and create
        analysis = await trainer.analyze_samples()
        profile = await trainer.create_profile_from_analysis(profile_name, analysis)
        
        return {
            "status": "created",
            "profile_id": profile_name.lower().replace(" ", "_"),
            "profile_name": profile.name,
            "tone": profile.tone,
            "samples_used": len(trainer.training_samples),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating profile from training: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/training/hubspot", response_model=Dict[str, Any])
async def train_from_hubspot(request: TrainFromHubSpotRequest) -> Dict[str, Any]:
    """Train a voice profile from HubSpot marketing emails."""
    try:
        trainer = get_trainer()
        
        if not trainer.hubspot_connector:
            # Return mock data for now if no connector
            return {
                "status": "error",
                "message": "HubSpot connector not configured. Add samples manually or upload a file.",
                "suggestion": "Use /api/voice/training/samples or /api/voice/training/upload",
            }
        
        profile = await trainer.train_from_hubspot(
            profile_name=request.profile_name,
            search_query=request.search_query,
            limit=request.limit,
        )
        
        return {
            "status": "success",
            "profile_id": request.profile_name.lower().replace(" ", "_"),
            "profile_name": profile.name,
            "tone": profile.tone,
            "emails_analyzed": len(trainer.training_samples),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error training from HubSpot: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/training/clear", response_model=Dict[str, Any])
async def clear_training_samples() -> Dict[str, Any]:
    """Clear all training samples."""
    try:
        global _trainer
        _trainer = create_trainer()
        
        return {
            "status": "cleared",
            "samples_count": 0,
        }
    except Exception as e:
        logger.error(f"Error clearing training samples: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/training/sent-emails", response_model=Dict[str, Any])
async def train_from_sent_emails(request: TrainFromSentEmailsRequest) -> Dict[str, Any]:
    """Train a voice profile from sent emails in HubSpot.
    
    This pulls actual emails sent by a specific user (like Casey) 
    to train the voice profile on real communication style.
    """
    try:
        from src.connectors.hubspot import create_hubspot_connector
        import re
        
        hubspot = create_hubspot_connector()
        trainer = get_trainer()
        
        # Fetch sent emails from HubSpot
        logger.info(f"Fetching sent emails for {request.owner_email}")
        emails = await hubspot.get_email_engagements(
            owner_email=request.owner_email,
            limit=request.limit,
            sent_only=True,
        )
        
        if not emails:
            return {
                "status": "warning",
                "message": f"No sent emails found for {request.owner_email}",
                "suggestion": "Check if the email matches a HubSpot owner and has sent emails logged",
                "emails_found": 0,
            }
        
        # Clean and add each email as a training sample
        samples_added = 0
        for email in emails:
            body = email.get("body", "")
            subject = email.get("subject", "")
            
            # Strip HTML if present
            if "<" in body and ">" in body:
                body = re.sub(r'<[^>]+>', '', body)
            
            # Skip if too short
            if len(body) < 50:
                continue
            
            trainer.add_text_sample(
                text=body,
                source=f"hubspot_sent_{email.get('id', 'unknown')}",
                subject=subject,
            )
            samples_added += 1
        
        if samples_added == 0:
            return {
                "status": "warning",
                "message": "Emails found but none had sufficient content for training",
                "emails_found": len(emails),
                "samples_added": 0,
            }
        
        # Analyze and create profile
        analysis = await trainer.analyze_samples()
        profile = await trainer.create_profile_from_analysis(request.profile_name, analysis)
        
        # Save the profile
        manager = get_voice_profile_manager()
        manager.profiles[request.profile_name.lower().replace(" ", "_")] = profile
        
        return {
            "status": "success",
            "profile_id": request.profile_name.lower().replace(" ", "_"),
            "profile_name": profile.name,
            "tone": profile.tone,
            "emails_analyzed": len(emails),
            "samples_used": samples_added,
            "analysis_summary": {
                "formality_level": analysis.formality_level,
                "uses_contractions": analysis.uses_contractions,
                "common_greetings": analysis.common_greetings[:3] if analysis.common_greetings else [],
                "common_sign_offs": analysis.common_sign_offs[:3] if analysis.common_sign_offs else [],
                "style_notes": analysis.style_notes[:5] if analysis.style_notes else [],
            }
        }
    except Exception as e:
        logger.error(f"Error training from sent emails: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/hubspot/diagnostic", response_model=Dict[str, Any])
async def hubspot_diagnostic() -> Dict[str, Any]:
    """Diagnose HubSpot connection and available emails."""
    try:
        from src.connectors.hubspot import create_hubspot_connector
        import os
        
        hubspot = create_hubspot_connector()
        api_key = os.environ.get("HUBSPOT_API_KEY", "")
        
        result = {
            "api_key_set": bool(api_key),
            "api_key_preview": f"{api_key[:10]}...{api_key[-4:]}" if len(api_key) > 14 else "too_short",
            "tests": {}
        }
        
        # Test 1: Try to list any emails
        import httpx
        async with httpx.AsyncClient(timeout=30) as client:
            # Test contacts access
            try:
                resp = await client.get(
                    f"{hubspot.BASE_URL}/crm/v3/objects/contacts?limit=1",
                    headers=hubspot.headers
                )
                result["tests"]["contacts_access"] = {
                    "status_code": resp.status_code,
                    "success": resp.status_code == 200,
                    "count": resp.json().get("total", 0) if resp.status_code == 200 else None
                }
            except Exception as e:
                result["tests"]["contacts_access"] = {"error": str(e)}
            
            # Test emails access
            try:
                resp = await client.post(
                    f"{hubspot.BASE_URL}/crm/v3/objects/emails/search",
                    headers=hubspot.headers,
                    json={"limit": 5, "sorts": [{"propertyName": "hs_createdate", "direction": "DESCENDING"}]}
                )
                result["tests"]["emails_access"] = {
                    "status_code": resp.status_code,
                    "success": resp.status_code == 200
                }
                if resp.status_code == 200:
                    data = resp.json()
                    result["tests"]["emails_access"]["total"] = data.get("total", 0)
                    result["tests"]["emails_access"]["sample_count"] = len(data.get("results", []))
                    if data.get("results"):
                        sample = data["results"][0].get("properties", {})
                        result["tests"]["emails_access"]["sample_from"] = sample.get("hs_email_from_email", "N/A")
                        result["tests"]["emails_access"]["sample_subject"] = sample.get("hs_email_subject", "N/A")[:50]
            except Exception as e:
                result["tests"]["emails_access"] = {"error": str(e)}
            
            # Test owners access (to find valid email addresses)
            try:
                resp = await client.get(
                    f"{hubspot.BASE_URL}/crm/v3/owners",
                    headers=hubspot.headers
                )
                result["tests"]["owners_access"] = {
                    "status_code": resp.status_code,
                    "success": resp.status_code == 200
                }
                if resp.status_code == 200:
                    owners = resp.json().get("results", [])
                    result["tests"]["owners_access"]["owners"] = [
                        {"email": o.get("email"), "name": f"{o.get('firstName', '')} {o.get('lastName', '')}".strip()}
                        for o in owners[:5]
                    ]
            except Exception as e:
                result["tests"]["owners_access"] = {"error": str(e)}
        
        return result
    except Exception as e:
        logger.error(f"Diagnostic error: {e}")
        return {"error": str(e)}


@router.post("/training/quick", response_model=Dict[str, Any])
async def quick_train_from_samples(request: ManualTrainingSamplesRequest) -> Dict[str, Any]:
    """Quickly train a voice profile from provided email samples.
    
    Provide a list of example emails and get a trained voice profile.
    """
    try:
        trainer = get_trainer()
        
        # Clear existing samples
        trainer.training_samples = []
        
        # Add all samples
        for i, sample in enumerate(request.samples):
            if len(sample) >= 50:  # Minimum viable sample
                trainer.add_text_sample(
                    text=sample,
                    source=f"quick_train_{i}",
                    subject=f"Sample {i+1}",
                )
        
        if not trainer.training_samples:
            raise HTTPException(
                status_code=400, 
                detail="No valid samples provided (each sample needs at least 50 characters)"
            )
        
        # Analyze and create profile
        analysis = await trainer.analyze_samples()
        profile = await trainer.create_profile_from_analysis(request.profile_name, analysis)
        
        # Save the profile
        manager = get_voice_profile_manager()
        profile_id = request.profile_name.lower().replace(" ", "_")
        manager.profiles[profile_id] = profile
        
        return {
            "status": "success",
            "profile_id": profile_id,
            "profile_name": profile.name,
            "tone": profile.tone,
            "samples_used": len(trainer.training_samples),
            "analysis": {
                "formality_level": analysis.formality_level,
                "uses_contractions": analysis.uses_contractions,
                "common_phrases": analysis.common_phrases[:5] if analysis.common_phrases else [],
                "style_notes": analysis.style_notes[:5] if analysis.style_notes else [],
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in quick training: {e}")
        raise HTTPException(status_code=500, detail=str(e))


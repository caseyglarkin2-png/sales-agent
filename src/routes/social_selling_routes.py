"""
Social Selling Routes - Social Selling API
============================================
REST API endpoints for social selling, profiles, posts, and interactions.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Any, Optional
from pydantic import BaseModel
from datetime import datetime

from ..social_selling import (
    SocialSellingService,
    get_social_selling_service,
)
from ..social_selling.social_selling_service import (
    SocialPlatform,
    PostType,
    InteractionType,
    PostStatus,
    CampaignStatus,
)


router = APIRouter(prefix="/social-selling", tags=["Social Selling"])


# Request models
class ConnectProfileRequest(BaseModel):
    """Connect profile request."""
    platform: str
    username: str
    profile_url: str
    display_name: Optional[str] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None


class CreatePostRequest(BaseModel):
    """Create post request."""
    profile_id: str
    post_type: str
    content: str
    media_urls: Optional[list[str]] = None
    hashtags: Optional[list[str]] = None
    mentions: Optional[list[str]] = None
    scheduled_at: Optional[datetime] = None


class UpdateMetricsRequest(BaseModel):
    """Update post metrics request."""
    likes_count: Optional[int] = None
    comments_count: Optional[int] = None
    shares_count: Optional[int] = None
    views_count: Optional[int] = None
    clicks_count: Optional[int] = None


class TrackInteractionRequest(BaseModel):
    """Track interaction request."""
    profile_id: str
    interaction_type: str
    target_username: Optional[str] = None
    target_post_id: Optional[str] = None
    content: Optional[str] = None
    contact_id: Optional[str] = None
    lead_id: Optional[str] = None


class CreateCampaignRequest(BaseModel):
    """Create campaign request."""
    name: str
    platforms: list[str]
    description: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    goals: Optional[dict[str, Any]] = None


def get_service() -> SocialSellingService:
    """Get social selling service instance."""
    return get_social_selling_service()


# Enums
@router.get("/platforms")
async def list_platforms():
    """List social platforms."""
    return {
        "platforms": [
            {"value": p.value, "name": p.name}
            for p in SocialPlatform
        ]
    }


@router.get("/post-types")
async def list_post_types():
    """List post types."""
    return {
        "types": [
            {"value": t.value, "name": t.name}
            for t in PostType
        ]
    }


@router.get("/interaction-types")
async def list_interaction_types():
    """List interaction types."""
    return {
        "types": [
            {"value": t.value, "name": t.name}
            for t in InteractionType
        ]
    }


# Profiles
@router.post("/profiles")
async def connect_profile(
    request: ConnectProfileRequest,
    user_id: str,
    org_id: str,
):
    """Connect a social media profile."""
    service = get_service()
    
    try:
        platform = SocialPlatform(request.platform)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid platform")
    
    profile = await service.connect_profile(
        platform=platform,
        username=request.username,
        profile_url=request.profile_url,
        user_id=user_id,
        org_id=org_id,
        display_name=request.display_name,
        access_token=request.access_token,
        refresh_token=request.refresh_token,
    )
    
    return {
        "id": profile.id,
        "platform": profile.platform.value,
        "username": profile.username,
        "profile_url": profile.profile_url,
    }


@router.get("/profiles")
async def list_profiles(
    user_id: Optional[str] = None,
    org_id: Optional[str] = None,
    platform: Optional[str] = None,
):
    """List social profiles."""
    service = get_service()
    
    plat = None
    if platform:
        try:
            plat = SocialPlatform(platform)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid platform")
    
    profiles = await service.list_profiles(user_id, org_id, plat)
    
    return {
        "profiles": [
            {
                "id": p.id,
                "platform": p.platform.value,
                "username": p.username,
                "display_name": p.display_name,
                "profile_url": p.profile_url,
                "followers_count": p.followers_count,
                "following_count": p.following_count,
                "is_connected": p.is_connected,
            }
            for p in profiles
        ]
    }


@router.get("/profiles/{profile_id}")
async def get_profile(profile_id: str):
    """Get a profile by ID."""
    service = get_service()
    profile = await service.get_profile(profile_id)
    
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    return {
        "id": profile.id,
        "platform": profile.platform.value,
        "username": profile.username,
        "display_name": profile.display_name,
        "profile_url": profile.profile_url,
        "bio": profile.bio,
        "avatar_url": profile.avatar_url,
        "followers_count": profile.followers_count,
        "following_count": profile.following_count,
        "posts_count": profile.posts_count,
        "is_connected": profile.is_connected,
        "created_at": profile.created_at.isoformat(),
    }


@router.delete("/profiles/{profile_id}")
async def disconnect_profile(profile_id: str):
    """Disconnect a social profile."""
    service = get_service()
    
    if not await service.disconnect_profile(profile_id):
        raise HTTPException(status_code=404, detail="Profile not found")
    
    return {"success": True}


# Posts
@router.post("/posts")
async def create_post(request: CreatePostRequest, user_id: Optional[str] = None):
    """Create a social media post."""
    service = get_service()
    
    try:
        post_type = PostType(request.post_type)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid post type")
    
    post = await service.create_post(
        profile_id=request.profile_id,
        post_type=post_type,
        content=request.content,
        media_urls=request.media_urls,
        hashtags=request.hashtags,
        mentions=request.mentions,
        scheduled_at=request.scheduled_at,
        created_by=user_id,
    )
    
    if not post:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    return {
        "id": post.id,
        "platform": post.platform.value,
        "status": post.status.value,
        "scheduled_at": post.scheduled_at.isoformat() if post.scheduled_at else None,
    }


@router.get("/posts")
async def list_posts(
    profile_id: Optional[str] = None,
    platform: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500),
):
    """List social posts."""
    service = get_service()
    
    plat = None
    if platform:
        try:
            plat = SocialPlatform(platform)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid platform")
    
    stat = None
    if status:
        try:
            stat = PostStatus(status)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid status")
    
    posts = await service.list_posts(profile_id, plat, stat, limit)
    
    return {
        "posts": [
            {
                "id": p.id,
                "platform": p.platform.value,
                "post_type": p.post_type.value,
                "content": p.content[:100] + "..." if len(p.content) > 100 else p.content,
                "status": p.status.value,
                "likes_count": p.likes_count,
                "comments_count": p.comments_count,
                "views_count": p.views_count,
                "engagement_rate": p.engagement_rate,
                "published_at": p.published_at.isoformat() if p.published_at else None,
            }
            for p in posts
        ]
    }


@router.get("/posts/{post_id}")
async def get_post(post_id: str):
    """Get a post by ID."""
    service = get_service()
    post = await service.get_post(post_id)
    
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    return {
        "id": post.id,
        "profile_id": post.profile_id,
        "platform": post.platform.value,
        "post_type": post.post_type.value,
        "content": post.content,
        "status": post.status.value,
        "external_post_id": post.external_post_id,
        "external_url": post.external_url,
        "media_urls": post.media_urls,
        "hashtags": post.hashtags,
        "mentions": post.mentions,
        "likes_count": post.likes_count,
        "comments_count": post.comments_count,
        "shares_count": post.shares_count,
        "views_count": post.views_count,
        "clicks_count": post.clicks_count,
        "engagement_rate": post.engagement_rate,
        "scheduled_at": post.scheduled_at.isoformat() if post.scheduled_at else None,
        "published_at": post.published_at.isoformat() if post.published_at else None,
        "created_at": post.created_at.isoformat(),
    }


@router.post("/posts/{post_id}/publish")
async def publish_post(post_id: str):
    """Publish a post."""
    service = get_service()
    post = await service.publish_post(post_id)
    
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    return {
        "id": post.id,
        "status": post.status.value,
        "external_url": post.external_url,
        "published_at": post.published_at.isoformat() if post.published_at else None,
    }


@router.patch("/posts/{post_id}/metrics")
async def update_post_metrics(post_id: str, request: UpdateMetricsRequest):
    """Update post metrics."""
    service = get_service()
    
    post = await service.update_post_metrics(
        post_id=post_id,
        likes_count=request.likes_count,
        comments_count=request.comments_count,
        shares_count=request.shares_count,
        views_count=request.views_count,
        clicks_count=request.clicks_count,
    )
    
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    return {"success": True, "engagement_rate": post.engagement_rate}


@router.delete("/posts/{post_id}")
async def delete_post(post_id: str):
    """Delete a post."""
    service = get_service()
    
    if not await service.delete_post(post_id):
        raise HTTPException(status_code=404, detail="Post not found")
    
    return {"success": True}


# Interactions
@router.post("/interactions")
async def track_interaction(request: TrackInteractionRequest, user_id: Optional[str] = None):
    """Track a social interaction."""
    service = get_service()
    
    try:
        interaction_type = InteractionType(request.interaction_type)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid interaction type")
    
    interaction = await service.track_interaction(
        profile_id=request.profile_id,
        interaction_type=interaction_type,
        target_username=request.target_username,
        target_post_id=request.target_post_id,
        content=request.content,
        contact_id=request.contact_id,
        lead_id=request.lead_id,
        created_by=user_id,
    )
    
    if not interaction:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    return {
        "id": interaction.id,
        "interaction_type": interaction.interaction_type.value,
        "platform": interaction.platform.value,
    }


@router.get("/interactions")
async def list_interactions(
    profile_id: Optional[str] = None,
    interaction_type: Optional[str] = None,
    contact_id: Optional[str] = None,
    since: Optional[datetime] = None,
    limit: int = Query(100, ge=1, le=500),
):
    """List social interactions."""
    service = get_service()
    
    itype = None
    if interaction_type:
        try:
            itype = InteractionType(interaction_type)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid interaction type")
    
    interactions = await service.list_interactions(
        profile_id, itype, contact_id, since, limit
    )
    
    return {
        "interactions": [
            {
                "id": i.id,
                "platform": i.platform.value,
                "interaction_type": i.interaction_type.value,
                "target_username": i.target_username,
                "content": i.content,
                "contact_id": i.contact_id,
                "created_at": i.created_at.isoformat(),
            }
            for i in interactions
        ]
    }


# Campaigns
@router.post("/campaigns")
async def create_campaign(
    request: CreateCampaignRequest,
    org_id: str,
    user_id: Optional[str] = None,
):
    """Create a social selling campaign."""
    service = get_service()
    
    platforms = []
    for p in request.platforms:
        try:
            platforms.append(SocialPlatform(p))
        except ValueError:
            pass
    
    if not platforms:
        raise HTTPException(status_code=400, detail="At least one valid platform required")
    
    campaign = await service.create_campaign(
        name=request.name,
        org_id=org_id,
        platforms=platforms,
        description=request.description,
        start_date=request.start_date,
        end_date=request.end_date,
        goals=request.goals,
        created_by=user_id,
    )
    
    return {
        "id": campaign.id,
        "name": campaign.name,
        "status": campaign.status.value,
    }


@router.get("/campaigns")
async def list_campaigns(
    org_id: str,
    status: Optional[str] = None,
):
    """List campaigns."""
    service = get_service()
    
    stat = None
    if status:
        try:
            stat = CampaignStatus(status)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid status")
    
    campaigns = await service.list_campaigns(org_id, stat)
    
    return {
        "campaigns": [
            {
                "id": c.id,
                "name": c.name,
                "platforms": [p.value for p in c.platforms],
                "status": c.status.value,
                "posts_count": len(c.posts),
                "start_date": c.start_date.isoformat() if c.start_date else None,
                "end_date": c.end_date.isoformat() if c.end_date else None,
            }
            for c in campaigns
        ]
    }


@router.get("/campaigns/{campaign_id}")
async def get_campaign(campaign_id: str):
    """Get a campaign by ID."""
    service = get_service()
    campaign = await service.get_campaign(campaign_id)
    
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    return {
        "id": campaign.id,
        "name": campaign.name,
        "description": campaign.description,
        "platforms": [p.value for p in campaign.platforms],
        "status": campaign.status.value,
        "goals": campaign.goals,
        "posts": campaign.posts,
        "start_date": campaign.start_date.isoformat() if campaign.start_date else None,
        "end_date": campaign.end_date.isoformat() if campaign.end_date else None,
        "created_at": campaign.created_at.isoformat(),
    }


@router.patch("/campaigns/{campaign_id}/status")
async def update_campaign_status(campaign_id: str, status: str):
    """Update campaign status."""
    service = get_service()
    
    try:
        stat = CampaignStatus(status)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid status")
    
    campaign = await service.update_campaign_status(campaign_id, stat)
    
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    return {"success": True, "status": campaign.status.value}


@router.post("/campaigns/{campaign_id}/posts/{post_id}")
async def add_post_to_campaign(campaign_id: str, post_id: str):
    """Add a post to a campaign."""
    service = get_service()
    
    campaign = await service.add_post_to_campaign(campaign_id, post_id)
    
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    return {"success": True, "posts_count": len(campaign.posts)}


@router.get("/campaigns/{campaign_id}/analytics")
async def get_campaign_analytics(campaign_id: str):
    """Get campaign analytics."""
    service = get_service()
    analytics = await service.get_campaign_analytics(campaign_id)
    
    if not analytics:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    return analytics


# Social scores and leaderboard
@router.get("/score")
async def get_social_score(user_id: str, period: str = "monthly"):
    """Get social selling score for a user."""
    service = get_service()
    score = await service.calculate_social_score(user_id, period)
    
    return {
        "user_id": score.user_id,
        "score": score.score,
        "rank": score.rank,
        "posts_count": score.posts_count,
        "engagement_count": score.engagement_count,
        "connections_made": score.connections_made,
        "period": score.period,
    }


@router.get("/leaderboard")
async def get_leaderboard(
    org_id: str,
    limit: int = Query(10, ge=1, le=50),
):
    """Get social selling leaderboard."""
    service = get_service()
    return {"leaderboard": await service.get_leaderboard(org_id, limit)}


# Platform analytics
@router.get("/analytics/{platform}")
async def get_platform_analytics(
    platform: str,
    org_id: str,
    since: Optional[datetime] = None,
):
    """Get analytics for a platform."""
    service = get_service()
    
    try:
        plat = SocialPlatform(platform)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid platform")
    
    return await service.get_platform_analytics(org_id, plat, since)

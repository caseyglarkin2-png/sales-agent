"""
Social Selling Service
======================
Social selling, engagement tracking, and social media automation.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional
import uuid


class SocialPlatform(str, Enum):
    """Social platforms."""
    LINKEDIN = "linkedin"
    TWITTER = "twitter"
    FACEBOOK = "facebook"
    INSTAGRAM = "instagram"
    YOUTUBE = "youtube"
    TIKTOK = "tiktok"


class PostType(str, Enum):
    """Post types."""
    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"
    ARTICLE = "article"
    POLL = "poll"
    CAROUSEL = "carousel"
    STORY = "story"
    REEL = "reel"
    LIVE = "live"


class InteractionType(str, Enum):
    """Interaction types."""
    LIKE = "like"
    COMMENT = "comment"
    SHARE = "share"
    REPLY = "reply"
    REPOST = "repost"
    MENTION = "mention"
    TAG = "tag"
    FOLLOW = "follow"
    UNFOLLOW = "unfollow"
    MESSAGE = "message"
    CONNECTION_REQUEST = "connection_request"
    CONNECTION_ACCEPTED = "connection_accepted"
    PROFILE_VIEW = "profile_view"


class PostStatus(str, Enum):
    """Post status."""
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    PUBLISHED = "published"
    FAILED = "failed"
    DELETED = "deleted"


class CampaignStatus(str, Enum):
    """Campaign status."""
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"


@dataclass
class SocialProfile:
    """Social media profile."""
    id: str
    platform: SocialPlatform
    username: str
    profile_url: str
    user_id: str  # Internal user who owns this profile
    org_id: str
    display_name: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    followers_count: int = 0
    following_count: int = 0
    posts_count: int = 0
    is_connected: bool = True
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_expires_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class SocialPost:
    """Social media post."""
    id: str
    profile_id: str
    platform: SocialPlatform
    post_type: PostType
    content: str
    status: PostStatus = PostStatus.DRAFT
    external_post_id: Optional[str] = None
    external_url: Optional[str] = None
    media_urls: list[str] = field(default_factory=list)
    hashtags: list[str] = field(default_factory=list)
    mentions: list[str] = field(default_factory=list)
    scheduled_at: Optional[datetime] = None
    published_at: Optional[datetime] = None
    likes_count: int = 0
    comments_count: int = 0
    shares_count: int = 0
    views_count: int = 0
    clicks_count: int = 0
    engagement_rate: float = 0.0
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    created_by: Optional[str] = None


@dataclass
class SocialInteraction:
    """Social media interaction."""
    id: str
    profile_id: str
    platform: SocialPlatform
    interaction_type: InteractionType
    target_user_id: Optional[str] = None  # External social user
    target_username: Optional[str] = None
    target_post_id: Optional[str] = None
    content: Optional[str] = None
    external_id: Optional[str] = None
    contact_id: Optional[str] = None  # Linked CRM contact
    lead_id: Optional[str] = None  # Linked CRM lead
    created_at: datetime = field(default_factory=datetime.utcnow)
    created_by: Optional[str] = None


@dataclass
class SocialCampaign:
    """Social selling campaign."""
    id: str
    name: str
    description: Optional[str]
    org_id: str
    platforms: list[SocialPlatform]
    status: CampaignStatus = CampaignStatus.DRAFT
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    goals: dict[str, Any] = field(default_factory=dict)
    target_audience: dict[str, Any] = field(default_factory=dict)
    posts: list[str] = field(default_factory=list)  # Post IDs
    total_reach: int = 0
    total_engagement: int = 0
    total_clicks: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    created_by: Optional[str] = None


@dataclass
class SocialScore:
    """Social selling score."""
    user_id: str
    score: float
    rank: int
    posts_count: int
    engagement_count: int
    connections_made: int
    profile_views: int
    period: str  # "weekly", "monthly", "quarterly"
    calculated_at: datetime = field(default_factory=datetime.utcnow)


class SocialSellingService:
    """
    Social Selling service.
    
    Manages social media profiles, posts, interactions,
    and social selling campaigns.
    """
    
    def __init__(self):
        """Initialize social selling service."""
        self.profiles: dict[str, SocialProfile] = {}
        self.posts: dict[str, SocialPost] = {}
        self.interactions: dict[str, SocialInteraction] = {}
        self.campaigns: dict[str, SocialCampaign] = {}
        self.scores: dict[str, SocialScore] = {}
    
    # Profile management
    async def connect_profile(
        self,
        platform: SocialPlatform,
        username: str,
        profile_url: str,
        user_id: str,
        org_id: str,
        display_name: Optional[str] = None,
        access_token: Optional[str] = None,
        refresh_token: Optional[str] = None,
    ) -> SocialProfile:
        """Connect a social media profile."""
        profile = SocialProfile(
            id=str(uuid.uuid4()),
            platform=platform,
            username=username,
            profile_url=profile_url,
            user_id=user_id,
            org_id=org_id,
            display_name=display_name or username,
            access_token=access_token,
            refresh_token=refresh_token,
        )
        
        self.profiles[profile.id] = profile
        return profile
    
    async def get_profile(self, profile_id: str) -> Optional[SocialProfile]:
        """Get a profile by ID."""
        return self.profiles.get(profile_id)
    
    async def list_profiles(
        self,
        user_id: Optional[str] = None,
        org_id: Optional[str] = None,
        platform: Optional[SocialPlatform] = None,
    ) -> list[SocialProfile]:
        """List social profiles."""
        profiles = list(self.profiles.values())
        
        if user_id:
            profiles = [p for p in profiles if p.user_id == user_id]
        
        if org_id:
            profiles = [p for p in profiles if p.org_id == org_id]
        
        if platform:
            profiles = [p for p in profiles if p.platform == platform]
        
        return profiles
    
    async def disconnect_profile(self, profile_id: str) -> bool:
        """Disconnect a social profile."""
        if profile_id in self.profiles:
            del self.profiles[profile_id]
            return True
        return False
    
    async def update_profile_stats(
        self,
        profile_id: str,
        followers_count: Optional[int] = None,
        following_count: Optional[int] = None,
        posts_count: Optional[int] = None,
    ) -> Optional[SocialProfile]:
        """Update profile statistics."""
        profile = self.profiles.get(profile_id)
        if not profile:
            return None
        
        if followers_count is not None:
            profile.followers_count = followers_count
        if following_count is not None:
            profile.following_count = following_count
        if posts_count is not None:
            profile.posts_count = posts_count
        
        profile.updated_at = datetime.utcnow()
        return profile
    
    # Post management
    async def create_post(
        self,
        profile_id: str,
        post_type: PostType,
        content: str,
        media_urls: Optional[list[str]] = None,
        hashtags: Optional[list[str]] = None,
        mentions: Optional[list[str]] = None,
        scheduled_at: Optional[datetime] = None,
        created_by: Optional[str] = None,
    ) -> Optional[SocialPost]:
        """Create a social media post."""
        profile = self.profiles.get(profile_id)
        if not profile:
            return None
        
        status = PostStatus.SCHEDULED if scheduled_at else PostStatus.DRAFT
        
        post = SocialPost(
            id=str(uuid.uuid4()),
            profile_id=profile_id,
            platform=profile.platform,
            post_type=post_type,
            content=content,
            status=status,
            media_urls=media_urls or [],
            hashtags=hashtags or [],
            mentions=mentions or [],
            scheduled_at=scheduled_at,
            created_by=created_by,
        )
        
        self.posts[post.id] = post
        return post
    
    async def get_post(self, post_id: str) -> Optional[SocialPost]:
        """Get a post by ID."""
        return self.posts.get(post_id)
    
    async def list_posts(
        self,
        profile_id: Optional[str] = None,
        platform: Optional[SocialPlatform] = None,
        status: Optional[PostStatus] = None,
        limit: int = 100,
    ) -> list[SocialPost]:
        """List social posts."""
        posts = list(self.posts.values())
        
        if profile_id:
            posts = [p for p in posts if p.profile_id == profile_id]
        
        if platform:
            posts = [p for p in posts if p.platform == platform]
        
        if status:
            posts = [p for p in posts if p.status == status]
        
        posts.sort(key=lambda x: x.created_at, reverse=True)
        return posts[:limit]
    
    async def publish_post(self, post_id: str) -> Optional[SocialPost]:
        """Publish a post."""
        post = self.posts.get(post_id)
        if not post:
            return None
        
        # Simulate publishing (would call platform API in production)
        post.status = PostStatus.PUBLISHED
        post.published_at = datetime.utcnow()
        post.external_post_id = f"ext_{uuid.uuid4().hex[:12]}"
        post.external_url = f"https://{post.platform.value}.com/post/{post.external_post_id}"
        post.updated_at = datetime.utcnow()
        
        return post
    
    async def update_post_metrics(
        self,
        post_id: str,
        likes_count: Optional[int] = None,
        comments_count: Optional[int] = None,
        shares_count: Optional[int] = None,
        views_count: Optional[int] = None,
        clicks_count: Optional[int] = None,
    ) -> Optional[SocialPost]:
        """Update post metrics."""
        post = self.posts.get(post_id)
        if not post:
            return None
        
        if likes_count is not None:
            post.likes_count = likes_count
        if comments_count is not None:
            post.comments_count = comments_count
        if shares_count is not None:
            post.shares_count = shares_count
        if views_count is not None:
            post.views_count = views_count
        if clicks_count is not None:
            post.clicks_count = clicks_count
        
        # Calculate engagement rate
        total_engagement = post.likes_count + post.comments_count + post.shares_count
        if post.views_count > 0:
            post.engagement_rate = (total_engagement / post.views_count) * 100
        
        post.updated_at = datetime.utcnow()
        return post
    
    async def delete_post(self, post_id: str) -> bool:
        """Delete a post."""
        post = self.posts.get(post_id)
        if post:
            post.status = PostStatus.DELETED
            return True
        return False
    
    # Interaction tracking
    async def track_interaction(
        self,
        profile_id: str,
        interaction_type: InteractionType,
        target_username: Optional[str] = None,
        target_post_id: Optional[str] = None,
        content: Optional[str] = None,
        contact_id: Optional[str] = None,
        lead_id: Optional[str] = None,
        created_by: Optional[str] = None,
    ) -> Optional[SocialInteraction]:
        """Track a social interaction."""
        profile = self.profiles.get(profile_id)
        if not profile:
            return None
        
        interaction = SocialInteraction(
            id=str(uuid.uuid4()),
            profile_id=profile_id,
            platform=profile.platform,
            interaction_type=interaction_type,
            target_username=target_username,
            target_post_id=target_post_id,
            content=content,
            contact_id=contact_id,
            lead_id=lead_id,
            created_by=created_by,
        )
        
        self.interactions[interaction.id] = interaction
        return interaction
    
    async def list_interactions(
        self,
        profile_id: Optional[str] = None,
        interaction_type: Optional[InteractionType] = None,
        contact_id: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: int = 100,
    ) -> list[SocialInteraction]:
        """List social interactions."""
        interactions = list(self.interactions.values())
        
        if profile_id:
            interactions = [i for i in interactions if i.profile_id == profile_id]
        
        if interaction_type:
            interactions = [i for i in interactions if i.interaction_type == interaction_type]
        
        if contact_id:
            interactions = [i for i in interactions if i.contact_id == contact_id]
        
        if since:
            interactions = [i for i in interactions if i.created_at >= since]
        
        interactions.sort(key=lambda x: x.created_at, reverse=True)
        return interactions[:limit]
    
    # Campaign management
    async def create_campaign(
        self,
        name: str,
        org_id: str,
        platforms: list[SocialPlatform],
        description: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        goals: Optional[dict[str, Any]] = None,
        created_by: Optional[str] = None,
    ) -> SocialCampaign:
        """Create a social selling campaign."""
        campaign = SocialCampaign(
            id=str(uuid.uuid4()),
            name=name,
            description=description,
            org_id=org_id,
            platforms=platforms,
            start_date=start_date,
            end_date=end_date,
            goals=goals or {},
            created_by=created_by,
        )
        
        self.campaigns[campaign.id] = campaign
        return campaign
    
    async def get_campaign(self, campaign_id: str) -> Optional[SocialCampaign]:
        """Get a campaign by ID."""
        return self.campaigns.get(campaign_id)
    
    async def list_campaigns(
        self,
        org_id: str,
        status: Optional[CampaignStatus] = None,
    ) -> list[SocialCampaign]:
        """List campaigns."""
        campaigns = [c for c in self.campaigns.values() if c.org_id == org_id]
        
        if status:
            campaigns = [c for c in campaigns if c.status == status]
        
        return campaigns
    
    async def update_campaign_status(
        self,
        campaign_id: str,
        status: CampaignStatus,
    ) -> Optional[SocialCampaign]:
        """Update campaign status."""
        campaign = self.campaigns.get(campaign_id)
        if not campaign:
            return None
        
        campaign.status = status
        campaign.updated_at = datetime.utcnow()
        return campaign
    
    async def add_post_to_campaign(
        self,
        campaign_id: str,
        post_id: str,
    ) -> Optional[SocialCampaign]:
        """Add a post to a campaign."""
        campaign = self.campaigns.get(campaign_id)
        if not campaign:
            return None
        
        if post_id not in campaign.posts:
            campaign.posts.append(post_id)
            campaign.updated_at = datetime.utcnow()
        
        return campaign
    
    async def get_campaign_analytics(
        self,
        campaign_id: str,
    ) -> Optional[dict[str, Any]]:
        """Get campaign analytics."""
        campaign = self.campaigns.get(campaign_id)
        if not campaign:
            return None
        
        total_reach = 0
        total_engagement = 0
        total_clicks = 0
        posts_data = []
        
        for post_id in campaign.posts:
            post = self.posts.get(post_id)
            if post:
                total_reach += post.views_count
                total_engagement += post.likes_count + post.comments_count + post.shares_count
                total_clicks += post.clicks_count
                posts_data.append({
                    "id": post.id,
                    "platform": post.platform.value,
                    "engagement_rate": post.engagement_rate,
                    "views": post.views_count,
                })
        
        return {
            "campaign_id": campaign_id,
            "total_posts": len(campaign.posts),
            "total_reach": total_reach,
            "total_engagement": total_engagement,
            "total_clicks": total_clicks,
            "avg_engagement_rate": total_engagement / total_reach * 100 if total_reach > 0 else 0,
            "posts": posts_data,
        }
    
    # Social selling score
    async def calculate_social_score(
        self,
        user_id: str,
        period: str = "monthly",
    ) -> SocialScore:
        """Calculate social selling score for a user."""
        # Get user profiles
        profiles = [p for p in self.profiles.values() if p.user_id == user_id]
        profile_ids = [p.id for p in profiles]
        
        # Count posts
        posts_count = len([
            p for p in self.posts.values()
            if p.profile_id in profile_ids and p.status == PostStatus.PUBLISHED
        ])
        
        # Count engagement
        engagement_count = len([
            i for i in self.interactions.values()
            if i.profile_id in profile_ids
        ])
        
        # Count connections
        connections_made = len([
            i for i in self.interactions.values()
            if i.profile_id in profile_ids
            and i.interaction_type in [InteractionType.CONNECTION_REQUEST, InteractionType.FOLLOW]
        ])
        
        # Profile views
        profile_views = sum(p.followers_count for p in profiles)
        
        # Calculate score (simplified algorithm)
        score = (
            posts_count * 10 +
            engagement_count * 5 +
            connections_made * 15 +
            profile_views * 0.1
        )
        
        social_score = SocialScore(
            user_id=user_id,
            score=min(100, score / 10),  # Normalize to 0-100
            rank=1,  # Would calculate based on all users
            posts_count=posts_count,
            engagement_count=engagement_count,
            connections_made=connections_made,
            profile_views=profile_views,
            period=period,
        )
        
        self.scores[user_id] = social_score
        return social_score
    
    async def get_social_score(self, user_id: str) -> Optional[SocialScore]:
        """Get social score for a user."""
        return self.scores.get(user_id)
    
    async def get_leaderboard(
        self,
        org_id: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Get social selling leaderboard."""
        # Get all users in org
        user_ids = set(p.user_id for p in self.profiles.values() if p.org_id == org_id)
        
        # Calculate scores for all
        leaderboard = []
        for user_id in user_ids:
            score = await self.calculate_social_score(user_id)
            leaderboard.append({
                "user_id": user_id,
                "score": score.score,
                "posts_count": score.posts_count,
                "engagement_count": score.engagement_count,
            })
        
        # Sort by score
        leaderboard.sort(key=lambda x: x["score"], reverse=True)
        
        # Add ranks
        for i, entry in enumerate(leaderboard):
            entry["rank"] = i + 1
        
        return leaderboard[:limit]
    
    async def get_platform_analytics(
        self,
        org_id: str,
        platform: SocialPlatform,
        since: Optional[datetime] = None,
    ) -> dict[str, Any]:
        """Get analytics for a platform."""
        if since is None:
            since = datetime.utcnow() - timedelta(days=30)
        
        profiles = [
            p for p in self.profiles.values()
            if p.org_id == org_id and p.platform == platform
        ]
        profile_ids = [p.id for p in profiles]
        
        posts = [
            p for p in self.posts.values()
            if p.profile_id in profile_ids and p.created_at >= since
        ]
        
        interactions = [
            i for i in self.interactions.values()
            if i.profile_id in profile_ids and i.created_at >= since
        ]
        
        total_followers = sum(p.followers_count for p in profiles)
        total_views = sum(p.views_count for p in posts)
        total_engagement = sum(p.likes_count + p.comments_count + p.shares_count for p in posts)
        
        return {
            "platform": platform.value,
            "profiles_count": len(profiles),
            "total_followers": total_followers,
            "posts_count": len(posts),
            "total_views": total_views,
            "total_engagement": total_engagement,
            "interactions_count": len(interactions),
            "avg_engagement_rate": total_engagement / total_views * 100 if total_views > 0 else 0,
        }


# Singleton instance
_social_selling_service: Optional[SocialSellingService] = None


def get_social_selling_service() -> SocialSellingService:
    """Get or create social selling service singleton."""
    global _social_selling_service
    if _social_selling_service is None:
        _social_selling_service = SocialSellingService()
    return _social_selling_service

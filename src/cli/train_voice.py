#!/usr/bin/env python3
"""CLI tool for training voice profiles from videos and newsletters.

Usage:
    python -m src.cli.train_voice --videos <url1> <url2> <url3>
    python -m src.cli.train_voice --newsletters "freight marketer"
    python -m src.cli.train_voice --all
"""
import asyncio
import argparse
import sys
from typing import List

from src.logger import get_logger
from src.connectors.hubspot import create_hubspot_connector
from src.voice_trainer import create_trainer
from src.transcription import create_youtube_transcriber

logger = get_logger(__name__)


async def train_from_videos(video_urls: List[str], profile_name: str = "dude_whats_the_bid") -> None:
    """Train voice from YouTube videos."""
    print(f"\n🎥 Training voice from {len(video_urls)} YouTube videos...")
    print("=" * 60)
    
    try:
        # Create trainer and transcriber
        trainer = create_trainer()
        transcriber = create_youtube_transcriber()
        
        # Transcribe videos
        print("\n📝 Transcribing videos (this may take a minute)...")
        transcripts = await transcriber.transcribe_multiple(video_urls)
        
        if not transcripts:
            print("❌ Could not transcribe any videos.")
            print("   Make sure the videos have captions/subtitles enabled.")
            return
        
        print(f"✅ Transcribed {len(transcripts)} videos")
        
        # Add to training
        count = trainer.add_video_transcripts(transcripts)
        print(f"✅ Added {count} video transcripts to training")
        
        # Analyze and create profile
        print("\n🧠 Analyzing voice patterns...")
        analysis = await trainer.analyze_samples()
        
        print(f"\n📊 Analysis Results:")
        print(f"   Tone: {analysis.tone}")
        print(f"   Formality: {analysis.formality_level:.2f}")
        print(f"   Uses contractions: {analysis.uses_contractions}")
        print(f"   Uses questions: {analysis.uses_questions}")
        
        print("\n🎨 Creating voice profile...")
        profile = await trainer.create_profile_from_analysis(profile_name, analysis)
        
        print(f"✅ Created voice profile: {profile.name}")
        print(f"\n🎯 Profile saved as: {profile_name}")
        
    except Exception as e:
        logger.error(f"Error training from videos: {e}")
        print(f"❌ Error: {e}")
        sys.exit(1)


async def train_from_newsletters(search_query: str = "freight marketer", profile_name: str = "freight_marketer_voice") -> None:
    """Train voice from HubSpot newsletters."""
    print(f"\n📧 Training voice from HubSpot newsletters...")
    print(f"   Search query: '{search_query}'")
    print("=" * 60)
    
    try:
        # Create trainer with HubSpot connector
        hubspot = create_hubspot_connector()
        trainer = create_trainer(hubspot_connector=hubspot)
        
        # Fetch newsletters
        print("\n📥 Fetching newsletters from HubSpot...")
        samples = await trainer.fetch_hubspot_newsletters(search_query, limit=20)
        
        if not samples:
            print(f"❌ No newsletters found for '{search_query}'")
            return
        
        print(f"✅ Fetched {len(samples)} newsletters")
        
        # Add to training
        for sample in samples:
            trainer.add_sample(sample)
        
        # Analyze and create profile
        print("\n🧠 Analyzing voice patterns...")
        analysis = await trainer.analyze_samples()
        
        print(f"\n📊 Analysis Results:")
        print(f"   Tone: {analysis.tone}")
        print(f"   Formality: {analysis.formality_level:.2f}")
        print(f"   Common phrases: {', '.join(analysis.common_phrases[:3])}")
        
        print("\n🎨 Creating voice profile...")
        profile = await trainer.create_profile_from_analysis(profile_name, analysis)
        
        print(f"✅ Created voice profile: {profile.name}")
        print(f"\n🎯 Profile saved as: {profile_name}")
        
    except Exception as e:
        logger.error(f"Error training from newsletters: {e}")
        print(f"❌ Error: {e}")
        sys.exit(1)


async def train_all() -> None:
    """Train from both videos and newsletters."""
    print("\n🚀 Full Voice Training Pipeline")
    print("=" * 60)
    
    # Example "Dude, What's The Bid?!" videos
    dude_videos = [
        "https://www.youtube.com/watch?v=EXAMPLE1",  # Replace with actual video URLs
        "https://www.youtube.com/watch?v=EXAMPLE2",
        "https://www.youtube.com/watch?v=EXAMPLE3",
    ]
    
    print("\nStep 1: Training from 'Dude, What's The Bid?!' videos")
    await train_from_videos(dude_videos, "dude_whats_the_bid")
    
    print("\n" + "=" * 60)
    print("\nStep 2: Training from 'Freight Marketer' newsletters")
    await train_from_newsletters("freight marketer", "freight_marketer_voice")
    
    print("\n" + "=" * 60)
    print("\n✨ Training complete!")
    print("\nNext steps:")
    print("  1. Review profiles in the UI")
    print("  2. Queue up contacts for outreach")
    print("  3. Generate personalized emails using trained voices")


def main():
    """Main CLI entrypoint."""
    parser = argparse.ArgumentParser(
        description="Train voice profiles from videos and newsletters"
    )
    
    parser.add_argument(
        "--videos",
        nargs="+",
        help="YouTube video URLs to transcribe and train from"
    )
    
    parser.add_argument(
        "--newsletters",
        type=str,
        help="HubSpot newsletter search query"
    )
    
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run complete training pipeline (videos + newsletters)"
    )
    
    parser.add_argument(
        "--profile-name",
        type=str,
        default="custom_voice",
        help="Name for the voice profile"
    )
    
    args = parser.parse_args()
    
    if args.all:
        asyncio.run(train_all())
    elif args.videos:
        asyncio.run(train_from_videos(args.videos, args.profile_name))
    elif args.newsletters:
        asyncio.run(train_from_newsletters(args.newsletters, args.profile_name))
    else:
        parser.print_help()
        print("\nExample usage:")
        print("  python -m src.cli.train_voice --videos https://youtu.be/ABC123 https://youtu.be/XYZ789")
        print("  python -m src.cli.train_voice --newsletters 'freight marketer'")
        print("  python -m src.cli.train_voice --all")


if __name__ == "__main__":
    main()

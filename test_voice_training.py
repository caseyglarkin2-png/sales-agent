#!/usr/bin/env python3
"""Test voice training on provided YouTube videos."""
import asyncio
import httpx
import json

VIDEOS = [
    "https://www.youtube.com/live/QZj8AtRMloE?si=aIfjB-cS88PUtVXB",
    "https://www.youtube.com/live/QZj8AtRMloE?si=Yd8d5S1ahcXyBmYc",
    "https://www.youtube.com/live/1PvGYxntd6w?si=qsdOenYrXuPmM23X",
    "https://www.youtube.com/live/0sjRFXSR-Ig?si=z4snMr14BMLYX4v9",
    "https://www.youtube.com/live/Yra0Sfk8RB4?si=fzOxaUILqJYSMKAl",
    "https://www.youtube.com/live/Pzc4oy0SxjY?si=4KH7Vr1nUtxjviab",
    "https://www.youtube.com/live/4eaZAZVnMm0?si=WCEIi7k2OPTapuOW",
    "https://www.youtube.com/live/E8AYbnIV-Hc?si=H3krBUyH400ek9Mc",
    "https://www.youtube.com/live/W2lb2PuqMXY?si=4nNI3qZwhO2kwxin",
    "https://www.youtube.com/live/uHbBCclf4KU?si=uuAvzKRYtw9hCfsL",
    "https://www.youtube.com/live/Vvko7h9YcyQ?si=JkG3IdC8pwH_3FLn",
]

async def main():
    base_url = "http://localhost:8000"
    
    async with httpx.AsyncClient(timeout=300.0) as client:
        print("🎥 Training voice on 11 YouTube videos from 'Dude, What's The Bid?!'")
        print("=" * 70)
        
        # Train from videos
        print(f"\n📹 Submitting {len(VIDEOS)} videos for transcription...")
        try:
            response = await client.post(
                f"{base_url}/api/voice/training/youtube-videos",
                json={
                    "video_urls": VIDEOS,
                    "profile_name": "dude_whats_the_bid"
                }
            )
            response.raise_for_status()
            result = response.json()
            
            print(f"✅ Status: {result['status']}")
            print(f"✅ Videos processed: {result.get('videos_processed', 0)}")
            print(f"✅ Transcripts added: {result.get('transcripts_added', 0)}")
            print(f"✅ Total samples: {result.get('total_samples', 0)}")
            
            if result.get('transcripts_added', 0) > 0:
                # Create voice profile
                print(f"\n🎨 Creating voice profile 'dude_whats_the_bid'...")
                response = await client.post(
                    f"{base_url}/api/voice/training/create-profile",
                    params={"profile_name": "dude_whats_the_bid"}
                )
                response.raise_for_status()
                profile_result = response.json()
                
                print(f"✅ Profile created: {profile_result.get('profile_name')}")
                print(f"✅ Tone: {profile_result.get('tone')}")
                print(f"✅ Samples used: {profile_result.get('samples_used')}")
                
                # Get profile details
                print(f"\n📊 Profile details:")
                response = await client.get(
                    f"{base_url}/api/voice/profiles/dude_whats_the_bid"
                )
                if response.status_code == 200:
                    profile = response.json()
                    print(json.dumps(profile, indent=2))
                
                print("\n🎉 Voice training complete!")
                print(f"\nYou can now use 'dude_whats_the_bid' as the voice_profile for contacts")
            
        except httpx.HTTPStatusError as e:
            print(f"❌ HTTP Error: {e.response.status_code}")
            print(f"Response: {e.response.text}")
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())

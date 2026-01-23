"""
Test HubSpot Contact Sync Service
==================================

Example script demonstrating how to use the HubSpot sync service.

Usage:
    python test_hubspot_sync.py [--max-contacts 10] [--chainge-only]
"""

import asyncio
import logging
import argparse
from src.hubspot_sync import HubSpotContactSyncService, ContactSegment

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_full_sync(max_contacts: int = None):
    """Test syncing all contacts from HubSpot"""
    logger.info("=" * 60)
    logger.info("TEST: Full Contact Sync")
    logger.info("=" * 60)
    
    try:
        # Initialize sync service (uses HUBSPOT_API_KEY from environment)
        sync_service = HubSpotContactSyncService()
        
        # Run sync
        logger.info(f"Starting sync (max_contacts={max_contacts or 'unlimited'})...")
        stats = await sync_service.sync_all_contacts(
            batch_size=100,
            max_contacts=max_contacts
        )
        
        # Print results
        logger.info("\n" + "=" * 60)
        logger.info("SYNC RESULTS")
        logger.info("=" * 60)
        logger.info(f"Total synced: {stats.total_synced}")
        logger.info(f"Pages processed: {stats.total_pages}")
        logger.info(f"Errors: {stats.errors}")
        logger.info(f"Duration: {stats.duration_seconds:.2f}s")
        
        logger.info("\nSegment Distribution:")
        for segment, count in stats.by_segment.items():
            logger.info(f"  {segment}: {count}")
        
        # Get some sample contacts
        logger.info("\n" + "=" * 60)
        logger.info("SAMPLE CONTACTS")
        logger.info("=" * 60)
        
        result = sync_service.get_contacts(limit=5)
        for contact in result["contacts"]:
            logger.info(f"\n  {contact['email']}")
            logger.info(f"    Name: {contact.get('firstname')} {contact.get('lastname')}")
            logger.info(f"    Company: {contact.get('company')}")
            logger.info(f"    Segments: {contact.get('segments', [])}")
        
        await sync_service.close()
        
        return stats
        
    except Exception as e:
        logger.error(f"Sync failed: {e}", exc_info=True)
        raise


async def test_chainge_sync():
    """Test syncing CHAINge contacts specifically"""
    logger.info("=" * 60)
    logger.info("TEST: CHAINge List Sync")
    logger.info("=" * 60)
    
    try:
        sync_service = HubSpotContactSyncService()
        
        # Run CHAINge sync
        logger.info("Starting CHAINge sync...")
        stats = await sync_service.sync_chainge_list()
        
        # Print results
        logger.info("\n" + "=" * 60)
        logger.info("CHAINGE SYNC RESULTS")
        logger.info("=" * 60)
        logger.info(f"Total synced: {stats.total_synced}")
        logger.info(f"CHAINge contacts: {stats.by_segment.get(ContactSegment.CHAINGE, 0)}")
        logger.info(f"Duration: {stats.duration_seconds:.2f}s")
        
        # Get CHAINge contacts
        result = sync_service.get_contacts(segment=ContactSegment.CHAINGE)
        
        logger.info("\n" + "=" * 60)
        logger.info(f"CHAINGE CONTACTS ({result['total']})")
        logger.info("=" * 60)
        
        for contact in result["contacts"][:10]:  # Show first 10
            logger.info(f"\n  {contact['email']}")
            logger.info(f"    Name: {contact.get('firstname')} {contact.get('lastname')}")
            logger.info(f"    Company: {contact.get('company')}")
        
        await sync_service.close()
        
        return stats
        
    except Exception as e:
        logger.error(f"CHAINge sync failed: {e}", exc_info=True)
        raise


async def test_segment_filtering():
    """Test filtering contacts by segment"""
    logger.info("=" * 60)
    logger.info("TEST: Segment Filtering")
    logger.info("=" * 60)
    
    try:
        sync_service = HubSpotContactSyncService()
        
        # First sync all contacts
        await sync_service.sync_all_contacts(max_contacts=50)
        
        # Test each segment
        for segment in [ContactSegment.CHAINGE, ContactSegment.ENGAGED, 
                       ContactSegment.HIGH_VALUE, ContactSegment.COLD]:
            result = sync_service.get_contacts(segment=segment, limit=5)
            
            logger.info(f"\n{segment.upper()} segment: {result['total']} contacts")
            for contact in result["contacts"]:
                logger.info(f"  - {contact['email']} ({contact.get('company')})")
        
        await sync_service.close()
        
    except Exception as e:
        logger.error(f"Segment filtering test failed: {e}", exc_info=True)
        raise


async def main():
    """Main test runner"""
    parser = argparse.ArgumentParser(description="Test HubSpot Contact Sync")
    parser.add_argument(
        "--max-contacts",
        type=int,
        default=None,
        help="Maximum number of contacts to sync (default: unlimited)"
    )
    parser.add_argument(
        "--chainge-only",
        action="store_true",
        help="Only sync CHAINge contacts"
    )
    parser.add_argument(
        "--test-segments",
        action="store_true",
        help="Test segment filtering"
    )
    
    args = parser.parse_args()
    
    try:
        if args.chainge_only:
            await test_chainge_sync()
        elif args.test_segments:
            await test_segment_filtering()
        else:
            await test_full_sync(max_contacts=args.max_contacts)
        
        logger.info("\n" + "=" * 60)
        logger.info("✅ All tests passed!")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error("\n" + "=" * 60)
        logger.error("❌ Tests failed!")
        logger.error("=" * 60)
        raise


if __name__ == "__main__":
    asyncio.run(main())

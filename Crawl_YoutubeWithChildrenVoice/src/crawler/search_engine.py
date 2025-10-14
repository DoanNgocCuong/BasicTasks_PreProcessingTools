"""
Search Engine - Coordinate YouTube searches and video collection

This module orchestrates the search process across multiple queries,
manages rate limiting, and coordinates with the YouTube API client.
"""

import asyncio
import time
from typing import List, Dict, Set, Optional, Any
from datetime import datetime

from config import CrawlerConfig, YouTubeAPIConfig
from models import VideoMetadata, QueryStatistics
from crawler.youtube_api import YouTubeAPIClient, QuotaExceededError
from utils import get_output_manager, get_progress_tracker


class SearchEngine:
    """
    Orchestrates YouTube video searches and collection.

    Manages multiple queries, handles rate limiting, and coordinates
    with the YouTube API client for efficient video discovery.
    """

    def __init__(self, crawler_config: CrawlerConfig, youtube_config: YouTubeAPIConfig):
        """
        Initialize search engine.

        Args:
            crawler_config: Crawler configuration
            youtube_config: YouTube API configuration
        """
        self.crawler_config = crawler_config
        self.youtube_config = youtube_config

        self.output = get_output_manager()
        self.progress = get_progress_tracker()

        self.api_client = YouTubeAPIClient(youtube_config)

        # Search state
        self.collected_video_ids: Set[str] = set()
        self.query_statistics: List[QueryStatistics] = []

        self.output.debug("Initialized search engine")

    async def search_all_queries(self, queries: List[str]) -> List[VideoMetadata]:
        """
        Search for videos across all provided queries.

        Args:
            queries: List of search queries

        Returns:
            List of unique VideoMetadata objects
        """
        self.output.info(f"Starting search across {len(queries)} queries")

        all_videos = []
        total_queries = len(queries)

        with self.progress.create_progress_bar(
            total=total_queries,
            description="Searching queries",
            unit="query"
        ) as progress_bar:

            for i, query in enumerate(queries):
                try:
                    self.output.info(f"Processing query {i + 1}/{total_queries}: '{query}'")

                    # Search for videos
                    videos = await self._search_single_query(query)

                    # Filter duplicates
                    new_videos = [v for v in videos if v.video_id not in self.collected_video_ids]
                    for video in new_videos:
                        self.collected_video_ids.add(video.video_id)

                    all_videos.extend(new_videos)

                    # Record statistics
                    stats = QueryStatistics(
                        query=query,
                        videos_found=len(videos),
                        new_videos=len(new_videos),
                        total_videos_so_far=len(all_videos),
                        timestamp=datetime.now()
                    )
                    self.query_statistics.append(stats)

                    self.output.info(f"Query '{query}': {len(videos)} found, {len(new_videos)} new")

                    progress_bar.update(1)

                    # Rate limiting between queries
                    if i < total_queries - 1:
                        await asyncio.sleep(self.crawler_config.query_delay_seconds)

                except QuotaExceededError:
                    self.output.error(f"Quota exceeded during query '{query}' - stopping search")
                    break
                except Exception as e:
                    self.output.error(f"Failed to process query '{query}': {e}")
                    progress_bar.update(1)
                    continue

        # Final statistics
        self.output.success(f"Search completed: {len(all_videos)} unique videos collected")
        self._log_search_statistics()

        return all_videos

    async def _search_single_query(self, query: str) -> List[VideoMetadata]:
        """
        Search for videos using a single query.

        Args:
            query: Search query

        Returns:
            List of VideoMetadata objects
        """
        try:
            # Perform search
            videos = self.api_client.search_videos(
                query=query,
                max_results=self.crawler_config.max_videos_per_query
            )

            # Get detailed metadata for all videos
            if videos:
                video_ids = [v.video_id for v in videos]
                detailed_metadata = self.api_client.get_video_details(video_ids)

                # Update videos with detailed metadata
                for video in videos:
                    if video.video_id in detailed_metadata:
                        # Merge detailed metadata
                        detailed = detailed_metadata[video.video_id]
                        video.view_count = detailed.view_count
                        video.like_count = detailed.like_count
                        video.comment_count = detailed.comment_count
                        video.duration = detailed.duration
                        video.tags = detailed.tags

            return videos

        except QuotaExceededError:
            raise
        except Exception as e:
            self.output.error(f"Search failed for query '{query}': {e}")
            return []

    def _log_search_statistics(self) -> None:
        """Log comprehensive search statistics."""
        if not self.query_statistics:
            return

        total_queries = len(self.query_statistics)
        total_videos_found = sum(stats.videos_found for stats in self.query_statistics)
        total_new_videos = sum(stats.new_videos for stats in self.query_statistics)
        final_video_count = self.query_statistics[-1].total_videos_so_far if self.query_statistics else 0

        self.output.info("=== Search Statistics ===")
        self.output.info(f"Total queries processed: {total_queries}")
        self.output.info(f"Total videos found: {total_videos_found}")
        self.output.info(f"New unique videos: {total_new_videos}")
        self.output.info(f"Final video collection: {final_video_count}")

        # Query performance
        if self.query_statistics:
            avg_videos_per_query = total_videos_found / total_queries
            self.output.info(f"Average videos per query: {avg_videos_per_query:.1f}")

        # Top performing queries
        top_queries = sorted(
            self.query_statistics,
            key=lambda s: s.new_videos,
            reverse=True
        )[:5]

        if top_queries:
            self.output.info("Top 5 queries by new videos:")
            for i, stats in enumerate(top_queries, 1):
                self.output.info(f"  {i}. '{stats.query}': {stats.new_videos} new videos")

    def get_search_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive search summary.

        Returns:
            Dictionary with search statistics and metadata
        """
        quota_status = self.api_client.get_quota_status()

        return {
            "total_queries": len(self.query_statistics),
            "total_videos_found": sum(s.videos_found for s in self.query_statistics),
            "unique_videos_collected": len(self.collected_video_ids),
            "query_statistics": [s.to_dict() for s in self.query_statistics],
            "api_quota_status": quota_status,
            "search_completed": len(self.query_statistics) > 0
        }
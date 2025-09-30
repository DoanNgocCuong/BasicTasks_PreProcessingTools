#!/usr/bin/env python3
"""
TikTok Channel Discovery and Auto-Crawling Module

This module extends the main crawler to automatically discover and crawl entire channels
when qualified videos are found. It maintains a discovered channels database and can
automatically add promising channels to the crawler configuration.

Features:
    - Automatic channel discovery from qualified videos
    - Channel quality scoring based on children's voice video ratio
    - Auto-update crawler configuration with discovered channels
    - Channel statistics and reporting
    - Duplicate channel detection and management

Author: Extension for TikTok Children's Voice Crawler
Version: 1.0
"""

import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Set, Any, Tuple
from datetime import datetime
from dataclasses import dataclass
import threading

# Import the main crawler components
try:
    from tiktok_api_client import TikTokAPIClient
    from tiktok_audio_classifier import TikTokAudioClassifier
    from tiktok_video_downloader import TikTokVideoDownloader
    API_CLIENT_AVAILABLE = True
except ImportError:
    API_CLIENT_AVAILABLE = False
    print("❌ Failed to import TikTok modules")


@dataclass
class ChannelInfo:
    """Information about a discovered TikTok channel."""
    username: str
    nickname: str
    channel_id: str
    follower_count: int
    video_count: int
    discovered_from_video: str
    discovery_time: str
    qualified_videos: int = 0
    total_analyzed: int = 0
    quality_score: float = 0.0
    last_crawled: Optional[str] = None


class ChannelDiscovery:
    """Manages automatic channel discovery and crawling."""
    
    def __init__(self, output_manager=None):
        """Initialize channel discovery system."""
        self.output = output_manager
        
        # File paths
        self.discovered_channels_file = Path("discovered_channels.json")
        self.channel_stats_file = Path("channel_statistics.json")
        
        # Data storage
        self.discovered_channels: Dict[str, ChannelInfo] = {}
        self.channel_lock = threading.Lock()
        
        # Thresholds for auto-adding channels
        self.min_quality_score = 0.3  # 30% qualified video rate
        self.min_videos_analyzed = 5   # At least 5 videos analyzed
        
        # Load existing data
        self._load_discovered_channels()
        
        self._log("✅ Channel Discovery system initialized")
    
    def _log(self, message: str, level: str = "info") -> None:
        """Log message through output manager if available."""
        if self.output:
            if level == "error":
                self.output.print_error(message)
            elif level == "warning":
                self.output.print_warning(message)
            else:
                self.output.print_info(message)
        else:
            print(f"[{level.upper()}] {message}")
    
    def _load_discovered_channels(self) -> None:
        """Load discovered channels from file."""
        try:
            if self.discovered_channels_file.exists():
                with open(self.discovered_channels_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                for username, channel_data in data.items():
                    self.discovered_channels[username] = ChannelInfo(**channel_data)
                
                self._log(f"📂 Loaded {len(self.discovered_channels)} discovered channels")
            else:
                self._log("📂 No existing discovered channels file found")
                
        except Exception as e:
            self._log(f"⚠️ Error loading discovered channels: {e}", "warning")
    
    def _save_discovered_channels(self) -> None:
        """Save discovered channels to file."""
        try:
            with self.channel_lock:
                data = {}
                for username, channel_info in self.discovered_channels.items():
                    data[username] = {
                        'username': channel_info.username,
                        'nickname': channel_info.nickname,
                        'channel_id': channel_info.channel_id,
                        'follower_count': channel_info.follower_count,
                        'video_count': channel_info.video_count,
                        'discovered_from_video': channel_info.discovered_from_video,
                        'discovery_time': channel_info.discovery_time,
                        'qualified_videos': channel_info.qualified_videos,
                        'total_analyzed': channel_info.total_analyzed,
                        'quality_score': channel_info.quality_score,
                        'last_crawled': channel_info.last_crawled
                    }
                
                with open(self.discovered_channels_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                
                self._log(f"💾 Saved {len(self.discovered_channels)} discovered channels")
                
        except Exception as e:
            self._log(f"❌ Error saving discovered channels: {e}", "error")
    
    def discover_channel_from_video(self, video_info: Dict, is_qualified: bool) -> Optional[ChannelInfo]:
        """
        Discover and record channel information from a video.
        
        Args:
            video_info (Dict): Video information
            is_qualified (bool): Whether this video passed qualification criteria
            
        Returns:
            Optional[ChannelInfo]: Channel info if discovered/updated
        """
        try:
            username = video_info.get('author_username')
            if not username:
                return None
            
            with self.channel_lock:
                # Check if we already know this channel
                if username in self.discovered_channels:
                    channel = self.discovered_channels[username]
                    channel.total_analyzed += 1
                    if is_qualified:
                        channel.qualified_videos += 1
                    
                    # Update quality score
                    channel.quality_score = channel.qualified_videos / max(channel.total_analyzed, 1)
                    
                    self._log(f"📈 Updated channel stats: @{username} ({channel.quality_score:.2f} quality)")
                    
                else:
                    # New channel discovery
                    channel = ChannelInfo(
                        username=username,
                        nickname=video_info.get('author_nickname', username),
                        channel_id=video_info.get('channel_id', ''),
                        follower_count=0,  # Will be updated by get_channel_details
                        video_count=0,
                        discovered_from_video=video_info.get('url', ''),
                        discovery_time=datetime.now().isoformat(),
                        qualified_videos=1 if is_qualified else 0,
                        total_analyzed=1,
                        quality_score=1.0 if is_qualified else 0.0
                    )
                    
                    self.discovered_channels[username] = channel
                    self._log(f"🆕 Discovered new channel: @{username}")
                
                # Save changes
                self._save_discovered_channels()
                return channel
                
        except Exception as e:
            self._log(f"❌ Error discovering channel: {e}", "error")
            return None
    
    def get_channel_details(self, api_client: TikTokAPIClient, username: str) -> Optional[Dict]:
        """
        Get detailed channel information using API.
        
        Args:
            api_client (TikTokAPIClient): API client instance
            username (str): Channel username
            
        Returns:
            Optional[Dict]: Channel details or None if failed
        """
        try:
            user_info = api_client.get_user_info(username)
            if user_info:
                # Update our channel record with API data
                if username in self.discovered_channels:
                    channel = self.discovered_channels[username]
                    channel.follower_count = user_info.get('follower_count', 0)
                    channel.video_count = user_info.get('video_count', 0)
                    channel.nickname = user_info.get('nickname', channel.nickname)
                    self._save_discovered_channels()
                
                return user_info
            
        except Exception as e:
            self._log(f"⚠️ Error getting channel details for @{username}: {e}", "warning")
            return None
    
    def crawl_entire_channel(self, api_client: TikTokAPIClient, 
                           audio_classifier: TikTokAudioClassifier,
                           video_downloader: TikTokVideoDownloader,
                           username: str, max_videos: int = 100) -> Dict[str, Any]:
        """
        Crawl all videos from a specific channel.
        
        Args:
            api_client: TikTok API client
            audio_classifier: Audio classifier instance
            video_downloader: Video downloader instance
            username: Channel username to crawl
            max_videos: Maximum videos to analyze
            
        Returns:
            Dict[str, Any]: Crawling results and statistics
        """
        self._log(f"🎯 Starting full channel crawl: @{username}")
        start_time = time.time()
        
        results = {
            'username': username,
            'start_time': datetime.now().isoformat(),
            'videos_found': 0,
            'videos_analyzed': 0,
            'qualified_videos': 0,
            'vietnamese_videos': 0,
            'children_voice_videos': 0,
            'collected_urls': [],
            'crawl_duration': 0,
            'success': False
        }
        
        try:
            # Get channel videos
            videos = api_client.get_user_videos(username, count=max_videos)
            results['videos_found'] = len(videos)
            
            if not videos:
                self._log(f"⚠️ No videos found for @{username}", "warning")
                return results
            
            self._log(f"📹 Found {len(videos)} videos from @{username}")
            
            # Process each video
            for i, video in enumerate(videos, 1):
                try:
                    self._log(f"🔄 Processing video {i}/{len(videos)}: {video['title'][:50]}...")
                    
                    # Download and analyze
                    audio_path, duration = video_downloader.download_and_convert_audio(video, i)
                    if not audio_path:
                        continue
                    
                    # Analyze audio
                    analysis_result = audio_classifier.analyze_audio(audio_path)
                    results['videos_analyzed'] += 1
                    
                    # Check qualification criteria
                    if analysis_result.is_vietnamese:
                        results['vietnamese_videos'] += 1
                    
                    if analysis_result.has_children_voice:
                        results['children_voice_videos'] += 1
                    
                    # Qualified if both Vietnamese and children's voice
                    if analysis_result.is_vietnamese and analysis_result.has_children_voice:
                        results['qualified_videos'] += 1
                        results['collected_urls'].append(video['url'])
                        self._log(f"✅ Qualified video found: {video['title'][:50]}...")
                    
                    # Clean up
                    video_downloader.cleanup_audio_file(audio_path)
                    
                    # Update channel discovery record
                    is_qualified = analysis_result.is_vietnamese and analysis_result.has_children_voice
                    self.discover_channel_from_video(video, is_qualified)
                    
                except Exception as e:
                    self._log(f"⚠️ Error processing video {i}: {e}", "warning")
                    continue
            
            # Final results
            results['crawl_duration'] = time.time() - start_time
            results['success'] = True
            
            # Update channel record
            if username in self.discovered_channels:
                channel = self.discovered_channels[username]
                channel.last_crawled = datetime.now().isoformat()
                self._save_discovered_channels()
            
            self._log(f"✅ Channel crawl completed: @{username}")
            self._log(f"   📊 {results['qualified_videos']}/{results['videos_analyzed']} qualified videos")
            self._log(f"   ⏱️ Duration: {results['crawl_duration']:.1f}s")
            
            return results
            
        except Exception as e:
            self._log(f"❌ Channel crawl failed for @{username}: {e}", "error")
            results['error'] = str(e)
            return results
    
    def get_promising_channels(self) -> List[str]:
        """
        Get list of channels that should be added to crawler config.
        
        Returns:
            List[str]: Usernames of promising channels
        """
        promising = []
        
        for username, channel in self.discovered_channels.items():
            if (channel.total_analyzed >= self.min_videos_analyzed and 
                channel.quality_score >= self.min_quality_score):
                promising.append(username)
        
        return promising
    
    def auto_update_crawler_config(self, config_file: str = "crawler_config.json") -> bool:
        """
        Automatically update crawler configuration with discovered channels.
        
        Args:
            config_file: Path to crawler configuration file
            
        Returns:
            bool: True if updated successfully
        """
        try:
            config_path = Path(config_file)
            if not config_path.exists():
                self._log(f"⚠️ Config file not found: {config_file}", "warning")
                return False
            
            # Load current config
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # Get promising channels
            promising_channels = self.get_promising_channels()
            
            if not promising_channels:
                self._log("ℹ️ No promising channels found to add", "info")
                return True
            
            # Add to search queries if not already present
            current_queries = set(config.get('search_queries', []))
            new_queries = []
            
            for username in promising_channels:
                if username not in current_queries:
                    new_queries.append(username)
            
            if new_queries:
                config['search_queries'].extend(new_queries)
                
                # Save updated config
                with open(config_path, 'w', encoding='utf-8') as f:
                    json.dump(config, f, indent=2, ensure_ascii=False)
                
                self._log(f"✅ Added {len(new_queries)} promising channels to config:")
                for username in new_queries:
                    channel = self.discovered_channels[username]
                    self._log(f"   📈 @{username} (quality: {channel.quality_score:.2f})")
                
                return True
            else:
                self._log("ℹ️ All promising channels already in config", "info")
                return True
                
        except Exception as e:
            self._log(f"❌ Error updating crawler config: {e}", "error")
            return False
    
    def generate_channel_report(self) -> str:
        """Generate comprehensive channel discovery report."""
        report_lines = [
            "📊 TikTok Channel Discovery Report",
            "=" * 50,
            f"Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Total Discovered Channels: {len(self.discovered_channels)}",
            ""
        ]
        
        # Sort channels by quality score
        sorted_channels = sorted(
            self.discovered_channels.items(),
            key=lambda x: x[1].quality_score,
            reverse=True
        )
        
        # Top performing channels
        report_lines.extend([
            "🏆 Top Performing Channels:",
            "-" * 30
        ])
        
        for username, channel in sorted_channels[:10]:
            quality_indicator = "🌟" if channel.quality_score >= 0.5 else "⭐" if channel.quality_score >= 0.3 else "🔸"
            report_lines.append(
                f"{quality_indicator} @{username}: {channel.quality_score:.2f} "
                f"({channel.qualified_videos}/{channel.total_analyzed} videos)"
            )
        
        # Promising channels (auto-add candidates)
        promising = self.get_promising_channels()
        report_lines.extend([
            "",
            f"🎯 Promising Channels for Auto-Add ({len(promising)}):",
            "-" * 30
        ])
        
        for username in promising:
            channel = self.discovered_channels[username]
            report_lines.append(
                f"✅ @{username}: {channel.quality_score:.2f} quality, "
                f"{channel.follower_count:,} followers"
            )
        
        # Statistics
        total_analyzed = sum(c.total_analyzed for c in self.discovered_channels.values())
        total_qualified = sum(c.qualified_videos for c in self.discovered_channels.values())
        overall_quality = total_qualified / max(total_analyzed, 1)
        
        report_lines.extend([
            "",
            "📈 Overall Statistics:",
            "-" * 30,
            f"Total Videos Analyzed: {total_analyzed:,}",
            f"Total Qualified Videos: {total_qualified:,}",
            f"Overall Quality Score: {overall_quality:.2f}",
            f"Channels with 50%+ Quality: {sum(1 for c in self.discovered_channels.values() if c.quality_score >= 0.5)}",
            f"Channels Ready for Auto-Add: {len(promising)}"
        ])
        
        return "\n".join(report_lines)
    
    def print_channel_report(self) -> None:
        """Print channel discovery report."""
        report = self.generate_channel_report()
        print(report)
    
    def save_channel_report(self, filename: Optional[str] = None) -> str:
        """Save channel discovery report to file."""
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"channel_discovery_report_{timestamp}.txt"
        
        report = self.generate_channel_report()
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(report)
            
            self._log(f"📋 Channel report saved: {filename}")
            return filename
            
        except Exception as e:
            self._log(f"❌ Error saving channel report: {e}", "error")
            return ""


# Integration function for the main crawler
def integrate_channel_discovery(crawler_instance, discovery_instance):
    """
    Integrate channel discovery with the main crawler.
    
    Args:
        crawler_instance: Main TikTokVideoCollector instance
        discovery_instance: ChannelDiscovery instance
    """
    # Override the process_video method to include channel discovery
    original_process_video = crawler_instance.process_video
    
    def enhanced_process_video(video):
        # Call original processing
        is_collected = original_process_video(video)
        
        # Add channel discovery
        discovery_instance.discover_channel_from_video(video, is_collected)
        
        return is_collected
    
    crawler_instance.process_video = enhanced_process_video
    
    return crawler_instance


if __name__ == "__main__":
    print("🧪 Testing Channel Discovery System...")
    
    try:
        discovery = ChannelDiscovery()
        discovery.print_channel_report()
        
        print("\n✅ Channel Discovery test completed")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
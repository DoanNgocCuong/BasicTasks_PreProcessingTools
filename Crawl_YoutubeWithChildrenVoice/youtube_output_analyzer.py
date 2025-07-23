#!/usr/bin/env python3
"""
YouTube Output Analyzer and Reporting System

This module provides comprehensive analysis and reporting capabilities for YouTube video
collection results. It generates detailed statistics, performance metrics, and formatted
reports for collection campaigns targeting Vietnamese children's voice content.

Key Features:
    - Comprehensive final report generation with collection statistics
    - Per-query performance analysis and efficiency metrics
    - Runtime tracking and collection efficiency calculations
    - JSON-based detailed results with complete metadata
    - Backup file creation with timestamp-based naming
    - Query-specific statistics and comparative analysis
    - Multi-format output (text reports, JSON data, backup files)

Report Types:
    - Final Collection Report: Human-readable summary with key metrics
    - Detailed JSON Results: Complete dataset with metadata and statistics
    - Query Statistics: Per-query performance and efficiency analysis
    - Backup Files: Timestamped collection snapshots

Key Metrics:
    - Collection efficiency rates (videos collected vs. reviewed)
    - Children's voice detection rates
    - Vietnamese language detection rates
    - Channel discovery and exploration statistics
    - Runtime performance and speed metrics
    - Target achievement tracking

Data Classes:
    - QueryStatistics: Comprehensive per-query metrics and analysis
    - Structured data for consistent reporting and analysis

Analytics Capabilities:
    - Best/worst performing query identification
    - Collection efficiency optimization insights
    - Language detection accuracy tracking
    - Children's voice detection success rates
    - Channel exploration effectiveness metrics

Output Formats:
    - Text Reports: Human-readable formatted summaries
    - JSON Files: Machine-readable data with complete metadata
    - Statistical Analysis: Detailed performance breakdowns
    - Backup Collections: Timestamped URL collections

Integration:
    - Seamless integration with youtube_video_crawler
    - Compatible with collection workflow and statistics
    - Supports real-time and post-collection analysis
    - Extensible for additional metrics and reporting needs

Use Cases:
    - Collection campaign performance analysis
    - Quality assurance and process optimization
    - Research data compilation and reporting
    - Historical collection tracking and comparison
    - Dataset documentation and metadata management

Dependencies:
    - json: For structured data serialization
    - pathlib: For file system operations
    - datetime: For timestamp management
    - typing: For type annotations and validation

Usage:
    from youtube_output_analyzer import YouTubeOutputAnalyzer, QueryStatistics
    
    analyzer = YouTubeOutputAnalyzer(output_dir)
    report = analyzer.generate_final_report(...)
    analyzer.save_report_to_file(report, filename)

Author: Le Hoang Minh
Created: 2025
Version: 1.0
"""

import json
import time
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Union
from dataclasses import dataclass


@dataclass
class QueryStatistics:
    """Data class for query statistics."""
    query: str
    videos_collected: int
    videos_reviewed: int
    videos_evaluated: int
    videos_with_children_voice: int
    videos_vietnamese: int
    videos_not_vietnamese: int
    efficiency_rate: float
    children_voice_rate: float
    vietnamese_rate: float
    new_channels_found: int


class YouTubeOutputAnalyzer:
    """Handles analysis and reporting for YouTube video collection results."""
    
    def __init__(self, output_dir: Path):
        """Initialize the analyzer with output directory."""
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def format_duration(self, seconds: float) -> str:
        """
        Format duration in seconds to a readable string
        
        Args:
            seconds (float): Duration in seconds
            
        Returns:
            str: Formatted duration string
        """
        if seconds < 60:
            return f"{seconds:.2f} seconds"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            remaining_seconds = seconds % 60
            return f"{minutes}m {remaining_seconds:.1f}s"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            remaining_seconds = seconds % 60
            return f"{hours}h {minutes}m {remaining_seconds:.1f}s"
    
    def generate_final_report(self, 
                            current_session_collected_count: int,
                            total_video_urls: List[str],
                            total_target_count: int,
                            target_video_count_per_query: int,
                            total_videos_evaluated: int,
                            total_videos_with_children_voice: int,
                            total_videos_vietnamese: int,
                            total_videos_not_vietnamese: int,
                            query_list: List[str],
                            query_statistics: List[QueryStatistics],
                            reviewed_channels: List[str]) -> str:
        """Generate comprehensive final report."""
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        total_children_voice_rate = (total_videos_with_children_voice / total_videos_evaluated * 100) if total_videos_evaluated > 0 else 0
        total_vietnamese_rate = (total_videos_vietnamese / (total_videos_vietnamese + total_videos_not_vietnamese) * 100) if (total_videos_vietnamese + total_videos_not_vietnamese) > 0 else 0
        
        report = "=== FINAL COLLECTION REPORT FOR VIETNAMESE CHILDREN'S VOICE VIDEOS ===\n"
        report += f"Report generated: {current_time}\n\n"
        
        report += "=== OVERALL STATISTICS ===\n"
        report += f"Videos collected in current session: {current_session_collected_count}\n"
        report += f"Total videos in file (including existing): {len(total_video_urls)}\n"
        report += f"Total target count: {total_target_count}\n"
        report += f"Target per query: {target_video_count_per_query}\n"
        report += f"Target achievement: {(current_session_collected_count / total_target_count * 100):.2f}%\n"
        report += f"Total videos evaluated: {total_videos_evaluated}\n"
        report += f"Total videos with children's voice: {total_videos_with_children_voice}\n"
        report += f"Total videos in Vietnamese: {total_videos_vietnamese}\n"
        report += f"Total videos not in Vietnamese: {total_videos_not_vietnamese}\n"
        report += f"Overall children's voice rate: {total_children_voice_rate:.2f}%\n"
        report += f"Overall Vietnamese rate: {total_vietnamese_rate:.2f}%\n"
        report += f"Total queries processed: {len(query_list)}\n"
        report += f"Total channels reviewed: {len(reviewed_channels)}\n\n"
        
        report += "=== DETAILED STATISTICS BY QUERY ===\n"
        for stat in query_statistics:
            report += f"Query: \"{stat.query}\"\n"
            report += f"  - Videos collected: {stat.videos_collected}\n"
            report += f"  - Videos reviewed: {stat.videos_reviewed}\n"
            report += f"  - Videos evaluated: {stat.videos_evaluated}\n"
            report += f"  - Videos with children's voice: {stat.videos_with_children_voice}\n"
            report += f"  - Videos in Vietnamese: {stat.videos_vietnamese}\n"
            report += f"  - Videos not in Vietnamese: {stat.videos_not_vietnamese}\n"
            report += f"  - Efficiency rate: {stat.efficiency_rate:.2f}%\n"
            report += f"  - Children's voice rate: {stat.children_voice_rate:.2f}%\n"
            report += f"  - Vietnamese rate: {stat.vietnamese_rate:.2f}%\n"
            report += f"  - New channels found: {stat.new_channels_found}\n\n"
        
        # Find best and worst performing queries
        if query_statistics:
            best_efficiency = max(query_statistics, key=lambda x: x.efficiency_rate)
            worst_efficiency = min(query_statistics, key=lambda x: x.efficiency_rate)
            best_children_voice = max(query_statistics, key=lambda x: x.children_voice_rate)
            best_vietnamese = max(query_statistics, key=lambda x: x.vietnamese_rate)
            
            report += "=== QUERY PERFORMANCE ANALYSIS ===\n"
            report += f"Most efficient query: \"{best_efficiency.query}\" ({best_efficiency.efficiency_rate:.2f}%)\n"
            report += f"Least efficient query: \"{worst_efficiency.query}\" ({worst_efficiency.efficiency_rate:.2f}%)\n"
            report += f"Best children's voice rate: \"{best_children_voice.query}\" ({best_children_voice.children_voice_rate:.2f}%)\n"
            report += f"Best Vietnamese rate: \"{best_vietnamese.query}\" ({best_vietnamese.vietnamese_rate:.2f}%)\n\n"
            
            report += "=== RECOMMENDATIONS ===\n"
            report += f"- Prioritize using query: \"{best_efficiency.query}\" for high efficiency\n"
            report += f"- Consider improving or replacing query: \"{worst_efficiency.query}\"\n"
            report += f"- Query \"{best_children_voice.query}\" provides best quality results\n"
            report += f"- Query \"{best_vietnamese.query}\" has highest Vietnamese content rate\n"
            report += f"- Language detection helps improve collection accuracy\n\n"
        
        report += "=== END OF REPORT ===\n"
        return report
    
    def save_report_to_file(self, report_content: str, filename: str) -> None:
        """Save report to file."""
        try:
            filepath = Path(filename)
            filepath.parent.mkdir(parents=True, exist_ok=True)
            with filepath.open('w', encoding='utf-8') as f:
                f.write(report_content)
            print(f"✅ Report saved to: {filepath.resolve()}")
        except Exception as e:
            print(f"❌ Error saving report: {e}")
    
    def save_detailed_results_with_statistics(self, 
                                            filename: str,
                                            current_session_collected_count: int,
                                            total_video_urls: List[str],
                                            total_target_count: int,
                                            target_video_count_per_query: int,
                                            total_videos_evaluated: int,
                                            total_videos_with_children_voice: int,
                                            total_videos_vietnamese: int,
                                            total_videos_not_vietnamese: int,
                                            query_list: List[str],
                                            query_statistics: List[QueryStatistics],
                                            reviewed_channels: List[str],
                                            current_session_collected_urls: List[str],
                                            start_time: float,
                                            start_datetime: datetime) -> None:
        """Save detailed results with statistics to JSON file."""
        filepath = Path(filename)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        end_time = time.time()
        total_runtime = end_time - start_time
        
        # Convert QueryStatistics objects to dictionaries for JSON serialization
        query_stats_dicts = []
        for stat in query_statistics:
            query_stats_dicts.append({
                'query': stat.query,
                'videos_collected': stat.videos_collected,
                'videos_reviewed': stat.videos_reviewed,
                'videos_evaluated': stat.videos_evaluated,
                'videos_with_children_voice': stat.videos_with_children_voice,
                'videos_vietnamese': stat.videos_vietnamese,
                'videos_not_vietnamese': stat.videos_not_vietnamese,
                'efficiency_rate': stat.efficiency_rate,
                'children_voice_rate': stat.children_voice_rate,
                'vietnamese_rate': stat.vietnamese_rate,
                'new_channels_found': stat.new_channels_found
            })
        
        detailed_results = {
            'collection_summary': {
                'videos_collected_current_session': current_session_collected_count,
                'total_videos_in_file': len(total_video_urls),
                'total_target_count': total_target_count,
                'target_videos_per_query': target_video_count_per_query,
                'target_achievement_rate': f"{(current_session_collected_count / total_target_count * 100):.2f}%",
                'total_queries_processed': len(query_list),
                'reviewed_channels': len(reviewed_channels),
                'total_videos_evaluated': total_videos_evaluated,
                'total_videos_with_children_voice': total_videos_with_children_voice,
                'total_videos_vietnamese': total_videos_vietnamese,
                'total_videos_not_vietnamese': total_videos_not_vietnamese,
                'overall_children_voice_rate': f"{(total_videos_with_children_voice / max(total_videos_evaluated, 1) * 100):.2f}%",
                'overall_vietnamese_rate': f"{(total_videos_vietnamese / max(total_videos_vietnamese + total_videos_not_vietnamese, 1) * 100):.2f}%",
                'runtime_statistics': {
                    'start_time': start_datetime.isoformat(),
                    'end_time': datetime.now().isoformat(),
                    'total_runtime_seconds': round(total_runtime, 2),
                    'total_runtime_formatted': self.format_duration(total_runtime),
                    'collection_efficiency': f"{(current_session_collected_count / max(total_videos_evaluated, 1)) * 100:.1f}%" if total_videos_evaluated > 0 else "0%"
                }
            },
            'query_list': query_list,
            'query_statistics': query_stats_dicts,
            'reviewed_channels': reviewed_channels,
            'current_session_collected_urls': current_session_collected_urls,
            'all_video_urls_in_file': total_video_urls
        }
        
        with filepath.open('w', encoding='utf-8') as f:
            json.dump(detailed_results, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Detailed results saved to: {filepath.resolve()}")
    
    def save_statistics_to_file(self, 
                              filename: str,
                              query_statistics: List[QueryStatistics],
                              query_list: List[str],
                              target_video_count_per_query: int,
                              total_target_count: int,
                              current_session_collected_count: int,
                              total_video_urls: List[str],
                              total_videos_evaluated: int,
                              total_videos_with_children_voice: int) -> None:
        """Save query statistics to JSON file."""
        try:
            filepath = Path(filename)
            filepath.parent.mkdir(parents=True, exist_ok=True)
            
            # Convert QueryStatistics objects to dictionaries for JSON serialization
            query_stats_dicts = []
            for stat in query_statistics:
                query_stats_dicts.append({
                    'query': stat.query,
                    'videos_collected': stat.videos_collected,
                    'videos_reviewed': stat.videos_reviewed,
                    'videos_evaluated': stat.videos_evaluated,
                    'videos_with_children_voice': stat.videos_with_children_voice,
                    'videos_vietnamese': stat.videos_vietnamese,
                    'videos_not_vietnamese': stat.videos_not_vietnamese,
                    'efficiency_rate': stat.efficiency_rate,
                    'children_voice_rate': stat.children_voice_rate,
                    'vietnamese_rate': stat.vietnamese_rate,
                    'new_channels_found': stat.new_channels_found
                })
            
            statistics_data = {
                'collection_metadata': {
                    'collection_date': datetime.now().isoformat(),
                    'total_queries': len(query_list),
                    'target_per_query': target_video_count_per_query,
                    'total_target_count': total_target_count,
                    'videos_collected_current_session': current_session_collected_count,
                    'total_videos_in_file': len(total_video_urls),
                    'target_achievement_rate': f"{(current_session_collected_count / total_target_count * 100):.2f}%",
                    'total_videos_evaluated': total_videos_evaluated,
                    'total_videos_with_children_voice': total_videos_with_children_voice,
                    'overall_efficiency': f"{(current_session_collected_count / max(total_videos_evaluated, 1)) * 100:.2f}%"
                },
                'query_statistics': query_stats_dicts,
                'query_list': query_list
            }
            
            with filepath.open('w', encoding='utf-8') as f:
                json.dump(statistics_data, f, indent=2, ensure_ascii=False)
            
            print(f"✅ Statistics saved to: {filepath.resolve()}")
        except Exception as e:
            print(f"❌ Error saving statistics: {e}")
    
    def create_backup_file(self, total_video_urls: List[str]) -> None:
        """Create backup file with timestamp."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = self.output_dir / f"{timestamp}_backup_collected_videos.txt"
        
        try:
            with backup_filename.open('w', encoding='utf-8') as f:
                for url in total_video_urls:
                    f.write(url + '\n')
            print(f"✅ Backup created: {backup_filename}")
        except Exception as e:
            print(f"❌ Error creating backup: {e}")

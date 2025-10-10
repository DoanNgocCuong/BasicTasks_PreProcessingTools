#!/usr/bin/env python3
"""
YouTube Output Analyzer and Reporting System

This module provides comprehensive analysis and reporting capabilities for YouTube video
collection results. It generates detailed statistics, performance metrics, and formatted
reports for collection campaigns targeting Vietnamese children's voice content.

Author: Le Hoang Minh
"""

import json
import time
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Union, Any
from dataclasses import dataclass

# Import models from the new models package  
from models.analytics_models import QueryStatistics


class NumpyJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles numpy types."""
    
    def default(self, o):
        if isinstance(o, np.integer):
            return int(o)
        elif isinstance(o, np.floating):
            return float(o)
        elif isinstance(o, np.ndarray):
            return o.tolist()
        elif hasattr(o, 'item'):  # Handle numpy scalar types
            return o.item()
        return super(NumpyJSONEncoder, self).default(o)


def sanitize_for_json(obj: Any) -> Any:
    """Recursively sanitize data to ensure JSON compatibility."""
    if isinstance(obj, dict):
        return {key: sanitize_for_json(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [sanitize_for_json(item) for item in obj]
    elif isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif hasattr(obj, 'item'):  # Handle numpy scalar types
        return obj.item()
    else:
        return obj


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
                                            start_datetime: datetime,
                                            video_analysis_results: Optional[List[Dict]] = None) -> None:
        """Save detailed results with statistics to JSON file.
        
        Args:
            video_analysis_results: Optional list of individual video analysis results
                                  with timing information for each analyzed video
        """
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
        
        # Sanitize video analysis results to ensure JSON compatibility
        sanitized_video_analysis_results = []
        if video_analysis_results:
            sanitized_video_analysis_results = sanitize_for_json(video_analysis_results)
        
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
                },
                'video_analysis_timing_summary': self._calculate_timing_summary(video_analysis_results)
            },
            'query_list': query_list,
            'query_statistics': query_stats_dicts,
            'reviewed_channels': reviewed_channels,
            'current_session_collected_urls': current_session_collected_urls,
            'all_video_urls_in_file': total_video_urls,
            'video_analysis_results': sanitized_video_analysis_results
        }
        
        # Sanitize the entire detailed_results to ensure JSON compatibility
        sanitized_detailed_results = sanitize_for_json(detailed_results)
        
        with filepath.open('w', encoding='utf-8') as f:
            json.dump(sanitized_detailed_results, f, indent=2, ensure_ascii=False, cls=NumpyJSONEncoder)
        
        print(f"✅ Detailed results saved to: {filepath.resolve()}")
    
    def _calculate_timing_summary(self, video_analysis_results: Optional[List[Dict]]) -> Dict:
        """Calculate timing summary statistics from video analysis results."""
        if not video_analysis_results:
            return {
                'total_videos_analyzed': 0,
                'total_analysis_time': 0.0,
                'avg_analysis_time_per_video': 0.0,
                'total_children_detection_time': 0.0,
                'avg_children_detection_time': 0.0,
                'min_children_detection_time': 0.0,
                'max_children_detection_time': 0.0,
                'videos_with_timing_data': 0
            }
        
        # Filter videos with valid timing data
        videos_with_timing = [
            video for video in video_analysis_results 
            if video.get('total_analysis_time') is not None and video.get('children_detection_time') is not None
        ]
        
        # Filter videos with valid video length data
        videos_with_length = [
            video for video in video_analysis_results 
            if video.get('video_length_seconds') is not None and video.get('video_length_seconds', 0) > 0
        ]
        
        if not videos_with_timing:
            return {
                'total_videos_analyzed': len(video_analysis_results),
                'total_analysis_time': 0.0,
                'avg_analysis_time_per_video': 0.0,
                'total_children_detection_time': 0.0,
                'avg_children_detection_time': 0.0,
                'min_children_detection_time': 0.0,
                'max_children_detection_time': 0.0,
                'videos_with_timing_data': 0,
                'video_length_statistics': {
                    'videos_with_length_data': 0,
                    'total_video_length_seconds': 0.0,
                    'avg_video_length_seconds': 0.0,
                    'min_video_length_seconds': 0.0,
                    'max_video_length_seconds': 0.0,
                    'total_video_length_formatted': '0:00:00'
                }
            }
        
        # Calculate timing statistics
        total_analysis_time = sum(video.get('total_analysis_time', 0) for video in videos_with_timing)
        total_children_detection_time = sum(video.get('children_detection_time', 0) for video in videos_with_timing)
        children_detection_times = [video.get('children_detection_time', 0) for video in videos_with_timing if video.get('children_detection_time', 0) > 0]
        
        # Calculate video length statistics
        video_length_stats = {}
        if videos_with_length:
            video_lengths = [video.get('video_length_seconds', 0) for video in videos_with_length]
            total_video_length = sum(video_lengths)
            hours = int(total_video_length // 3600)
            minutes = int((total_video_length % 3600) // 60)
            seconds = int(total_video_length % 60)
            
            video_length_stats = {
                'videos_with_length_data': len(videos_with_length),
                'total_video_length_seconds': round(total_video_length, 2),
                'avg_video_length_seconds': round(total_video_length / len(videos_with_length), 2),
                'min_video_length_seconds': round(min(video_lengths), 2),
                'max_video_length_seconds': round(max(video_lengths), 2),
                'total_video_length_formatted': f'{hours}:{minutes:02d}:{seconds:02d}'
            }
        else:
            video_length_stats = {
                'videos_with_length_data': 0,
                'total_video_length_seconds': 0.0,
                'avg_video_length_seconds': 0.0,
                'min_video_length_seconds': 0.0,
                'max_video_length_seconds': 0.0,
                'total_video_length_formatted': '0:00:00'
            }
        
        return {
            'total_videos_analyzed': len(video_analysis_results),
            'videos_with_timing_data': len(videos_with_timing),
            'total_analysis_time': round(total_analysis_time, 2),
            'avg_analysis_time_per_video': round(total_analysis_time / len(videos_with_timing), 3),
            'total_children_detection_time': round(total_children_detection_time, 2),
            'avg_children_detection_time': round(total_children_detection_time / len(videos_with_timing), 3),
            'min_children_detection_time': round(min(children_detection_times), 3) if children_detection_times else 0.0,
            'max_children_detection_time': round(max(children_detection_times), 3) if children_detection_times else 0.0,
            'detection_efficiency_percentage': round((total_children_detection_time / total_analysis_time * 100), 1) if total_analysis_time > 0 else 0.0,
            'video_length_statistics': video_length_stats
        }
    
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
            
            # Sanitize all data to ensure JSON compatibility
            sanitized_statistics_data = sanitize_for_json(statistics_data)
            
            with filepath.open('w', encoding='utf-8') as f:
                json.dump(sanitized_statistics_data, f, indent=2, ensure_ascii=False, cls=NumpyJSONEncoder)
            
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

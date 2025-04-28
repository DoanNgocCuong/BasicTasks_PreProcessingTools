import logging
import argparse
import time
import sys
import os
import pandas as pd
from typing import List, Dict
from utils_readExcel import ExcelReader
from utils_saveExcel import TranscriptExcelSaver
from def_IDVideoYoutube2Transcript import YouTubeTranscriptFetcher

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

def process_video(video: Dict, transcript_fetcher: YouTubeTranscriptFetcher, 
                 transcript_saver: TranscriptExcelSaver, input_file: str) -> Dict:
    try:
        video_id = video['videoId']
        logger.info(f"=== Bắt đầu xử lý video: {video['title']} ({video_id}) ===")

        # Kiểm tra xem video đã có transcript chưa
        df = pd.read_excel(input_file)  # Đọc trực tiếp từ input file
        if 'transcript' in df.columns:
            mask = df['ID video'] == video_id
            if mask.any() and pd.notna(df.loc[mask, 'transcript']).any():
                logger.info(f"Video {video_id} đã có transcript, bỏ qua")
                return {
                    'video_id': video_id,
                    'status': 'skipped',
                    'message': 'Đã có transcript'
                }

        # Nếu chưa có transcript, tiến hành lấy từ API
        logger.info(f"Đang lấy transcript cho video {video_id}...")
        transcript_data = transcript_fetcher.get_transcript(video_id)
        if not transcript_data:
            logger.error(f"Không lấy được transcript cho video {video_id}")
            return {
                'video_id': video_id,
                'status': 'error',
                'message': 'Không thể lấy transcript'
            }
        logger.info(f"Đã lấy được transcript cho video {video_id}")

        # Lưu transcript vào Excel
        logger.info(f"Đang lưu transcript vào Excel cho video {video_id}...")
        excel_path = transcript_saver.save_transcript(transcript_data, video, input_file)
        if not excel_path:
            logger.error(f"Không lưu được transcript vào Excel cho video {video_id}")
            return {
                'video_id': video_id,
                'status': 'error',
                'message': 'Không thể lưu transcript vào Excel'
            }
        logger.info(f"Đã lưu transcript vào Excel cho video {video_id}")

        return {
            'video_id': video_id,
            'status': 'success',
            'excel_path': excel_path
        }

    except Exception as e:
        logger.exception(f"Lỗi khi xử lý video {video_id}: {str(e)}")
        return {
            'video_id': video_id,
            'status': 'error',
            'message': str(e)
        }

def main():
    parser = argparse.ArgumentParser(description='Lấy transcript cho danh sách video từ file Excel')
    parser.add_argument('--input', required=True, help='Đường dẫn đến file Excel chứa danh sách video')
    parser.add_argument('--delay', type=int, default=5, help='Thời gian delay giữa các request (giây)')
    parser.add_argument('--limit', type=int, help='Số lượng video muốn lấy (mặc định: tất cả)')
    args = parser.parse_args()

    # Khởi tạo các đối tượng
    excel_reader = ExcelReader()
    transcript_fetcher = YouTubeTranscriptFetcher()
    transcript_saver = TranscriptExcelSaver()

    # Đọc danh sách video từ Excel
    videos = excel_reader.read_videos_from_excel(args.input)
    if not videos:
        logger.error("Không thể đọc danh sách video từ file Excel")
        sys.exit(1)

    # Giới hạn số lượng video nếu có tham số limit
    if args.limit and args.limit > 0:
        videos = videos[:args.limit]
        logger.info(f"Giới hạn xử lý {args.limit} video đầu tiên")

    # Xử lý tuần tự các video
    results = []
    for idx, video in enumerate(videos):
        # Thêm delay giữa các request (trừ request đầu tiên)
        if idx > 0:
            logger.info(f"Đợi {args.delay} giây trước khi xử lý video tiếp theo...")
            time.sleep(args.delay)
            
        result = process_video(video, transcript_fetcher, transcript_saver, args.input)
        results.append(result)
        logger.info(f"Kết quả xử lý video {video['videoId']}: {result['status']}")
        logger.info("=" * 50)

    # In tổng kết
    success_count = sum(1 for r in results if r['status'] == 'success')
    skipped_count = sum(1 for r in results if r['status'] == 'skipped')
    logger.info(f"Đã xử lý xong {len(results)} video:")
    logger.info(f"- Thành công: {success_count}")
    logger.info(f"- Đã có sẵn: {skipped_count}")
    
    # In chi tiết các video lỗi
    failed_videos = [r for r in results if r['status'] == 'error']
    if failed_videos:
        logger.info("\nDanh sách video bị lỗi:")
        for failed in failed_videos:
            logger.info(f"- Video {failed['video_id']}: {failed['message']}")

if __name__ == "__main__":
    main()

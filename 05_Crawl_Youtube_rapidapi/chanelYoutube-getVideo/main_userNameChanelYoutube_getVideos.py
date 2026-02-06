import logging
import sys
from dotenv import load_dotenv
import argparse
import json
import os
from def_xtracrt_chanelID_fromUsername import YouTubeChannelExtractor
from def_chanelID_get_videos import YouTubeVideoFetcher
from utils_savelistVideos2Excel import ExcelExporter

# Tải biến môi trường từ file .env
load_dotenv()

# Thiết lập logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def main():
    """
    Hàm chính để chạy script.
    """
    parser = argparse.ArgumentParser(description='Lấy danh sách video từ một kênh YouTube.')
    parser.add_argument('--url', required=True, help='URL của kênh YouTube (có thể sử dụng Handle).')

    args = parser.parse_args()
    channel_url = args.url

    if not channel_url:
        logger.error("Thiếu URL của kênh YouTube.")
        sys.exit(1)

    # Trích xuất Channel ID
    channel_id = YouTubeChannelExtractor.extract_channel_id(channel_url)
    if not channel_id:
        logger.error("Không thể trích xuất Channel ID từ URL đã cung cấp.")
        sys.exit(1)

    logger.info(f"Channel ID: {channel_id}")

    # Khởi tạo video fetcher và lấy danh sách video
    video_fetcher = YouTubeVideoFetcher(os.getenv('RAPID_API_KEY'))
    videos = video_fetcher.get_channel_videos(channel_id)
    
    if not videos:
        logger.error("Không tìm thấy video nào cho kênh này.")
        sys.exit(1)

    # In kết quả dưới dạng JSON
    print(json.dumps({
        'videos': videos,
        'channel_id': channel_id,
        'video_count': len(videos)
    }, indent=4, ensure_ascii=False))

    # Sau khi lấy được danh sách video
    if videos:
        # Khởi tạo ExcelExporter
        excel_exporter = ExcelExporter()
        
        # Lưu danh sách video vào file Excel
        excel_file = excel_exporter.save_videos_to_excel(videos, channel_id)
        
        if excel_file:
            logger.info(f"Đã lưu danh sách video vào file: {excel_file}")
        else:
            logger.error("Không thể lưu danh sách video vào file Excel")

if __name__ == "__main__":
    main()

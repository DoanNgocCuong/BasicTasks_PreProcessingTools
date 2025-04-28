import pandas as pd
import logging
from typing import Dict

logger = logging.getLogger(__name__)

class TranscriptExcelSaver:
    """Class để lưu transcript vào file Excel."""

    def save_transcript(self, transcript_data: Dict, video_info: Dict, input_file: str) -> str:
        """
        Lưu transcript trực tiếp vào file input Excel.
        """
        try:
            # Đọc file input Excel
            df = pd.read_excel(input_file)
            logger.info(f"Đọc file input: {input_file}")
            
            # Tìm dòng của video cần cập nhật
            video_id = video_info['videoId']
            mask = df['ID video'] == video_id
            
            if mask.any():
                # Thêm cột transcript nếu chưa có
                if 'transcript' not in df.columns:
                    df['transcript'] = None
                    
                # Cập nhật transcript cho video
                df.loc[mask, 'transcript'] = transcript_data['transcript']
                
                # Lưu trực tiếp vào file input
                df.to_excel(input_file, index=False)
                logger.info(f"Đã lưu transcript cho video {video_id} vào {input_file}")
                
                return input_file
            else:
                logger.error(f"Không tìm thấy video {video_id} trong file Excel")
                return ""

        except Exception as e:
            logger.exception(f"Lỗi khi lưu transcript vào Excel: {str(e)}")
            return ""

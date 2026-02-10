import pandas as pd
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class ExcelReader:
    """Class để đọc dữ liệu từ file Excel."""

    @staticmethod
    def read_videos_from_excel(file_path: str) -> List[Dict]:
        """
        Đọc danh sách video từ file Excel.
        
        Args:
            file_path (str): Đường dẫn đến file Excel
            
        Returns:
            List[Dict]: Danh sách các video, mỗi video là một dict với các thông tin
        """
        try:
            df = pd.read_excel(file_path)
            logger.info(f"Đọc được {len(df)} dòng từ file Excel")
            
            videos = []
            for _, row in df.iterrows():
                video = {
                    'videoId': row['ID video'],
                    'title': row['Tiêu đề'],
                    'url': row['Đường dẫn video']
                }
                videos.append(video)
            
            return videos

        except Exception as e:
            logger.exception(f"Lỗi khi đọc file Excel: {str(e)}")
            return []

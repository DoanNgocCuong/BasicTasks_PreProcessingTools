import pandas as pd
import logging
from typing import List, Dict
from datetime import datetime
import os

logger = logging.getLogger(__name__)

class ExcelExporter:
    """Class để xử lý việc xuất danh sách video ra file Excel."""

    def __init__(self, output_dir: str = "output"):
        """
        Khởi tạo ExcelExporter với thư mục output.
        
        Args:
            output_dir (str): Đường dẫn đến thư mục output
        """
        self.output_dir = output_dir
        self._ensure_output_dir()

    def _ensure_output_dir(self) -> None:
        """Tạo thư mục output nếu chưa tồn tại."""
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            logger.info(f"Đã tạo thư mục output: {self.output_dir}")

    def _generate_filename(self, channel_id: str) -> str:
        """
        Tạo tên file Excel với format: videos_channelID_YYYYMMDD_HHMMSS.xlsx
        
        Args:
            channel_id (str): ID của kênh YouTube
            
        Returns:
            str: Tên file được tạo
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"videos_{channel_id}_{timestamp}.xlsx"

    def save_videos_to_excel(self, videos: List[Dict], channel_id: str) -> str:
        """
        Lưu danh sách video vào file Excel.
        
        Args:
            videos (List[Dict]): Danh sách các video
            channel_id (str): ID của kênh YouTube
            
        Returns:
            str: Đường dẫn đến file Excel đã tạo
        """
        try:
            if not videos:
                logger.error("Không có dữ liệu video để lưu")
                return ""

            # Tạo DataFrame từ danh sách video
            df = pd.DataFrame(videos)
            
            # Thêm cột STT
            df.insert(0, 'STT', range(1, len(df) + 1))
            
            # Đổi tên các cột sang tiếng Việt
            df = df.rename(columns={
                'url': 'Đường dẫn video',
                'title': 'Tiêu đề',
                'videoId': 'ID video'
            })

            # Tạo tên file và đường dẫn đầy đủ
            filename = self._generate_filename(channel_id)
            filepath = os.path.join(self.output_dir, filename)

            # Lưu vào file Excel
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Danh sách video', index=False)
                
                # Tự động điều chỉnh độ rộng cột
                worksheet = writer.sheets['Danh sách video']
                for idx, col in enumerate(df.columns):
                    max_length = max(
                        df[col].astype(str).apply(len).max(),
                        len(col)
                    )
                    worksheet.column_dimensions[chr(65 + idx)].width = max_length + 2

            logger.info(f"Đã lưu danh sách video vào file: {filepath}")
            return filepath

        except Exception as e:
            logger.exception(f"Lỗi khi lưu file Excel: {str(e)}")
            return ""

    def append_to_existing_excel(self, videos: List[Dict], filepath: str) -> bool:
        """
        Thêm danh sách video vào file Excel đã tồn tại.
        
        Args:
            videos (List[Dict]): Danh sách các video mới
            filepath (str): Đường dẫn đến file Excel cần thêm dữ liệu
            
        Returns:
            bool: True nếu thành công, False nếu thất bại
        """
        try:
            if not os.path.exists(filepath):
                logger.error(f"Kh��ng tìm thấy file: {filepath}")
                return False

            # Đọc dữ liệu hiện có
            existing_df = pd.read_excel(filepath)
            
            # Tạo DataFrame mới từ danh sách video
            new_df = pd.DataFrame(videos)
            
            # Gộp hai DataFrame
            combined_df = pd.concat([existing_df, new_df], ignore_index=True)
            
            # Cập nhật lại cột STT
            combined_df['STT'] = range(1, len(combined_df) + 1)

            # Lưu lại file Excel
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                combined_df.to_excel(writer, sheet_name='Danh sách video', index=False)
                
                # Tự động điều chỉnh độ rộng cột
                worksheet = writer.sheets['Danh sách video']
                for idx, col in enumerate(combined_df.columns):
                    max_length = max(
                        combined_df[col].astype(str).apply(len).max(),
                        len(col)
                    )
                    worksheet.column_dimensions[chr(65 + idx)].width = max_length + 2

            logger.info(f"Đã cập nhật thành công file: {filepath}")
            return True

        except Exception as e:
            logger.exception(f"Lỗi khi cập nhật file Excel: {str(e)}")
            return False

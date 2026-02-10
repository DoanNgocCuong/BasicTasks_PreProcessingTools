Tôi sẽ giúp bạn viết các file này. Hãy đi qua từng file:

1. Đầu tiên là `utils_readExcel.py`:

```python:Crawl_Youtube_rapidapi/idVideoYoutube2Transcription_RapidAPI/utils_readExcel.py
import pandas as pd
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class ExcelReader:
    """Class để đọc dữ liệu từ file Excel."""

    @staticmethod
    def read_videos_from_excel(filepath: str) -> List[Dict]:
        """
        Đọc danh sách video từ file Excel.
        
        Args:
            filepath (str): Đường dẫn đến file Excel
            
        Returns:
            List[Dict]: Danh sách các video với thông tin url và title
        """
        try:
            # Đọc file Excel
            df = pd.read_excel(filepath)
            
            # Kiểm tra các cột cần thiết
            required_columns = ['Đường dẫn video', 'Tiêu đề', 'ID video']
            if not all(col in df.columns for col in required_columns):
                logger.error("File Excel không có đủ các cột cần thiết")
                return []
            
            # Chuyển DataFrame thành list of dictionaries
            videos = []
            for _, row in df.iterrows():
                video = {
                    'url': row['Đường dẫn video'],
                    'title': row['Tiêu đề'],
                    'videoId': row['ID video']
                }
                videos.append(video)
            
            logger.info(f"Đã đọc thành công {len(videos)} video từ file Excel")
            return videos
            
        except Exception as e:
            logger.exception(f"Lỗi khi đọc file Excel: {str(e)}")
            return []
```

2. File `utils_saveExcel.py`:

```python:Crawl_Youtube_rapidapi/idVideoYoutube2Transcription_RapidAPI/utils_saveExcel.py
import pandas as pd
import logging
from datetime import datetime
import os
from typing import List, Dict

logger = logging.getLogger(__name__)

class TranscriptExcelSaver:
    """Class để lưu transcript vào file Excel."""

    def __init__(self, output_dir: str = "output"):
        """
        Khởi tạo TranscriptExcelSaver với thư mục output.
        
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

    def _generate_filename(self, video_id: str) -> str:
        """Tạo tên file Excel với timestamp."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"transcript_{video_id}_{timestamp}.xlsx"

    def save_transcript(self, transcript_data: Dict, video_info: Dict) -> str:
        """
        Lưu transcript vào file Excel.
        
        Args:
            transcript_data (Dict): Dữ liệu transcript
            video_info (Dict): Thông tin video
            
        Returns:
            str: Đường dẫn đến file Excel đã tạo
        """
        try:
            # Tạo DataFrame từ transcript
            df = pd.DataFrame(transcript_data['transcript'])
            
            # Thêm thông tin video
            metadata = pd.DataFrame([{
                'Video Title': video_info['title'],
                'Video URL': video_info['url'],
                'Video ID': video_info['videoId']
            }])

            # Tạo tên file và đường dẫn
            filename = self._generate_filename(video_info['videoId'])
            filepath = os.path.join(self.output_dir, filename)

            # Lưu vào Excel với nhiều sheet
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                metadata.to_excel(writer, sheet_name='Video Info', index=False)
                df.to_excel(writer, sheet_name='Transcript', index=False)
                
                # Tự động điều chỉnh độ rộng cột
                for sheet_name in writer.sheets:
                    worksheet = writer.sheets[sheet_name]
                    for idx, col in enumerate(df.columns):
                        max_length = max(
                            df[col].astype(str).apply(len).max(),
                            len(col)
                        )
                        worksheet.column_dimensions[chr(65 + idx)].width = max_length + 2

            logger.info(f"Đã lưu transcript vào file: {filepath}")
            return filepath

        except Exception as e:
            logger.exception(f"Lỗi khi lưu transcript vào Excel: {str(e)}")
            return ""
```

3. File `def_IDVideoYoutube2Transcript.py`:

```python:Crawl_Youtube_rapidapi/idVideoYoutube2Transcription_RapidAPI/def_IDVideoYoutube2Transcript.py
import requests
import logging
from typing import Dict, Optional
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class YouTubeTranscriptFetcher:
    """Class để lấy transcript từ video YouTube."""

    def __init__(self):
        self.api_key = os.getenv('RAPID_API_KEY')
        self.headers = {
            'X-RapidAPI-Key': self.api_key,
            'X-RapidAPI-Host': 'youtube-media-downloader.p.rapidapi.com'
        }

    def get_transcript(self, video_id: str) -> Optional[Dict]:
        """
        Lấy transcript cho một video YouTube.
        
        Args:
            video_id (str): ID của video YouTube
            
        Returns:
            Optional[Dict]: Transcript của video hoặc None nếu có lỗi
        """
        try:
            url = "https://youtube-media-downloader.p.rapidapi.com/v2/video/subtitles"
            params = {"videoId": video_id}

            logger.debug(f"Gọi API để lấy transcript cho video ID: {video_id}")
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()

            data = response.json()
            
            if not data.get("status"):
                logger.error(f"API trả về lỗi: {data.get('errorId', 'Unknown error')}")
                return None

            return {
                'transcript': data.get('subtitles', []),
                'status': 'success'
            }

        except requests.exceptions.RequestException as e:
            logger.exception(f"Lỗi khi lấy transcript: {str(e)}")
            return None
        except Exception as e:
            logger.exception(f"Lỗi không xác định: {str(e)}")
            return None
```

4. File `main_listVideosExcel_2_listTranscript.py`:

```python:Crawl_Youtube_rapidapi/idVideoYoutube2Transcription_RapidAPI/main_listVideosExcel_2_listTranscript.py
import logging
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict
import sys
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
                 transcript_saver: TranscriptExcelSaver) -> Dict:
    """
    Xử lý một video: lấy transcript và lưu vào Excel.
    """
    try:
        video_id = video['videoId']
        logger.info(f"Đang xử lý video: {video['title']} ({video_id})")

        # Lấy transcript
        transcript_data = transcript_fetcher.get_transcript(video_id)
        if not transcript_data:
            return {
                'video_id': video_id,
                'status': 'error',
                'message': 'Không thể lấy transcript'
            }

        # Lưu transcript vào Excel
        excel_path = transcript_saver.save_transcript(transcript_data, video)
        if not excel_path:
            return {
                'video_id': video_id,
                'status': 'error',
                'message': 'Không thể lưu transcript vào Excel'
            }

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
    parser.add_argument('--max-workers', type=int, default=5, help='Số luồng xử lý tối đa')
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

    # Xử lý song song các video
    results = []
    with ThreadPoolExecutor(max_workers=args.max_workers) as executor:
        future_to_video = {
            executor.submit(process_video, video, transcript_fetcher, transcript_saver): video 
            for video in videos
        }
        
        for future in as_completed(future_to_video):
            video = future_to_video[future]
            try:
                result = future.result()
                results.append(result)
                logger.info(f"Kết quả xử lý video {video['videoId']}: {result['status']}")
            except Exception as e:
                logger.exception(f"Lỗi khi xử lý video {video['videoId']}: {str(e)}")

    # In tổng kết
    success_count = sum(1 for r in results if r['status'] == 'success')
    logger.info(f"Đã xử lý xong {len(results)} video, thành công: {success_count}")

if __name__ == "__main__":
    main()
```

### Cách sử dụng:

1. Đảm bảo có file `.env` với API key:
```plaintext
RAPID_API_KEY=your_rapidapi_key_here
```

2. Cài đặt các thư viện cần thiết:
```bash
pip install pandas openpyxl requests python-dotenv
```

3. Chạy script:
```bash
python main_listVideosExcel_2_listTranscript.py --input path/to/your/videos.xlsx --max-workers 5
```

Script sẽ:
1. Đọc danh sách video từ file Excel
2. Lấy transcript cho mỗi video
3. Lưu transcript vào các file Excel riêng biệt trong thư mục output
4. Xử lý song song nhiều video cùng lúc
5. Hiển thị log chi tiết về quá trình xử lý



====


Tôi sẽ hướng dẫn bạn cách chạy chương trình để lấy transcript từ danh sách video trong file Excel:

1. **Đảm bảo cấu trúc thư mục**:
```
Crawl_Youtube_rapidapi/
├── idVideoYoutube2Transcription_RapidAPI/
│   ├── listMoxieVideosYoutube.xlsx
│   ├── main_listVideosExcel_2_listTranscript.py
│   ├── def_IDVideoYoutube2Transcript.py
│   ├── utils_readExcel.py
│   ├── utils_saveExcel.py
│   └── .env
```

2. **Tạo file `.env`** trong thư mục `idVideoYoutube2Transcription_RapidAPI`:
```plaintext
RAPID_API_KEY=your_rapidapi_key_here
```

3. **Cài đặt các thư viện cần thiết**:
```bash
pip install pandas openpyxl requests python-dotenv
```

4. **Chạy script**:
```bash
# Di chuyển vào thư mục chứa script
cd Crawl_Youtube_rapidapi/idVideoYoutube2Transcription_RapidAPI

# Chạy script với đường dẫn đến file Excel
python main_listVideosExcel_2_listTranscript.py --input listMoxieVideosYoutube.xlsx
```

Hoặc nếu muốn chỉ định số luồng xử lý:
```bash
python main_listVideosExcel_2_listTranscript.py --input listMoxieVideosYoutube.xlsx --max-workers 3
```

5. **Kết quả**:
- Script sẽ tạo một thư mục `output` (nếu chưa tồn tại)
- Mỗi video sẽ có một file Excel riêng trong thư mục `output` với format: `transcript_[video_id]_[timestamp].xlsx`
- Mỗi file Excel sẽ có 2 sheet:
  - `Video Info`: Thông tin về video
  - `Transcript`: Nội dung transcript của video

6. **Theo dõi tiến trình**:
- Script sẽ hiển thị log cho mỗi video đang được xử lý
- Cuối cùng sẽ hiển thị tổng kết số video đã xử lý thành công

7. **Xử lý lỗi thường gặp**:
- Nếu gặp lỗi "API key invalid": Kiểm tra lại API key trong file `.env`
- Nếu gặp lỗi "File not found": Kiểm tra đường dẫn file Excel
- Nếu gặp lỗi "Missing required columns": Kiểm tra file Excel có đủ các cột cần thiết không

8. **Cấu trúc file Excel đầu vào** phải có các cột:
- `Đường dẫn video`
- `Tiêu đề`
- `ID video`

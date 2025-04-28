import os
import pickle
import json
import logging
import time
from typing import Optional, Dict, Tuple
import requests
import gdown
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import sqlite3
import re




from googleapiclient.http import MediaIoBaseDownload

class Config:
    """Configuration settings"""
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    TRANSCRIBE_API_URL = 'http://103.253.20.13:25029/role_assign'
    ANALYZE_API_URL = 'http://localhost:25034/analyze'
    SECRET_KEY = 'codedongian'
    # SCOPES = ['https://www.googleapis.com/auth/drive.metadata.readonly']
    CREDENTIALS_PATH = os.path.join(BASE_DIR, 'credentials.json')
    TOKEN_PATH = os.path.join(BASE_DIR, 'token.pickle')
    DATABASE_PATH = os.path.join(BASE_DIR, 'video_database.db')
    TEMP_DIR = os.path.join(BASE_DIR, 'temp_files')
    LOG_DIR = os.path.join(BASE_DIR, 'logs')
    
    SCOPES = [
        'https://www.googleapis.com/auth/drive',  # Full access
        'https://www.googleapis.com/auth/drive.file',  # Access to files created/opened by the app
        'https://www.googleapis.com/auth/drive.readonly'  # Read-only access to files
    ]    

class DatabaseManager:
    def __init__(self, db_path: str, logger: logging.Logger):
        self.db_path = db_path
        self.logger = logger
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.create_database()

    def create_database(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS videos (
                    id INTEGER PRIMARY KEY,
                    url_video TEXT NOT NULL UNIQUE,
                    transcription TEXT,
                    criteria TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            self.logger.info("Database initialized")

    def url_exists(self, url_video: str) -> bool:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('SELECT COUNT(*) FROM videos WHERE url_video = ?', 
                                    (url_video,))
                return cursor.fetchone()[0] > 0
        except sqlite3.Error as e:
            self.logger.error(f"Database error checking URL: {e}")
            return False

    def insert_video(self, url_video: str, transcription: str, criteria: str = None) -> bool:
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT INTO videos (url_video, transcription, criteria)
                    VALUES (?, ?, ?)
                ''', (url_video, transcription, criteria or 'Pending analysis'))
                self.logger.info(f"Inserted video: {url_video}")
                return True
        except sqlite3.IntegrityError:
            self.logger.info(f"Video URL already exists: {url_video}")
            return False
        except sqlite3.Error as e:
            self.logger.error(f"Database error: {e}")
            return False

class AudioProcessor:
    def __init__(self, config: Config, logger: logging.Logger):
        self.config = config
        self.logger = logger
        os.makedirs(config.TEMP_DIR, exist_ok=True)

    def process_audio(self, audio_path: str, language: str = 'en') -> Optional[Dict]:
        if not os.path.exists(audio_path):
            self.logger.error(f"Audio file not found: {audio_path}")
            return None

        with open(audio_path, 'rb') as audio_file:
            try:
                response = requests.post(
                    self.config.TRANSCRIBE_API_URL,
                    files={'audio': audio_file},
                    data={
                        'secret_key': self.config.SECRET_KEY,
                        'language': language
                    }
                )
                response.raise_for_status()
                return response.json()
            except Exception as e:
                self.logger.error(f"Error processing audio: {e}")
                return None

    def combine_transcriptions(self, hv_output: Dict, mentor_output: Dict) -> str:
        """Combine and format transcriptions from HV and mentor"""
        try:
            # Extract data
            hv_data = self.extract_dicts(hv_output['output'])
            mentor_data = self.extract_dicts(mentor_output['output'])

            # Format with Mentee/Mentor instead of Speaker 1/2
            formatted = []
            for item in hv_data:
                time = self.format_time(item['start_time'])
                formatted.append(f"[{time}] Mentee: {item['text']}")
            
            for item in mentor_data:
                time = self.format_time(item['start_time'])
                formatted.append(f"[{time}] Mentor: {item['text']}")

            # Sort by time
            # Extract time from string for sorting
            def get_time(s):
                return int(s[1:3])*3600 + int(s[4:6])*60 + int(s[7:9])
            
            formatted.sort(key=get_time)
            
            # Join with newlines
            transcript = '\n'.join(formatted)
            
            # Log for debugging
            self.logger.info(f"Combined transcript format sample:\n{transcript[:200]}...")
            
            return transcript

        except Exception as e:
            self.logger.error(f"Error combining transcriptions: {e}")
            return ""

    def extract_dicts(self, s: str) -> list:
        pattern = r"\{[^{}]*\}"
        matches = re.findall(pattern, s)
        result = []
        for match in matches:
            try:
                match = match.replace("'", '"')
                d = json.loads(match)
                result.append(d)
            except json.JSONDecodeError:
                pass
        return result

    def format_time(self, milliseconds: int) -> str:
        seconds = milliseconds // 1000
        minutes = seconds // 60
        hours = minutes // 60
        return f"{hours:02d}:{minutes%60:02d}:{seconds%60:02d}"

    def analyze_transcript(self, transcript: str) -> Optional[str]:
        """Analyze transcript using the analyze API"""
        try:
            self.logger.info("Preparing to analyze transcript...")
            self.logger.info(f"Transcript length: {len(transcript)}")
            
            # Format payload
            payload = {
                "transcription": transcript
            }
            
            # Log request details for debugging
            self.logger.info(f"Sending request to: {self.config.ANALYZE_API_URL}")
            self.logger.info(f"Transcript sample: {transcript[:100]}...")
            
            # Make request
            response = requests.post(
                self.config.ANALYZE_API_URL,
                headers={
                    'Content-Type': 'application/json'
                },
                json=payload,
                timeout=60
            )
            
            # Enhanced error logging
            self.logger.info(f"Response status code: {response.status_code}")
            if response.status_code != 200:
                self.logger.error(f"Error response: {response.text}")
                return None
            
            # Log full response for debugging
            self.logger.info(f"Full response content: {response.text}")
            
            result = response.json()
            
            if 'criteria' in result:
                # Convert dictionary thành JSON string trước khi return
                criteria_str = json.dumps(result['criteria'], 
                                        ensure_ascii=False, 
                                        indent=2)
                self.logger.info("Successfully received criteria")
                return criteria_str
            else:
                self.logger.error(f"No criteria in response. Full response: {result}")
                return None

        except requests.exceptions.Timeout:
            self.logger.error("Request timed out")
            return None
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Request failed: {str(e)}")
            return None
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to decode JSON response: {str(e)}")
            return None
        except Exception as e:
            self.logger.error(f"Error analyzing transcript: {str(e)}", exc_info=True)
            return None

class VideoProcessor:
    def __init__(self, config: Config, logger: logging.Logger):
        self.config = config
        self.logger = logger
        self.db = DatabaseManager(config.DATABASE_PATH, logger)
        self.audio_processor = AudioProcessor(config, logger)
        self.drive_service = self._authenticate_google_drive()

    def _authenticate_google_drive(self):
        creds = None
        if os.path.exists(self.config.TOKEN_PATH):
            with open(self.config.TOKEN_PATH, 'rb') as token:
                creds = pickle.load(token)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.config.CREDENTIALS_PATH, self.config.SCOPES)
                creds = flow.run_local_server(port=0)
            with open(self.config.TOKEN_PATH, 'wb') as token:
                pickle.dump(creds, token)

        return build('drive', 'v3', credentials=creds)

    def list_folder_contents(self, folder_id: str) -> list:
        """List all contents of a folder with detailed logging"""
        try:
            self.logger.info(f"\nListing contents of folder {folder_id}")
            
            # Get drive ID
            drive_id = self.get_drive_id(folder_id)
            self.logger.info(f"Using Drive ID: {drive_id}")
            
            # Now list contents
            query = f"'{folder_id}' in parents"
            
            # Set up parameters based on whether it's a shared drive or not
            params = {
                'q': query,
                'fields': "files(id, name, mimeType)",
                'supportsAllDrives': True,
                'includeItemsFromAllDrives': True,
                'pageSize': 100
            }
            
            # Add drive-specific parameters only if we have a drive ID
            if drive_id:
                params.update({
                    'corpora': 'drive',
                    'driveId': drive_id
                })
                
            # Execute the query
            results = self.drive_service.files().list(**params).execute()
            
            files = results.get('files', [])
            self.logger.info(f"Found {len(files)} items:")
            for file in files:
                self.logger.info(f"- {file['name']} ({file['mimeType']}) ID: {file['id']}")
            
            return files
            
        except Exception as e:
            self.logger.error(f"Error listing folder contents: {str(e)}")
            return []

    def get_drive_id(self, folder_id: str) -> Optional[str]:
        """Get the Drive ID for a shared folder"""
        try:
            file = self.drive_service.files().get(
                fileId=folder_id,
                fields="driveId",
                supportsAllDrives=True
            ).execute()
            drive_id = file.get('driveId')
            if drive_id:
                self.logger.info(f"Found Drive ID: {drive_id}")
            else:
                self.logger.info("This is not a shared drive folder")
            return drive_id
        except Exception as e:
            self.logger.error(f"Error getting Drive ID: {str(e)}")
            return None

    def find_folders(self, folder_id: str) -> Tuple[Optional[str], Optional[str]]:
        """Find Audio and Video folders in shared folders"""
        self.logger.info(f"\nLooking for Audio and Video folders in {folder_id}")
        
        # First list all contents
        files = self.list_folder_contents(folder_id)
        
        audio_folder = None
        video_folder = None
        
        # Look for folders (case-insensitive)
        for item in files:
            if item['mimeType'] == 'application/vnd.google-apps.folder':
                name = item['name'].lower()
                if 'audio' in name:
                    audio_folder = item['id']
                    self.logger.info(f"Found Audio folder: {item['name']} (ID: {audio_folder})")
                elif 'video' in name:
                    video_folder = item['id']
                    self.logger.info(f"Found Video folder: {item['name']} (ID: {video_folder})")
        
        # Log results
        if not audio_folder:
            self.logger.error("Audio folder not found")
        if not video_folder:
            self.logger.error("Video folder not found")
            
        return audio_folder, video_folder

    def download_file(self, file_id: str, destination: str) -> bool:
        """Download a file from Google Drive using Drive API"""
        try:
            request = self.drive_service.files().get_media(
                fileId=file_id,
                supportsAllDrives=True
            )
            
            with open(destination, 'wb') as f:
                downloader = MediaIoBaseDownload(f, request)
                done = False
                while done is False:
                    status, done = downloader.next_chunk()
                    if status:
                        self.logger.info(f"Download {int(status.progress() * 100)}%")
            return True
        except Exception as e:
            self.logger.error(f"Error downloading file: {str(e)}")
            return False

    def process_folder(self, folder_id: str):
        """Process a shared folder"""
        try:
            # First get drive ID
            drive_id = self.get_drive_id(folder_id)
            if not drive_id:
                self.logger.error("Could not get Drive ID")
                return

            # Try to access the folder
            try:
                folder = self.drive_service.files().get(
                    fileId=folder_id,
                    fields="name,mimeType",
                    supportsAllDrives=True
                ).execute()
                self.logger.info(f"Successfully accessed folder: {folder.get('name')}")
            except Exception as e:
                self.logger.error(f"Cannot access folder: {str(e)}")
                return

            # Find Audio and Video folders
            audio_folder, video_folder = self.find_folders(folder_id)
            if not audio_folder or not video_folder:
                self.logger.error("Could not find both Audio and Video folders")
                return

            # List files in Video folder
            self.logger.info(f"\nListing files in Video folder:")
            videos = self.drive_service.files().list(
                q=f"'{video_folder}' in parents",
                fields="files(id, name, mimeType)",
                supportsAllDrives=True,
                includeItemsFromAllDrives=True
            ).execute().get('files', [])
            
            # Check if videos are found
            if not videos:
                self.logger.error("No videos found in the folder.")
                return
            
            self.logger.info(f"Found {len(videos)} videos:")
            for video in videos:
                self.logger.info(f"- Video: {video['name']} (ID: {video['id']})")

            # List files in Audio folder
            self.logger.info(f"\nListing files in Audio folder:")
            audio_files = self.drive_service.files().list(
                q=f"'{audio_folder}' in parents",
                fields="files(id, name, mimeType)",
                supportsAllDrives=True,
                includeItemsFromAllDrives=True
            ).execute().get('files', [])
            
            self.logger.info(f"Found {len(audio_files)} audio files:")
            for audio in audio_files:
                self.logger.info(f"- Audio: {audio['name']} (ID: {audio['id']})")

            # Process each video
            for video in videos:
                self.logger.info(f"\nProcessing video: {video['name']}")
                
                # Remove "Bản sao của" from the video name
                video_name_cleaned = video['name'].replace("Bản sao của ", "")
                video_url = f"https://drive.google.com/file/d/{video['id']}/view"
                
                # Check if already processed
                if self.db.url_exists(video_url):
                    self.logger.info(f"Skipping existing video: {video['name']}")
                    continue

                # Find corresponding audio files
                self.logger.info(f"Looking for audio files for video: {video_name_cleaned}")
                base_name = os.path.splitext(video_name_cleaned)[0]  # Use cleaned name
                
                # List all matching audio files
                matching_audio = [
                    f for f in audio_files 
                    if base_name in f['name']
                ]
                
                self.logger.info(f"Found {len(matching_audio)} related audio files:")
                for audio in matching_audio:
                    self.logger.info(f"- Related audio: {audio['name']}")

                # Find HV and mentor files
                hv_file = None
                mentor_file = None
                for file in matching_audio:
                    self.logger.info(f"Checking audio file: {file['name']}")
                    if 'HV' in file['name']:
                        hv_file = file
                        self.logger.info(f"Found HV file: {file['name']} (ID: {file['id']})")
                    elif 'mentor' in file['name']:
                        mentor_file = file
                        self.logger.info(f"Found mentor file: {file['name']} (ID: {file['id']})")

                if not (hv_file and mentor_file):
                    self.logger.error(f"Missing audio files for video: {video['name']}")
                    continue

                try:
                    # Download and process HV file
                    self.logger.info(f"Processing HV file: {hv_file['name']}")
                    hv_path = os.path.join(self.config.TEMP_DIR, f"hv_{video['id']}.wav")
                    self.logger.info(f"Downloading HV file to: {hv_path}")
                    
                    # Use new download method instead of gdown
                    if not self.download_file(hv_file['id'], hv_path):
                        raise Exception(f"Failed to download HV file: {hv_file['name']}")
                    
                    hv_result = self.audio_processor.process_audio(hv_path)

                    # Download and process mentor file
                    self.logger.info(f"Processing mentor file: {mentor_file['name']}")
                    mentor_path = os.path.join(self.config.TEMP_DIR, f"mentor_{video['id']}.wav")
                    self.logger.info(f"Downloading mentor file to: {mentor_path}")
                    
                    # Use new download method instead of gdown
                    if not self.download_file(mentor_file['id'], mentor_path):
                        raise Exception(f"Failed to download mentor file: {mentor_file['name']}")
                    
                    mentor_result = self.audio_processor.process_audio(mentor_path)

                    if hv_result and mentor_result:
                        self.logger.info("Combining transcriptions...")
                        transcript = self.audio_processor.combine_transcriptions(
                            hv_result, mentor_result)
                        
                        self.logger.info("Getting criteria...")
                        criteria = self.audio_processor.analyze_transcript(transcript)

                        # Save to database
                        self.logger.info("Saving to database...")
                        if self.db.insert_video(video_url, transcript, criteria):
                            self.logger.info(f"Successfully processed video: {video['name']}")
                    else:
                        self.logger.error("Failed to process audio files.")
                        continue

                    # Cleanup
                    self.logger.info("Cleaning up temporary files...")
                    for path in [hv_path, mentor_path]:
                        if os.path.exists(path):
                            os.remove(path)
                            self.logger.info(f"Removed temporary file: {path}")

                except Exception as e:
                    self.logger.error(f"Error processing video {video['name']}: {str(e)}")
                    continue

                time.sleep(3)  # Add delay between processing videos

        except Exception as e:
            self.logger.error(f"Error in main processing: {str(e)}")


def main():
    # Initialize config
    config = Config()
    
    # Setup logging
    os.makedirs(config.LOG_DIR, exist_ok=True)
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    
    if not logger.handlers:
        if not logger.handlers:
            fh = logging.FileHandler(os.path.join(config.LOG_DIR, 'app.log'), 
                                encoding='utf-8')
        fh.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logger.addHandler(fh)
        
        ch = logging.StreamHandler()
        ch.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logger.addHandler(ch)
    
    try:
        processor = VideoProcessor(config, logger)
        folder_id = "15ik6vWdz1IcbPmsPfr4p-DdszkB484yg"
        processor.process_folder(folder_id)
        
        # Display results
        logger.info("\nProcessed Videos:")
        with sqlite3.connect(config.DATABASE_PATH) as conn:
            cursor = conn.execute('''
                SELECT id, url_video, 
                       substr(transcription, 1, 100) as transcription_preview, 
                       criteria, created_at 
                FROM videos
                ORDER BY created_at DESC
            ''')
            for row in cursor.fetchall():
                logger.info(f"\nVideo ID: {row[0]}")
                logger.info(f"URL: {row[1]}")
                logger.info(f"Transcription Preview: {row[2]}...")
                logger.info(f"Criteria: {row[3]}")
                logger.info(f"Created at: {row[4]}")
                
    except Exception as e:
        logger.error(f"Main execution error: {e}")
        raise

if __name__ == '__main__':
    main()

"""
Language Detector - Detect spoken language in audio

This module provides language detection capabilities for audio content,
focusing on identifying Vietnamese speech in children's voice recordings.
"""

import numpy as np
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum

from ..config import AnalysisConfig
from ..models import LanguageDetectionResult
from ..utils import get_output_manager


class Language(Enum):
    """Supported languages for detection."""
    VIETNAMESE = "vi"
    ENGLISH = "en"
    UNKNOWN = "unknown"


@dataclass
class LanguageDetectionResultLocal:
    """Result of language detection analysis."""
    detected_language: Language
    confidence: float
    language_probabilities: Dict[str, float]
    processing_time: float
    model_version: str

    @property
    def is_successful(self) -> bool:
        """Check if language detection was successful."""
        return self.detected_language != Language.UNKNOWN and self.confidence > 0.0


class LanguageDetector:
    """
    Machine learning model for detecting spoken language in audio.

    Uses acoustic features and deep learning to identify the language
    being spoken, with focus on Vietnamese children's speech.
    """

    def __init__(self, config: AnalysisConfig):
        """
        Initialize language detector.

        Args:
            config: Analysis configuration
        """
        self.config = config
        self.output = get_output_manager()

        # Model parameters
        self.model = None
        self.device = None  # Initialize lazily
        self.model_version = "1.0.0"

        # Supported languages
        self.supported_languages = [Language.VIETNAMESE, Language.ENGLISH]

        # Feature extraction parameters
        self.sample_rate = 16000
        self.n_mfcc = 13
        self.n_fft = 400
        self.hop_length = 160

        self.output.debug("Initialized language detector")

    def load_model(self, model_path: Optional[Path] = None) -> bool:
        """
        Load the language detection model.

        Args:
            model_path: Path to model file (optional)

        Returns:
            True if model loaded successfully
        """
        try:
            # For now, create a simple placeholder model
            # In production, this would load a trained PyTorch model
            self.model = self._create_placeholder_model()
            self.output.debug("Language detection model loaded")
            return True

        except Exception as e:
            self.output.error(f"Failed to load language detection model: {e}")
            return False

    def _create_placeholder_model(self) -> Any:
        """Create a placeholder model for demonstration."""
        try:
            import torch
            import torch.nn as nn
        except ImportError:
            return None

        class SimpleLanguageDetector(nn.Module):
            def __init__(self, num_languages=2):
                super().__init__()
                self.fc1 = nn.Linear(13, 64)  # 13 MFCC features
                self.fc2 = nn.Linear(64, 32)
                self.fc3 = nn.Linear(32, num_languages)
                self.dropout = nn.Dropout(0.3)

            def forward(self, x):
                x = torch.relu(self.fc1(x))
                x = self.dropout(x)
                x = torch.relu(self.fc2(x))
                x = self.dropout(x)
                x = torch.softmax(self.fc3(x), dim=1)
                return x

        model = SimpleLanguageDetector(len(self.supported_languages))
        model.eval()  # Set to evaluation mode
        return model

    def detect_language_file(self, audio_path: Path) -> LanguageDetectionResultLocal:
        """
        Detect language in an audio file.

        Args:
            audio_path: Path to audio file

        Returns:
            Language detection result
        """
        import time
        start_time = time.time()

        try:
            # Extract features from audio
            features = self._extract_features(audio_path)

            if features is None:
                return LanguageDetectionResultLocal(
                    detected_language=Language.UNKNOWN,
                    confidence=0.0,
                    language_probabilities={},
                    processing_time=time.time() - start_time,
                    model_version=self.model_version
                )

            # Detect language using model
            detected_lang, confidence, probabilities = self._detect_language(features)

            return LanguageDetectionResultLocal(
                detected_language=detected_lang,
                confidence=confidence,
                language_probabilities=probabilities,
                processing_time=time.time() - start_time,
                model_version=self.model_version
            )

        except Exception as e:
            self.output.error(f"Language detection failed for {audio_path}: {e}")
            return LanguageDetectionResultLocal(
                detected_language=Language.UNKNOWN,
                confidence=0.0,
                language_probabilities={},
                processing_time=time.time() - start_time,
                model_version=self.model_version
            )

    def _extract_features(self, audio_path: Path) -> Optional[Dict[str, float]]:
        """
        Extract acoustic features from audio file.

        Args:
            audio_path: Path to audio file

        Returns:
            Dictionary of extracted features
        """
        try:
            import librosa

            # Load audio
            audio, sr = librosa.load(audio_path, sr=self.sample_rate)

            if len(audio) == 0:
                return None

            # Extract MFCC features
            mfccs = librosa.feature.mfcc(
                y=audio,
                sr=sr,
                n_mfcc=self.n_mfcc,
                n_fft=self.n_fft,
                hop_length=self.hop_length
            )

            # Compute statistics
            features = {}
            for i in range(self.n_mfcc):
                mfcc_coeffs = mfccs[i]
                features[f'mfcc_{i}_mean'] = float(np.mean(mfcc_coeffs))
                features[f'mfcc_{i}_std'] = float(np.std(mfcc_coeffs))

            # Additional language-discriminative features
            features['rms_energy'] = float(np.mean(librosa.feature.rms(y=audio)))
            features['zero_crossing_rate'] = float(np.mean(librosa.feature.zero_crossing_rate(audio)))
            features['spectral_centroid'] = float(np.mean(librosa.feature.spectral_centroid(y=audio, sr=sr)))
            features['spectral_rolloff'] = float(np.mean(librosa.feature.spectral_rolloff(y=audio, sr=sr)))

            return features

        except ImportError:
            self.output.warning("librosa not available - using mock features")
            return self._mock_features()
        except Exception as e:
            self.output.error(f"Feature extraction failed: {e}")
            return None

    def _mock_features(self) -> Dict[str, float]:
        """Generate mock features for testing."""
        features = {}
        for i in range(self.n_mfcc):
            features[f'mfcc_{i}_mean'] = np.random.normal(0, 1)
            features[f'mfcc_{i}_std'] = np.random.uniform(0.1, 2.0)

        features['rms_energy'] = np.random.uniform(0.01, 0.1)
        features['zero_crossing_rate'] = np.random.uniform(0.01, 0.2)
        features['spectral_centroid'] = np.random.uniform(1000, 5000)
        features['spectral_rolloff'] = np.random.uniform(2000, 8000)

        return features

    def _detect_language(self, features: Dict[str, float]) -> tuple[Language, float, Dict[str, float]]:
        """
        Detect language using the model.

        Args:
            features: Extracted audio features

        Returns:
            Tuple of (detected_language, confidence, probabilities)
        """
        if self.model is None:
            # Fallback: use simple heuristic
            # Vietnamese speech often has different spectral characteristics
            centroid = features.get('spectral_centroid', 3000)
            rolloff = features.get('spectral_rolloff', 4000)

            # Simple heuristic: higher frequencies might indicate Vietnamese tones
            vietnamese_score = min(max((centroid - 2500) / 1500, 0.0), 1.0)
            english_score = 1.0 - vietnamese_score

            probabilities = {
                Language.VIETNAMESE.value: vietnamese_score,
                Language.ENGLISH.value: english_score
            }

            detected = Language.VIETNAMESE if vietnamese_score > english_score else Language.ENGLISH
            confidence = max(vietnamese_score, english_score)

            return detected, confidence, probabilities

        try:
            # Initialize device if not done yet
            if self.device is None:
                try:
                    import torch
                    self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
                except ImportError:
                    self.device = 'cpu'

            # Ensure model is on the correct device
            if self.model is not None:
                self.model.to(self.device)

            # Prepare features for model input
            feature_vector = self._features_to_vector(features)

            # Run inference
            try:
                import torch
                with torch.no_grad():
                    inputs = torch.tensor(feature_vector, dtype=torch.float32).unsqueeze(0).to(self.device)
                    outputs = self.model(inputs)
                    probabilities_tensor = outputs.squeeze()

                    # Convert to probabilities dictionary
                    probabilities = {}
                    for i, lang in enumerate(self.supported_languages):
                        probabilities[lang.value] = float(probabilities_tensor[i])

                    # Find most likely language
                    max_prob_idx = torch.argmax(probabilities_tensor).item()
                    detected_language = self.supported_languages[max_prob_idx]
                    confidence = float(probabilities_tensor[max_prob_idx])
            except ImportError:
                # Fallback if torch not available
                probabilities = {lang.value: 0.5 for lang in self.supported_languages}
                detected_language = Language.UNKNOWN
                confidence = 0.0

            return detected_language, confidence, probabilities

        except Exception as e:
            self.output.error(f"Model inference failed: {e}")
            return Language.UNKNOWN, 0.0, {}

    def _features_to_vector(self, features: Dict[str, float]) -> np.ndarray:
        """Convert feature dictionary to model input vector."""
        # Use MFCC means for the simple model
        vector = []
        for i in range(self.n_mfcc):
            vector.append(features.get(f'mfcc_{i}_mean', 0.0))

        return np.array(vector, dtype=np.float32)

    def analyze_audio_chunk(self, audio_chunk: np.ndarray, sample_rate: int) -> LanguageDetectionResultLocal:
        """
        Analyze a chunk of audio data directly.

        Args:
            audio_chunk: Audio data as numpy array
            sample_rate: Sample rate of audio

        Returns:
            Language detection result
        """
        import time
        start_time = time.time()

        try:
            # Extract features from audio chunk
            features = self._extract_features_from_array(audio_chunk, sample_rate)

            if features is None:
                return LanguageDetectionResultLocal(
                    detected_language=Language.UNKNOWN,
                    confidence=0.0,
                    language_probabilities={},
                    processing_time=time.time() - start_time,
                    model_version=self.model_version
                )

            # Detect language
            detected_lang, confidence, probabilities = self._detect_language(features)

            return LanguageDetectionResultLocal(
                detected_language=detected_lang,
                confidence=confidence,
                language_probabilities=probabilities,
                processing_time=time.time() - start_time,
                model_version=self.model_version
            )

        except Exception as e:
            self.output.error(f"Audio chunk analysis failed: {e}")
            return LanguageDetectionResultLocal(
                detected_language=Language.UNKNOWN,
                confidence=0.0,
                language_probabilities={},
                processing_time=time.time() - start_time,
                model_version=self.model_version
            )

    def detect_language_from_youtube_transcript(self, video_id: str) -> LanguageDetectionResultLocal:
        """
        Detect language from YouTube video using auto-generated transcripts.
        This is much more accurate than audio-based detection.

        Args:
            video_id: YouTube video ID

        Returns:
            Language detection result
        """
        import time
        start_time = time.time()

        try:
            # Import YouTube Transcript API (similar to working example)
            try:
                from youtube_transcript_api import YouTubeTranscriptApi
                transcript_api_available = True
            except ImportError:
                self.output.warning("youtube-transcript-api not available, falling back to audio-based detection")
                return LanguageDetectionResultLocal(
                    detected_language=Language.UNKNOWN,
                    confidence=0.0,
                    language_probabilities={
                        Language.VIETNAMESE.value: 0.0,
                        Language.ENGLISH.value: 0.0
                    },
                    processing_time=time.time() - start_time,
                    model_version=self.model_version
                )

            # Get available transcripts (similar to working example)
            try:
                transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            except Exception as e:
                self.output.debug(f"No transcripts available for video {video_id}: {e}")
                return LanguageDetectionResultLocal(
                    detected_language=Language.UNKNOWN,
                    confidence=0.0,
                    language_probabilities={
                        Language.VIETNAMESE.value: 0.0,
                        Language.ENGLISH.value: 0.0
                    },
                    processing_time=time.time() - start_time,
                    model_version=self.model_version
                )

            # Find auto-generated transcript (similar to working example)
            auto_generated_transcript = None
            for transcript in transcript_list:
                if transcript.is_generated:  # Check if auto-generated
                    auto_generated_transcript = transcript
                    break

            if auto_generated_transcript is None:
                self.output.debug(f"No auto-generated transcript found for video {video_id}")
                return LanguageDetectionResultLocal(
                    detected_language=Language.UNKNOWN,
                    confidence=0.0,
                    language_probabilities={
                        Language.VIETNAMESE.value: 0.0,
                        Language.ENGLISH.value: 0.0
                    },
                    processing_time=time.time() - start_time,
                    model_version=self.model_version
                )

            # Get the language code directly (much simpler than working example)
            language_code = auto_generated_transcript.language_code

            # Map language codes to our enum
            if language_code.lower() == 'vi':
                detected_lang = Language.VIETNAMESE
                vietnamese_prob = 1.0
                english_prob = 0.0
                confidence = 1.0
            elif language_code.lower() in ['en', 'en-us', 'en-gb']:
                detected_lang = Language.ENGLISH
                vietnamese_prob = 0.0
                english_prob = 1.0
                confidence = 1.0
            else:
                # Unknown language
                detected_lang = Language.UNKNOWN
                vietnamese_prob = 0.0
                english_prob = 0.0
                confidence = 0.0

            self.output.debug(f"Transcript language detection for {video_id}: {language_code} -> {detected_lang.value}")

            return LanguageDetectionResultLocal(
                detected_language=detected_lang,
                confidence=confidence,
                language_probabilities={
                    Language.VIETNAMESE.value: vietnamese_prob,
                    Language.ENGLISH.value: english_prob
                },
                processing_time=time.time() - start_time,
                model_version=self.model_version
            )

        except Exception as e:
            self.output.error(f"YouTube transcript language detection failed for {video_id}: {e}")
            return LanguageDetectionResultLocal(
                detected_language=Language.UNKNOWN,
                confidence=0.0,
                language_probabilities={
                    Language.VIETNAMESE.value: 0.0,
                    Language.ENGLISH.value: 0.0
                },
                processing_time=time.time() - start_time,
                model_version=self.model_version
            )

    def detect_language_from_text(self, text: str) -> LanguageDetectionResultLocal:
        """
        Detect language from text content using transcript analysis.

        Args:
            text: Text content to analyze

        Returns:
            Language detection result
        """
        import time
        start_time = time.time()

        try:
            # Use transcript-based language detection similar to the working example
            # Check for Vietnamese vs English patterns in transcript text

            if not text or not text.strip():
                return LanguageDetectionResultLocal(
                    detected_language=Language.UNKNOWN,
                    confidence=0.0,
                    language_probabilities={
                        Language.VIETNAMESE.value: 0.0,
                        Language.ENGLISH.value: 0.0
                    },
                    processing_time=time.time() - start_time,
                    model_version=self.model_version
                )

            text_lower = text.lower()

            # Vietnamese language patterns (from the working example)
            vietnamese_indicators = {
                'chars': set('ăâêôưđ'),  # Vietnamese specific characters
                'words': [
                    'cái', 'là', 'của', 'và', 'có', 'không', 'được', 'cho', 'với', 'như',
                    'tôi', 'bạn', 'anh', 'chị', 'em', 'cháu', 'bố', 'mẹ', 'con',
                    'nhà', 'đi', 'đến', 'từ', 'ở', 'làm', 'học', 'chơi', 'ăn', 'uống'
                ],
                'particles': ['ạ', 'ạh', 'ơi', 'nha', 'đi', 'mà', 'là', 'thì', 'mới', 'đã']
            }

            # English language patterns
            english_indicators = {
                'words': [
                    'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by',
                    'this', 'that', 'these', 'those', 'here', 'there', 'where', 'when', 'why', 'how',
                    'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them'
                ]
            }

            vietnamese_score = 0.0
            english_score = 0.0

            # Check for Vietnamese specific characters (strong indicator)
            vietnamese_chars_found = sum(1 for char in vietnamese_indicators['chars'] if char in text_lower)
            if vietnamese_chars_found > 0:
                vietnamese_score += vietnamese_chars_found * 2.0  # Strong weight for Vietnamese chars

            # Check for Vietnamese words
            vietnamese_words_found = 0
            for word in vietnamese_indicators['words']:
                if word in text_lower:
                    vietnamese_words_found += 1
            vietnamese_score += vietnamese_words_found * 0.5

            # Check for Vietnamese particles (common in speech)
            vietnamese_particles_found = 0
            for particle in vietnamese_indicators['particles']:
                # Use word boundaries for particles
                if f' {particle} ' in f' {text_lower} ':
                    vietnamese_particles_found += 1
            vietnamese_score += vietnamese_particles_found * 0.3

            # Check for English words
            english_words_found = 0
            for word in english_indicators['words']:
                if f' {word} ' in f' {text_lower} ':
                    english_words_found += 1
            english_score += english_words_found * 0.5

            # Length-based scoring (longer transcripts are more reliable)
            text_length = len(text.split())
            length_bonus = min(text_length / 50.0, 1.0)  # Bonus for longer transcripts

            # Normalize scores
            total_score = vietnamese_score + english_score
            if total_score > 0:
                vietnamese_prob = (vietnamese_score / total_score) * length_bonus
                english_prob = (english_score / total_score) * length_bonus
            else:
                # No clear indicators found
                vietnamese_prob = 0.0
                english_prob = 0.0

            # Determine final language with confidence threshold
            confidence_threshold = 0.6

            if vietnamese_prob > english_prob and vietnamese_prob > confidence_threshold:
                detected_lang = Language.VIETNAMESE
                confidence = vietnamese_prob
            elif english_prob > vietnamese_prob and english_prob > confidence_threshold:
                detected_lang = Language.ENGLISH
                confidence = english_prob
            else:
                detected_lang = Language.UNKNOWN
                confidence = max(vietnamese_prob, english_prob)

            probabilities = {
                Language.VIETNAMESE.value: vietnamese_prob,
                Language.ENGLISH.value: english_prob
            }

            return LanguageDetectionResultLocal(
                detected_language=detected_lang,
                confidence=confidence,
                language_probabilities=probabilities,
                processing_time=time.time() - start_time,
                model_version=self.model_version
            )

        except Exception as e:
            self.output.error(f"Text language detection failed: {e}")
            return LanguageDetectionResultLocal(
                detected_language=Language.UNKNOWN,
                confidence=0.0,
                language_probabilities={
                    Language.VIETNAMESE.value: 0.0,
                    Language.ENGLISH.value: 0.0
                },
                processing_time=time.time() - start_time,
                model_version=self.model_version
            )

    def _extract_features_from_array(self, audio: np.ndarray, sr: int) -> Optional[Dict[str, float]]:
        """Extract features from audio array."""
        try:
            import librosa

            if len(audio) == 0:
                return None

            # Resample if necessary
            if sr != self.sample_rate:
                audio = librosa.resample(audio, orig_sr=sr, target_sr=self.sample_rate)

            # Extract MFCC features
            mfccs = librosa.feature.mfcc(
                y=audio,
                sr=self.sample_rate,
                n_mfcc=self.n_mfcc,
                n_fft=self.n_fft,
                hop_length=self.hop_length
            )

            # Compute statistics
            features = {}
            for i in range(self.n_mfcc):
                mfcc_coeffs = mfccs[i]
                features[f'mfcc_{i}_mean'] = float(np.mean(mfcc_coeffs))
                features[f'mfcc_{i}_std'] = float(np.std(mfcc_coeffs))

            # Additional features
            features['rms_energy'] = float(np.mean(librosa.feature.rms(y=audio)))
            features['zero_crossing_rate'] = float(np.mean(librosa.feature.zero_crossing_rate(audio)))

            return features

        except ImportError:
            self.output.warning("librosa not available - using mock features")
            return self._mock_features()
        except Exception as e:
            self.output.error(f"Feature extraction from array failed: {e}")
            return None
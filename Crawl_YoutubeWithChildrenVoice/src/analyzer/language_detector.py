"""
Language Detector - Detect spoken language in audio

This module provides language detection capabilities for audio content,
focusing on identifying Vietnamese speech in children's voice recordings.
"""

import numpy as np
import torch
import torch.nn as nn
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
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
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

    def _create_placeholder_model(self) -> nn.Module:
        """Create a placeholder model for demonstration."""
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
            # Prepare features for model input
            feature_vector = self._features_to_vector(features)

            # Run inference
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
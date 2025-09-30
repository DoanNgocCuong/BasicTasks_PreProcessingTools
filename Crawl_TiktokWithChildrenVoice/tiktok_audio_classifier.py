#!/usr/bin/env python3
"""
TikTok Audio Classifier with Model Caching and Language Detection

This module provides advanced audio classification capabilities specifically designed for
analyzing TikTok video content. It combines children's voice detection with Vietnamese
language detection, adapted from the YouTube crawler's audio analysis pipeline.

Features:
    - Children's voice detection using Wav2Vec2 model
    - Vietnamese language detection using Whisper
    - Model caching for optimal performance
    - TikTok-specific audio preprocessing

Author: Generated for TikTok Children's Voice Crawl        print(f\"   Device: {stats['device']}\")
        print(f\"   Whisper available: {stats['whisper_available']}\")
        print(f\"   Transformers available: {stats['transformers_available']}\")
        print(f\"   PyTorch available: {stats['torch_available']}\")dapted from YouTube crawler)
Version: 1.0
"""

import os
import sys
import warnings
import logging
import threading
import tempfile
import shutil
import time
from pathlib import Path
from typing import Optional, Dict, Tuple, NamedTuple, Any, Union
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass

import numpy as np
import librosa
import soundfile as sf

# Import environment configuration
try:
    from env_config import config
    USE_ENV_CONFIG = True
except ImportError:
    config = None
    USE_ENV_CONFIG = False

# Constants
DEFAULT_SAMPLE_RATE = 16000
DEFAULT_MAX_AUDIO_LENGTH = 30.0
DEFAULT_CHILD_THRESHOLD = 0.5
DEFAULT_AGE_THRESHOLD = 0.3
TEMP_FILE_SUFFIX = "_temp_segment"
MIN_AUDIO_LENGTH = 0.5  # Minimum audio length in seconds

# Import torch for ML models with better error handling
try:
    import torch
    import torch.nn as nn
    TORCH_AVAILABLE = True
except ImportError:
    torch = None
    nn = None
    TORCH_AVAILABLE = False
    print("⚠️ PyTorch not available, children's voice detection disabled")

# Import transformers for Wav2Vec2
try:
    from transformers import Wav2Vec2Processor
    from transformers.models.wav2vec2.modeling_wav2vec2 import (
        Wav2Vec2Model,
        Wav2Vec2PreTrainedModel,
    )
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    Wav2Vec2Processor = None
    Wav2Vec2Model = None
    Wav2Vec2PreTrainedModel = None
    TRANSFORMERS_AVAILABLE = False
    print("⚠️ Transformers not available, children's voice detection disabled")

# Import Whisper for transcription
try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    whisper = None
    WHISPER_AVAILABLE = False
    print("⚠️ Whisper not available, falling back to pattern-based detection")

# Suppress warnings
warnings.filterwarnings('ignore')

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Groq/Azure removed - set constants to prevent errors
GROQ_AVAILABLE = False

# CUDA memory optimization
if TORCH_AVAILABLE:
    os.environ['PYTORCH_CUDA_ALLOC_CONF'] = 'expandable_segments:True'
    if torch.cuda.is_available():
        torch.backends.cudnn.benchmark = True
        torch.backends.cuda.matmul.allow_tf32 = True
        torch.backends.cudnn.allow_tf32 = True


@dataclass
class AudioAnalysisResult:
    """Result of audio analysis containing all detection results."""
    is_vietnamese: bool
    detected_language: Optional[str]
    has_children_voice: bool
    confidence: float
    total_analysis_time: float
    children_detection_time: float
    video_length_seconds: float
    error: Optional[str] = None
    transcription: Optional[str] = None
    age_prediction: Optional[float] = None
    gender_probabilities: Optional[Dict[str, float]] = None


# Model classes only if dependencies available
if TORCH_AVAILABLE and TRANSFORMERS_AVAILABLE:
    class ModelHead(nn.Module):
        """Classification head for age/gender detection."""

        def __init__(self, config, num_labels):
            super().__init__()
            self.dense = nn.Linear(config.hidden_size, config.hidden_size)
            self.dropout = nn.Dropout(config.final_dropout)
            self.out_proj = nn.Linear(config.hidden_size, num_labels)

        def forward(self, features, **kwargs):
            x = features
            x = self.dropout(x)
            x = self.dense(x)
            x = torch.tanh(x)
            x = self.dropout(x)
            x = self.out_proj(x)
            return x

    class AgeGenderModel(Wav2Vec2PreTrainedModel):
        """Speech age and gender classifier."""

        def __init__(self, config):
            super().__init__(config)
            self.config = config
            self.wav2vec2 = Wav2Vec2Model(config)
            self.age = ModelHead(config, 1)
            self.gender = ModelHead(config, 3)
            self.init_weights()

        def forward(self, input_values):
            outputs = self.wav2vec2(input_values)
            hidden_states = outputs[0]
            hidden_states = torch.mean(hidden_states, dim=1)
            logits_age = self.age(hidden_states)
            logits_gender = torch.softmax(self.gender(hidden_states), dim=1)
            return hidden_states, logits_age, logits_gender
else:
    # Define stub classes when dependencies not available
    class ModelHead:
        def __init__(self, *args, **kwargs):
            pass
    
    class AgeGenderModel:
        @classmethod
        def from_pretrained(cls, *args, **kwargs):
            return None


class TikTokAudioClassifier:
    """TikTok audio classifier for children's voice and language detection."""
    
    def __init__(self, output_manager=None):
        """
        Initialize the TikTok audio classifier.
        
        Args:
            output_manager: Optional output manager for logging
        """
        self.output = output_manager
        
        # Configuration from environment or defaults
        if USE_ENV_CONFIG and config:
            self.child_threshold = getattr(config, 'CHILD_THRESHOLD', 0.5)
            self.age_threshold = getattr(config, 'AGE_THRESHOLD', 0.3)
            self.whisper_model_size = getattr(config, 'WHISPER_MODEL_SIZE', 'tiny')
            self.wav2vec2_model = getattr(config, 'WAV2VEC2_MODEL', 'audeering/wav2vec2-large-robust-24-ft-age-gender')
        else:
            self.child_threshold = 0.5
            self.age_threshold = 0.3
            self.whisper_model_size = "tiny"
            self.wav2vec2_model = "audeering/wav2vec2-large-robust-24-ft-age-gender"
        
        # Device configuration
        if TORCH_AVAILABLE:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        else:
            self.device = "cpu"
        
        # Model caching
        self._whisper_model = None
        self._wav2vec2_model = None
        self._wav2vec2_processor = None
        
        # Thread locks for model loading
        self._whisper_lock = threading.Lock()
        self._wav2vec2_lock = threading.Lock()
        
        # Statistics
        self.total_analyses = 0
        self.successful_analyses = 0
        self.failed_analyses = 0
        
        self._log("TikTok Audio Classifier initialized")
    
    def _log(self, message: str, level: str = "info") -> None:
        """Log message through output manager if available."""
        if self.output:
            if level == "error":
                self.output.print_error(message)
            elif level == "warning":
                self.output.print_warning(message)
            else:
                self.output.print_info(message)
        else:
            print(f"[{level.upper()}] {message}")
    
    def _load_whisper_model(self):
        """Lazy load Whisper model for language detection and transcription."""
        if not WHISPER_AVAILABLE:
            return None
            
        if self._whisper_model is None:
            with self._whisper_lock:
                if self._whisper_model is None:
                    try:
                        self._log(f"Loading Whisper model ({self.whisper_model_size})...")
                        self._whisper_model = whisper.load_model(self.whisper_model_size, device=self.device)
                        self._log("✅ Whisper model loaded successfully")
                    except Exception as e:
                        self._log(f"❌ Failed to load Whisper model: {e}", "error")
                        return None
        return self._whisper_model
    
    def _load_wav2vec2_model(self):
        """Lazy load Wav2Vec2 model for age/gender classification."""
        if not (TORCH_AVAILABLE and TRANSFORMERS_AVAILABLE):
            return None, None
            
        if self._wav2vec2_model is None or self._wav2vec2_processor is None:
            with self._wav2vec2_lock:
                if self._wav2vec2_model is None:
                    try:
                        self._log(f"Loading Wav2Vec2 model ({self.wav2vec2_model})...")
                        self._wav2vec2_processor = Wav2Vec2Processor.from_pretrained(self.wav2vec2_model)
                        model = AgeGenderModel.from_pretrained(self.wav2vec2_model)
                        if model is not None and TORCH_AVAILABLE:
                            self._wav2vec2_model = model.to(self.device)
                            self._wav2vec2_model.eval()
                        else:
                            self._wav2vec2_model = model
                        self._log("✅ Wav2Vec2 model loaded successfully")
                    except Exception as e:
                        self._log(f"❌ Failed to load Wav2Vec2 model: {e}", "error")
                        return None, None
        return self._wav2vec2_model, self._wav2vec2_processor
    
    def _load_groq_client(self):
        """Lazy load Groq client for transcription."""
        if not GROQ_AVAILABLE:
            return None
            
        if self._groq_client is None:
            with self._groq_lock:
                if self._groq_client is None:
                    try:
                        if (USE_ENV_CONFIG and config and 
                            hasattr(config, 'GROQ_API_KEY') and 
                            config.GROQ_API_KEY):
                            self._groq_client = None  # Groq removed from codebase
                            self._log("✅ Groq client initialized")
                        else:
                            self._log("⚠️ Groq API key not available", "warning")
                            return None
                    except Exception as e:
                        self._log(f"⚠️ Failed to initialize Groq client: {e}", "warning")
                        return None
        return self._groq_client
    
    def preprocess_audio(self, audio_path: str, target_sr: int = 16000) -> Tuple[Optional[np.ndarray], Optional[int]]:
        """
        Preprocess audio file for analysis.
        
        Args:
            audio_path (str): Path to audio file
            target_sr (int): Target sample rate
            
        Returns:
            Tuple[Optional[np.ndarray], Optional[int]]: (audio_array, sample_rate) or (None, None) if failed
        """
        try:
            # Load audio
            audio_array, sample_rate = librosa.load(audio_path, sr=target_sr, mono=True)
            
            # Validate audio
            if audio_array is None or len(audio_array) == 0:
                self._log(f"⚠️ Empty audio file: {audio_path}", "warning")
                return None, None
            
            if len(audio_array) < target_sr * 0.1:  # Less than 0.1 second
                self._log(f"⚠️ Audio too short: {audio_path} ({len(audio_array) / target_sr:.2f}s)", "warning")
                return None, None
            
            # Normalize audio
            if np.max(np.abs(audio_array)) > 0:
                audio_array = audio_array / np.max(np.abs(audio_array)) * 0.9
            
            return audio_array, int(target_sr)  # Ensure integer return
            
        except Exception as e:
            self._log(f"❌ Error preprocessing audio {audio_path}: {e}", "error")
            return None, None
    
    def detect_language_whisper(self, audio_path: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Detect language using Whisper model.
        
        Args:
            audio_path (str): Path to audio file
            
        Returns:
            Tuple[Optional[str], Optional[str]]: (detected_language, transcription) or (None, None) if failed
        """
        try:
            model = self._load_whisper_model()
            if not model:
                return None, None
            
            # Transcribe and detect language
            result = model.transcribe(audio_path, language=None)
            
            detected_language = result.get('language', 'unknown')
            transcription_data = result.get('text', '')
            
            # Handle different types of transcription data
            if isinstance(transcription_data, list):
                transcription = ' '.join(str(item) for item in transcription_data)
            else:
                transcription = str(transcription_data).strip()
            
            return detected_language, transcription
            
        except Exception as e:
            self._log(f"⚠️ Whisper language detection failed: {e}", "warning")
            return None, None
    
    def detect_language_groq(self, audio_path: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Detect language using Groq transcription service.
        
        Args:
            audio_path (str): Path to audio file
            
        Returns:
            Tuple[Optional[str], Optional[str]]: (detected_language, transcription) or (None, None) if failed
        """
        try:
            client = self._load_groq_client()
            if not client:
                return None, None
            
            # Transcribe with Groq
            with open(audio_path, "rb") as file:
                transcription = client.audio.transcriptions.create(
                    file=(audio_path, file.read()),
                    model="whisper-large-v3",
                    response_format="json",
                )
                
                if hasattr(transcription, 'text'):
                    text = transcription.text
                    # Simple Vietnamese detection based on text content
                    vietnamese_indicators = ['là', 'của', 'với', 'trong', 'được', 'có', 'không', 'và', 'một', 'các']
                    if any(word in text.lower() for word in vietnamese_indicators):
                        return 'vi', text
                    else:
                        return 'unknown', text
                else:
                    return None, None
                    
        except Exception as e:
            self._log(f"⚠️ Groq language detection failed: {e}", "warning")
            return None, None
    
    def detect_language_pattern_based(self, transcription: str) -> bool:
        """
        Pattern-based Vietnamese language detection as fallback.
        
        Args:
            transcription (str): Transcribed text
            
        Returns:
            bool: True if likely Vietnamese, False otherwise
        """
        if not transcription:
            return False
        
        # Vietnamese language indicators
        vietnamese_patterns = [
            'là', 'của', 'với', 'trong', 'được', 'có', 'không', 'và', 'một', 'các',
            'để', 'về', 'này', 'đó', 'khi', 'như', 'sẽ', 'đã', 'cho', 'từ',
            'bạn', 'tôi', 'em', 'anh', 'chị', 'con', 'mẹ', 'bố', 'gia đình'
        ]
        
        text_lower = transcription.lower()
        matches = sum(1 for pattern in vietnamese_patterns if pattern in text_lower)
        
        # Consider Vietnamese if at least 2 indicators found
        return matches >= 2
    
    def classify_children_voice(self, audio_path: str) -> Tuple[bool, float, Optional[Dict[str, float]]]:
        """
        Classify if audio contains children's voice using Wav2Vec2 model.
        
        Args:
            audio_path (str): Path to audio file
            
        Returns:
            Tuple[bool, float, Optional[Dict[str, float]]]: (has_children_voice, confidence, gender_probs)
        """
        try:
            model, processor = self._load_wav2vec2_model()
            if not model or not processor:
                # Fallback to simple heuristics
                return self._classify_children_voice_fallback(audio_path)
            
            # Preprocess audio
            audio_array, sample_rate = self.preprocess_audio(audio_path)
            if audio_array is None:
                return False, 0.0, None
            
            # Process with model
            inputs = processor(audio_array, sampling_rate=sample_rate, return_tensors="pt")
            input_values = inputs['input_values'].to(self.device)
            
            if TORCH_AVAILABLE:
                with torch.no_grad():
                    hidden_states, age_logits, gender_probs = model(input_values)
                    
                    # Age prediction (0-1 scale, 0=0 years, 1=100 years)
                    age_normalized = float(age_logits.squeeze().cpu())
                    
                    # Gender prediction probabilities [female, male, child]
                    gender_probs_array = gender_probs.squeeze().cpu().numpy()
                    child_prob = float(gender_probs_array[2]) if len(gender_probs_array) > 2 else 0.0
                    
                    # Classification logic
                    has_children_voice = (child_prob > self.child_threshold) or (age_normalized < self.age_threshold)
                    confidence = max(child_prob, 1.0 - age_normalized) if has_children_voice else min(child_prob, age_normalized)
                    
                    gender_dict = {
                        'female': float(gender_probs_array[0]),
                        'male': float(gender_probs_array[1]),
                        'child': child_prob
                    } if len(gender_probs_array) >= 3 else None
                    
                    return has_children_voice, confidence, gender_dict
            else:
                return self._classify_children_voice_fallback(audio_path)
                
        except Exception as e:
            self._log(f"⚠️ Children's voice classification failed: {e}", "warning")
            return self._classify_children_voice_fallback(audio_path)
    
    def _classify_children_voice_fallback(self, audio_path: str) -> Tuple[bool, float, Optional[Dict[str, float]]]:
        """
        Fallback children's voice classification using audio features.
        
        Args:
            audio_path (str): Path to audio file
            
        Returns:
            Tuple[bool, float, Optional[Dict[str, float]]]: (has_children_voice, confidence, None)
        """
        try:
            # Load audio
            audio_array, sample_rate = librosa.load(audio_path, sr=22050, mono=True)
            
            # Extract fundamental frequency (pitch)
            pitches, magnitudes = librosa.piptrack(y=audio_array, sr=sample_rate, threshold=0.1)
            
            # Get mean pitch (Hz)
            pitch_values = []
            for t in range(pitches.shape[1]):
                index = magnitudes[:, t].argmax()
                pitch = pitches[index, t]
                if pitch > 0:
                    pitch_values.append(pitch)
            
            if not pitch_values:
                return False, 0.0, None
            
            mean_pitch = np.mean(pitch_values)
            
            # Children typically have higher pitch (>250 Hz)
            # Adults typically have lower pitch (<200 Hz for women, <150 Hz for men)
            if mean_pitch > 280:
                confidence = min(0.8, (mean_pitch - 200) / 200)
                return True, confidence, None
            elif mean_pitch > 250:
                confidence = 0.6
                return True, confidence, None
            else:
                confidence = max(0.2, 1.0 - (mean_pitch / 250))
                return False, confidence, None
                
        except Exception as e:
            self._log(f"⚠️ Fallback children's voice classification failed: {e}", "warning")
            return False, 0.0, None
    
    def analyze_audio(self, audio_path: str) -> AudioAnalysisResult:
        """
        Comprehensive audio analysis for Vietnamese language and children's voice detection.
        
        Args:
            audio_path (str): Path to audio file
            
        Returns:
            AudioAnalysisResult: Complete analysis results
        """
        start_time = time.time()
        self.total_analyses += 1
        
        try:
            # Get audio duration
            try:
                info = sf.info(audio_path)
                duration = info.frames / info.samplerate
            except:
                duration = 0.0
            
            # Language detection
            detected_language = None
            transcription = None
            is_vietnamese = False
            
            # Try Whisper for language detection (Groq removed)
            if WHISPER_AVAILABLE:
                detected_language, transcription = self.detect_language_whisper(audio_path)
                if detected_language == 'vi':
                    is_vietnamese = True
            
            # Pattern-based fallback
            if not is_vietnamese and transcription:
                is_vietnamese = self.detect_language_pattern_based(transcription)
                if is_vietnamese and not detected_language:
                    detected_language = 'vi'
            
            # Children's voice detection
            children_start_time = time.time()
            has_children_voice, confidence, gender_probs = self.classify_children_voice(audio_path)
            children_detection_time = time.time() - children_start_time
            
            total_time = time.time() - start_time
            self.successful_analyses += 1
            
            return AudioAnalysisResult(
                is_vietnamese=is_vietnamese,
                detected_language=detected_language,
                has_children_voice=has_children_voice,
                confidence=confidence,
                total_analysis_time=total_time,
                children_detection_time=children_detection_time,
                video_length_seconds=duration,
                transcription=transcription,
                gender_probabilities=gender_probs
            )
            
        except Exception as e:
            self.failed_analyses += 1
            total_time = time.time() - start_time
            
            return AudioAnalysisResult(
                is_vietnamese=False,
                detected_language=None,
                has_children_voice=False,
                confidence=0.0,
                total_analysis_time=total_time,
                children_detection_time=0.0,
                video_length_seconds=0.0,
                error=str(e)
            )
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get classifier statistics."""
        return {
            'total_analyses': self.total_analyses,
            'successful_analyses': self.successful_analyses,
            'failed_analyses': self.failed_analyses,
            'success_rate': (self.successful_analyses / max(self.total_analyses, 1)) * 100,
            'device': str(self.device),
            'whisper_available': WHISPER_AVAILABLE,
            'transformers_available': TRANSFORMERS_AVAILABLE,
            'torch_available': TORCH_AVAILABLE
        }


# Testing function
if __name__ == "__main__":
    print("🧪 Testing TikTok Audio Classifier...")
    
    try:
        classifier = TikTokAudioClassifier()
        stats = classifier.get_statistics()
        
        print("✅ Audio classifier initialized successfully")
        print(f"   Device: {stats['device']}")
        print(f"   Whisper available: {stats['whisper_available']}")
        print(f"   Transformers available: {stats['transformers_available']}")
        print(f"   Groq available: {stats['groq_available']}")
        print(f"   PyTorch available: {stats['torch_available']}")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
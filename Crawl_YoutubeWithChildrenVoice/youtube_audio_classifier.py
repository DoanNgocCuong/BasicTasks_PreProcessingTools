#!/usr/bin/env python3
"""
YouTube Audio Classifier with Model Caching and Language Detection

This module provides advanced audio classification capabilities specifically designed for
analyzing YouTube video content. It combines children's voice detection with Vietnamese
language detection, featuring intelligent model caching for optimal performance.

Author: Le Hoang Minh
"""

# @DoanNgocCuong - Embedded exact same logic from AgeDetection.py
import os
import sys
import shutil
import warnings
import logging
import importlib.util
from pathlib import Path
from typing import Optional, Dict
from concurrent.futures import ThreadPoolExecutor, as_completed

import torch
import torch.nn as nn
import librosa
import numpy as np
import whisper

# Import environment configuration
try:
    from env_config import config
    USE_ENV_CONFIG = True
    print("✅ Audio Classifier using environment configuration")
except ImportError:
    config = None
    USE_ENV_CONFIG = False
    print("⚠️ Environment configuration not available, using defaults")
from transformers import Wav2Vec2Processor
from transformers.models.wav2vec2.modeling_wav2vec2 import (
    Wav2Vec2Model,
    Wav2Vec2PreTrainedModel,
)

# Tắt warnings không cần thiết
warnings.filterwarnings('ignore')

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class ModelHead(nn.Module):
    """Classification head."""

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


class BaseAudioClassifier:
    """Base audio classifier with exact same logic from AgeDetection.py"""
    
    def __init__(self, model_name=None, child_threshold=None, age_threshold=None):
        """
        Initialize classifier with model and confidence thresholds
        
        Args:
            model_name: Model name on Hugging Face (uses env config if None)
            child_threshold: Probability threshold for classifying as child (uses env config if None)
            age_threshold: Age threshold for classifying as child (uses env config if None)
        """
        # Use environment configuration if available, otherwise defaults
        if USE_ENV_CONFIG and config is not None:
            self.model_name = model_name or config.WAV2VEC2_MODEL
            self.child_threshold = child_threshold if child_threshold is not None else config.CHILD_THRESHOLD
            self.age_threshold = age_threshold if age_threshold is not None else config.AGE_THRESHOLD
        else:
            self.model_name = model_name or "audeering/wav2vec2-large-robust-24-ft-age-gender"
            self.child_threshold = child_threshold if child_threshold is not None else 0.5
            self.age_threshold = age_threshold if age_threshold is not None else 0.3
            
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        logger.info(f"Using device: {self.device}")
        logger.info(f"Model: {self.model_name}")
        logger.info(f"Child threshold: {self.child_threshold}")
        logger.info(f"Age threshold: {self.age_threshold}")
        
        # Load model and processor
        try:
            logger.info("Loading model...")
            self.processor = Wav2Vec2Processor.from_pretrained(model_name)
            self.model = AgeGenderModel.from_pretrained(model_name)
            self.model = self.model.to(self.device)
            self.model.eval()
            logger.info("Model loaded successfully!")
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            raise
        
        # Labels: [female, male, child]
        self.gender_labels = ['female', 'male', 'child']
        
    def preprocess_audio(self, audio_path, target_sr=16000):
        """
        Preprocess audio file
        """
        try:
            # Use librosa to load audio
            speech_array, original_sr = librosa.load(audio_path, sr=None)
            
            # Resample if needed
            if original_sr != target_sr:
                speech_array = librosa.resample(speech_array, orig_sr=original_sr, target_sr=target_sr)
            
            # Normalize audio
            if np.max(np.abs(speech_array)) > 0:
                speech_array = speech_array / np.max(np.abs(speech_array))
            
            return speech_array.astype(np.float32), target_sr
        except Exception as e:
            logger.error(f"Error processing audio {audio_path}: {e}")
            return None, None
    
    def predict(self, audio_path):
        """
        Predict age and gender for audio file
        """
        speech_array, sampling_rate = self.preprocess_audio(audio_path)
        if speech_array is None:
            return None, None, None, "error"
        
        try:
            # Process audio
            inputs = self.processor(speech_array, sampling_rate=sampling_rate)
            input_values = inputs['input_values'][0]
            input_values = input_values.reshape(1, -1)
            input_values = torch.from_numpy(input_values).to(self.device)
            
            # Prediction
            with torch.no_grad():
                hidden_states, age_logits, gender_probs = self.model(input_values)
                
                # Age prediction (0-1 scale, 0=0 years, 1=100 years)
                age_normalized = float(age_logits.squeeze())
                age_years = age_normalized * 100  # Convert to years
                
                # Gender prediction probabilities [female, male, child]
                gender_probs = gender_probs.squeeze().cpu().numpy()
                
                return age_normalized, age_years, gender_probs, "success"
                
        except Exception as e:
            logger.error(f"Error predicting for {audio_path}: {e}")
            return None, None, None, "error"
    
    def classify_age_group(self, age_normalized, gender_probs):
        """
        Classify as child or adult
        
        Logic:
        1. If gender_probs[2] (child) > child_threshold -> child
        2. Or if age_normalized < age_threshold -> child  
        3. Otherwise -> adult
        """
        child_prob = gender_probs[2] if gender_probs is not None else 0
        
        # Check child probability
        if child_prob > self.child_threshold:
            return "child", child_prob
        
        # Or check age
        if age_normalized is not None and age_normalized < self.age_threshold:
            return "child", age_normalized
        
        return "adult", 1 - child_prob


# Utility functions from utils_remove1s_indexing.py
def filter_and_rename(input_dir="input"):
    """
    Filter out short audio files and rename remaining files with sequential numbering.
    
    Args:
        input_dir: Directory containing .wav files
        
    Process:
        1. Move files with duration <= 2.0s to recycle folder
        2. Rename remaining files as 1_<filename>.wav, 2_<filename>.wav, etc.
    """
    recycle_dir = os.path.join(input_dir, "recycle")
    os.makedirs(recycle_dir, exist_ok=True)

    files = [f for f in os.listdir(input_dir) if f.endswith('.wav')]
    files.sort()
    valid_files = []
    
    for f in files:
        path = os.path.join(input_dir, f)
        try:
            # Fast duration check without loading full audio
            try:
                import soundfile as sf
                info = sf.info(path)
                duration = info.frames / info.samplerate
            except ImportError:
                # Fallback to librosa if soundfile not available
                duration = librosa.get_duration(filename=path)
            
            if duration <= 2.0:
                shutil.move(path, os.path.join(recycle_dir, f))
                print(f"Moved {f} to recycle (duration: {duration:.2f}s)")
            else:
                valid_files.append(f)
        except Exception as e:
            print(f"Error with {f}: {e}")

    for idx, filename in enumerate(valid_files, 1):
        src = os.path.join(input_dir, filename)
        dst = os.path.join(input_dir, f"{idx}_{filename}")
        os.rename(src, dst)
        print(f"Renamed {filename} -> {idx}_{filename}")


# Import YouTube downloader components (optional)
def _load_youtube_downloader():
    """Load youtube_audio_downloader module if available"""
    converter_path = Path(__file__).parent / "youtube_audio_downloader.py"
    
    try:
        if not converter_path.exists():
            print("⚠️ youtube_audio_downloader.py not found")
            return None, None
            
        spec = importlib.util.spec_from_file_location("youtube_audio_downloader", converter_path)
        if not spec or not spec.loader:
            print("⚠️ Could not load youtube_audio_downloader module")
            return None, None
            
        converter_module = importlib.util.module_from_spec(spec)
        sys.modules["youtube_audio_downloader"] = converter_module
        spec.loader.exec_module(converter_module)
        
        print("✅ YouTube downloader components loaded successfully")
        return converter_module.Config, converter_module.YoutubeAudioDownloader
        
    except Exception as e:
        print(f"⚠️ Error loading youtube_audio_downloader: {e}")
        return None, None

Config, YoutubeAudioDownloader = _load_youtube_downloader()

class AudioClassifier:
    """Main audio classifier with model caching and language detection capabilities"""
    
    # Class-level shared instances for memory efficiency
    _shared_classifier = None
    _shared_whisper_model = None
    
    def __init__(self, model_name="audeering/wav2vec2-large-robust-24-ft-age-gender", 
                 child_threshold=0.5, age_threshold=0.3):
        """
        Initialize classifier with model and confidence thresholds

        Args:
            model_name: Name of the model on Hugging Face
            child_threshold: Probability threshold for classifying as child
            age_threshold: Age threshold for classifying as child (0.3 ~ 30 years)
        """
        self.classifier = self._get_or_create_classifier(model_name, child_threshold, age_threshold)
    
    def _get_or_create_classifier(self, model_name, child_threshold, age_threshold):
        """Get existing classifier or create new one if parameters differ"""
        if (self._shared_classifier is not None and
            self._shared_classifier.model_name == model_name and
            self._shared_classifier.child_threshold == child_threshold and
            self._shared_classifier.age_threshold == age_threshold):
            print("🔄 Reusing existing model (model already loaded)")
            return self._shared_classifier
        else:
            print("🚀 Loading model for the first time...")
            classifier = BaseAudioClassifier(model_name, child_threshold, age_threshold)
            AudioClassifier._shared_classifier = classifier
            print("✅ Model loaded and cached for future use")
            return classifier
    
    @classmethod
    def clear_model_cache(cls):
        """Clear cached model instances to free memory"""
        if cls._shared_classifier is not None:
            print("🗑️ Clearing audio classifier cache...")
            # Clear CUDA cache if available
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.synchronize()
            cls._shared_classifier = None
            print("✅ Audio classifier cache cleared")
        
        if cls._shared_whisper_model is not None:
            print("🗑️ Clearing Whisper model cache...")
            # Clear CUDA cache if available
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.synchronize()
            cls._shared_whisper_model = None
            print("✅ Whisper model cache cleared")
            
        # Force garbage collection
        import gc
        gc.collect()
        
    @classmethod
    def clear_cuda_memory(cls):
        """Explicitly clear CUDA memory"""
        if torch.cuda.is_available():
            print("🧹 Clearing CUDA memory...")
            torch.cuda.empty_cache()
            torch.cuda.synchronize()
            torch.cuda.reset_peak_memory_stats()
            print(f"✅ CUDA memory cleared. Available: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f}GB")

    def is_child_audio(self, audio_path: str) -> Optional[bool]:
        """
        Determines whether the given .wav audio file contains a child's voice.

        Args:
            audio_path (str): Path to the .wav audio file.

        Returns:
            Optional[bool]: True if the audio is classified as a child's voice, False otherwise.
                            Returns None if an error occurs.
        """
        try:
            # Use the predict method from the base classifier
            age_norm, age_years, gender_probs, status = self.classifier.predict(audio_path)
            
            if status == "error":
                return None
            
            # Use the classify_age_group method to determine if it's a child
            final_label, confidence = self.classifier.classify_age_group(age_norm, gender_probs)
            
            return final_label == "child"
            
        except Exception as e:
            print(f"An error occurred: {e}")
            return None

    def is_child_audio_optimized(self, audio_path: str) -> Optional[bool]:
        """
        OPTIMIZED: Determines whether audio contains child's voice using combined prediction.
        
        Args:
            audio_path (str): Path to the .wav audio file.

        Returns:
            Optional[bool]: True if child voice, False otherwise, None if error.
        """
        try:
            result = self.get_combined_prediction(audio_path)
            if "error" in result:
                return None
            return result.get("is_child", False)
        except Exception as e:
            print(f"An error occurred: {e}")
            return None
    
    def _get_whisper_model(self):
        """Get or load Whisper model for language detection"""
        if AudioClassifier._shared_whisper_model is None:
            # Use environment configuration for model size
            if USE_ENV_CONFIG and config is not None:
                model_size = config.WHISPER_MODEL_SIZE
            else:
                model_size = "tiny"
                
            print(f"🚀 Loading Whisper {model_size} model for language detection...")
            AudioClassifier._shared_whisper_model = whisper.load_model(model_size)
            print("✅ Whisper model loaded and cached")
        else:
            print("🔄 Reusing existing Whisper model")
        return AudioClassifier._shared_whisper_model

    def is_vietnamese(self, audio_path: str) -> Optional[bool]:
        """
        Determines whether the given .wav audio file contains Vietnamese speech.

        Args:
            audio_path (str): Path to the .wav audio file.

        Returns:
            Optional[bool]: True if the audio is classified as Vietnamese, False otherwise.
                            Returns None if an error occurs.
        """
        try:
            whisper_model = self._get_whisper_model()
            
            # Clear CUDA cache before processing
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            
            # Load audio and detect language
            audio = whisper.load_audio(audio_path)
            audio = whisper.pad_or_trim(audio)
            
            # Make log-Mel spectrogram and move to the same device as the model
            mel = whisper.log_mel_spectrogram(audio).to(whisper_model.device)
            
            # Detect the spoken language with proper error handling
            with torch.no_grad():
                try:
                    _, probs = whisper_model.detect_language(mel)
                    
                    # Ensure probs is a dict (as expected by whisper)
                    if isinstance(probs, list) and len(probs) > 0 and isinstance(probs[0], dict):
                        probs = probs[0]
                    
                    if not isinstance(probs, dict):
                        print("⚠️ Language detection failed: probs is not a dict")
                        return None
                    
                    if not probs:
                        print("⚠️ Language detection failed: empty probabilities")
                        return None
                    
                    detected_language, confidence = max(probs.items(), key=lambda x: x[1])
                    print(f"  Detected language: {detected_language} (confidence: {confidence:.3f})")
                    
                    # Clean up GPU memory
                    del mel
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
                    
                    # Return True if Vietnamese is detected with reasonable confidence
                    return detected_language == "vi" and confidence > 0.1
                    
                except torch.cuda.OutOfMemoryError as e:
                    print(f"⚠️ CUDA out of memory during language detection: {e}")
                    # Clear all cached memory and try again
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
                        torch.cuda.synchronize()
                    # Return unknown instead of crashing
                    print("  Detected language: unknown (CUDA memory error)")
                    return None
            
        except Exception as e:
            print(f"⚠️ Language detection error: {e}")
            print("  Detected language: unknown")
            # Clean up on any error
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            return None
    
    def _load_audio_once(self, audio_path: str):
        """Load audio once for both age detection and language detection"""
        try:
            # Load with librosa for age detection (16kHz)
            speech_array, original_sr = librosa.load(audio_path, sr=None)
            if original_sr != 16000:
                speech_array_16k = librosa.resample(speech_array, orig_sr=original_sr, target_sr=16000)
            else:
                speech_array_16k = speech_array.copy()
            
            # Normalize for age detection
            if np.max(np.abs(speech_array_16k)) > 0:
                speech_array_16k = speech_array_16k / np.max(np.abs(speech_array_16k))
            
            # Load with whisper format for language detection
            whisper_audio = whisper.load_audio(audio_path)
            whisper_audio = whisper.pad_or_trim(whisper_audio)
            
            return {
                "age_audio": speech_array_16k.astype(np.float32),
                "whisper_audio": whisper_audio,
                "sample_rate": 16000
            }
        except Exception as e:
            logger.error(f"Error loading audio {audio_path}: {e}")
            return None

    def _predict_age_from_audio_data(self, audio_data):
        """Predict age/gender from pre-loaded audio data with memory management"""
        if audio_data is None:
            return None, None, None, "error"
        
        try:
            speech_array = audio_data["age_audio"]
            sampling_rate = audio_data["sample_rate"]
            
            # Clear GPU cache before processing
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            
            # Process audio
            inputs = self.classifier.processor(speech_array, sampling_rate=sampling_rate)
            input_values = inputs['input_values'][0]
            input_values = input_values.reshape(1, -1)
            input_values = torch.from_numpy(input_values).to(self.classifier.device)
            
            # Prediction with gradient disabled and memory management
            with torch.no_grad():
                try:
                    hidden_states, age_logits, gender_probs = self.classifier.model(input_values)
                    
                    # Age prediction (0-1 scale, 0=0 years, 1=100 years)
                    age_normalized = float(age_logits.squeeze())
                    age_years = age_normalized * 100  # Convert to years
                    
                    # Gender prediction probabilities [female, male, child]
                    gender_probs = gender_probs.squeeze().cpu().numpy()
                    
                    # Clear intermediate tensors
                    del input_values, hidden_states, age_logits
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
                    
                    return age_normalized, age_years, gender_probs, "success"
                    
                except torch.cuda.OutOfMemoryError as e:
                    print(f"⚠️ CUDA out of memory during prediction: {e}")
                    # Clear all cached memory
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
                        torch.cuda.synchronize()
                    return None, None, None, "cuda_error"
                    
        except Exception as e:
            logger.error(f"Error predicting from audio data: {e}")
            # Clean up on any error
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            return None, None, None, "error"

    def _detect_language_from_audio_data(self, audio_data):
        """Detect language from pre-loaded audio data with better error handling"""
        if audio_data is None:
            print("⚠️ No audio data provided for language detection")
            return None
        
        try:
            whisper_model = self._get_whisper_model()
            whisper_audio = audio_data["whisper_audio"]
            
            # Clear GPU cache if using CUDA
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            
            # Make log-Mel spectrogram and move to the same device as the model
            mel = whisper.log_mel_spectrogram(whisper_audio).to(whisper_model.device)
            
            # Detect the spoken language
            with torch.no_grad():
                try:
                    _, probs = whisper_model.detect_language(mel)
                    
                    # Ensure probs is a dict (as expected by whisper)
                    if isinstance(probs, list) and len(probs) > 0 and isinstance(probs[0], dict):
                        probs = probs[0]
                    
                    if not isinstance(probs, dict):
                        print("⚠️ Language detection failed: probs is not a dict")
                        return None
                    
                    if not probs:
                        print("⚠️ Language detection failed: empty probabilities")
                        return None
                    
                    detected_language, confidence = max(probs.items(), key=lambda x: x[1])
                    print(f"  Language detection: {detected_language} (confidence: {confidence:.3f})")
                    
                    # Clear GPU memory after processing
                    del mel
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
                    
                    # Return True if Vietnamese is detected with reasonable confidence
                    return detected_language == "vi" and confidence > 0.1
                    
                except torch.cuda.OutOfMemoryError as e:
                    print(f"⚠️ CUDA out of memory during language detection: {e}")
                    # Clear all cached memory
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
                        torch.cuda.synchronize()
                    return None
            
        except Exception as e:
            print(f"⚠️ Language detection error: {e}")
            # Clean up on any error
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            return None

    def get_combined_prediction(self, audio_path: str) -> dict:
        """
        Get combined prediction with shared audio loading and improved memory management
        
        Args:
            audio_path (str): Path to the .wav audio file.
            
        Returns:
            dict: Combined prediction results with both age/gender and language detection
        """
        try:
            # Load audio once for both predictions
            audio_data = self._load_audio_once(audio_path)
            if audio_data is None:
                return {"error": "Failed to load audio file"}
            
            # Get language detection first (less memory intensive)
            is_vietnamese = self._detect_language_from_audio_data(audio_data)
            
            # Get age/gender prediction from shared audio data
            age_norm, age_years, gender_probs, status = self._predict_age_from_audio_data(audio_data)
            
            if status == "cuda_error":
                return {
                    "error": "CUDA out of memory during processing",
                    "is_vietnamese": is_vietnamese,
                    "suggestion": "Try reducing batch size or using CPU processing"
                }
            elif status == "error":
                return {
                    "error": "Failed to process audio for age detection", 
                    "is_vietnamese": is_vietnamese
                }
            
            # Classify age group
            final_label, confidence = self.classifier.classify_age_group(age_norm, gender_probs)
            
            return {
                "age_normalized": age_norm,
                "age_years": age_years,
                "gender_probabilities": {
                    "female": gender_probs[0] if gender_probs is not None else None,
                    "male": gender_probs[1] if gender_probs is not None else None,
                    "child": gender_probs[2] if gender_probs is not None else None
                },
                "final_label": final_label,
                "confidence": confidence,
                "is_child": final_label == "child",
                "is_vietnamese": is_vietnamese
            }
            
        except Exception as e:
            # Final cleanup
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            return {"error": f"An error occurred: {e}"}

    def get_detailed_prediction(self, audio_path: str) -> dict:
        """
        Get detailed prediction results including age, gender probabilities, classification, and language detection.

        Args:
            audio_path (str): Path to the .wav audio file.

        Returns:
            dict: Detailed prediction results with age, gender probabilities, final classification, and language detection.
        """
        # Use the optimized combined prediction method
        return self.get_combined_prediction(audio_path)


def process_youtube_urls_from_file(txt_file_path: str) -> Dict[str, int]:
    """
    Process a list of YouTube URLs from a text file, convert to audio, and classify each one.
    
    Args:
        txt_file_path (str): Path to the .txt file containing YouTube URLs (one per line)
        
    Returns:
        Dict[str, int]: Summary with counts of children vs non-children audio files
    """
    base_dir = Path(__file__).parent
    file_path = base_dir / txt_file_path
    
    print(f"Reading URLs from: {file_path.resolve()}")
    
    # Validate file existence and read URLs
    try:
        urls = _read_urls_from_file(file_path)
    except Exception as e:
        print(f"Error reading file: {e}")
        return {"error": 1, "children": 0, "non_children": 0}
    
    if not urls:
        print("No URLs found in the file.")
        return {"error": 0, "children": 0, "non_children": 0}
    
    print(f"Found {len(urls)} URLs to process...")
    
    # Initialize components
    try:
        classifier, downloader = _initialize_components()
    except Exception as e:
        print(f"Error initializing components: {e}")
        return {"error": 1, "children": 0, "non_children": 0}
    
    # Process URLs and return results
    return _process_urls(urls, classifier, downloader, base_dir)


def _read_urls_from_file(file_path: Path) -> list:
    """Read and validate URLs from file"""
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        return [line.strip() for line in f if line.strip()]


def _initialize_components():
    """Initialize classifier and downloader components with optional cookie support"""
    if Config is None or YoutubeAudioDownloader is None:
        raise ImportError("YouTube downloader not available. Please ensure youtube_audio_downloader.py is present.")
    
    classifier = AudioClassifier()
    config = Config()
    
    # Check for cookie settings from environment or command line
    cookies_file = None
    cookies_browser = None
    
    # Check environment variables first
    cookies_file = os.getenv('YOUTUBE_COOKIES_FILE')
    cookies_browser = os.getenv('YOUTUBE_COOKIES_BROWSER')
    
    # Check for cookies.txt file in current directory if no environment variable
    if not cookies_file and not cookies_browser:
        if os.path.exists('cookies.txt'):
            cookies_file = 'cookies.txt'
            print("🍪 Found cookies.txt file, using it for YouTube access")
    
    downloader = YoutubeAudioDownloader(config, cookies_file, cookies_browser)
    
    return classifier, downloader


def _process_urls(urls: list, classifier, downloader, base_dir: Path) -> Dict[str, int]:
    """Process each URL and return summary statistics with parallel processing"""
    results = {"children": 0, "non_children": 0, "errors": 0}
    summary_file_path = base_dir / "classification_summary.txt"
    
    # Initialize summary file
    with open(summary_file_path, 'w', encoding='utf-8') as summary_file:
        summary_file.write("URL,Result\n")
    
    # Collect results for batch writing
    results_buffer = []
    
    # Process URLs in parallel with controlled concurrency
    max_workers = min(4, len(urls))  # Limit to 4 concurrent workers
    print(f"Processing {len(urls)} URLs with {max_workers} parallel workers...")
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_url = {
            executor.submit(_process_single_url, url, i, classifier, downloader): (url, i) 
            for i, url in enumerate(urls)
        }
        
        # Process completed tasks
        for future in as_completed(future_to_url):
            url, index = future_to_url[future]
            try:
                result = future.result()
                results[result] += 1
                results_buffer.append(f"{url},{result.title()}\n")
                print(f"✓ Completed URL {index+1}/{len(urls)}: {url} -> {result.title()}")
            except Exception as e:
                print(f"✗ Error processing URL {index+1}/{len(urls)}: {url} -> {e}")
                results["errors"] += 1
                results_buffer.append(f"{url},Error\n")
    
    # Batch write all results to file
    with open(summary_file_path, 'a', encoding='utf-8') as summary_file:
        summary_file.writelines(results_buffer)
    
    _print_final_summary(len(urls), results)
    return {"children": results["children"], "non_children": results["non_children"], "errors": results["errors"]}


def _process_single_url(url: str, index: int, classifier, downloader) -> str:
    """Process a single URL and return classification result with optimized audio loading"""
    try:
        # Download and convert to audio
        print(f"  [{index+1}] Downloading and converting audio from: {url}")
        audio_file_path = downloader.download_audio_from_yturl(url, index=index)
        
        if audio_file_path is None:
            print(f"  [{index+1}] Failed to download/convert audio")
            return "errors"
        
        print(f"  [{index+1}] Audio saved, classifying...")
        
        # Use optimized combined prediction (loads audio only once)
        prediction_result = classifier.get_combined_prediction(audio_file_path)
        
        # Clean up the audio file immediately after processing
        _cleanup_audio_file(audio_file_path)
        
        # Check prediction result
        if "error" in prediction_result:
            print(f"  [{index+1}] Classification failed: {prediction_result['error']}")
            return "errors"
        
        is_child = prediction_result.get("is_child", False)
        is_vietnamese = prediction_result.get("is_vietnamese", False)
        
        if is_child:
            status = "✓ CHILD voice detected"
            if is_vietnamese:
                status += " (Vietnamese)"
            print(f"  [{index+1}] {status}")
            return "children"
        else:
            status = "✗ NON-CHILD voice detected"
            if is_vietnamese:
                status += " (Vietnamese)"
            print(f"  [{index+1}] {status}")
            return "non_children"
            
    except Exception as e:
        print(f"  [{index+1}] Error processing {url}: {e}")
        return "errors"


def _cleanup_audio_file(audio_file_path: str):
    """Clean up temporary audio file"""
    try:
        if os.path.exists(audio_file_path):
            os.remove(audio_file_path)
            print(f"  Cleaned up: {audio_file_path}")
    except Exception as cleanup_error:
        print(f"  Warning: Could not clean up {audio_file_path}: {cleanup_error}")


def _print_final_summary(total_urls: int, results: dict):
    """Print final processing summary"""
    print("\n" + "="*50)
    print("PROCESSING COMPLETE - SUMMARY:")
    print("="*50)
    print(f"Total URLs processed: {total_urls}")
    print(f"Children voices found: {results['children']}")
    print(f"Non-children voices found: {results['non_children']}")
    print(f"Errors/Failed classifications: {results['errors']}")
    success_count = results['children'] + results['non_children']
    success_rate = (success_count / total_urls * 100) if total_urls > 0 else 0
    print(f"Success rate: {success_rate:.1f}%")
    print("="*50)


def test_audio_classifier():
    """
    Test the AudioClassifier with a sample audio file.
    """
    sample_audio_path = Path(__file__).parent / "youtube-audio/children-audio.wav"
    
    print(f"Accessing file at: {Path(sample_audio_path).resolve()}")
    
    if not Path(sample_audio_path).exists():
        print(f"Sample audio file not found: {sample_audio_path}")
        return

    classifier = AudioClassifier()
    result = classifier.is_child_audio(str(sample_audio_path))

    if result is None:
        print("An error occurred during classification.")
    elif result:
        print("The audio contains a child's voice.")
    else:
        print("The audio does not contain a child's voice.")

def main():
    """Main function with interactive menu and command line support"""
    import sys
    
    # Check for command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == "--help" or sys.argv[1] == "-h":
            print("YouTube Children Voice Classifier")
            print("=" * 40)
            print("Usage:")
            print("  python youtube_audio_classifier.py [options]")
            print("")
            print("Options:")
            print("  --cookies-file <path>     Use cookies from Netscape format file")
            print("  --cookies-browser <name>  Use cookies from browser (chrome, firefox, safari, edge, opera, brave)")
            print("  --help, -h               Show this help message")
            print("")
            print("Environment Variables:")
            print("  YOUTUBE_COOKIES_FILE     Path to cookies file")
            print("  YOUTUBE_COOKIES_BROWSER  Browser name for cookies")
            print("")
            print("Examples:")
            print("  python youtube_audio_classifier.py --cookies-browser chrome")
            print("  python youtube_audio_classifier.py --cookies-file cookies.txt")
            return
        
        # Parse cookie arguments
        cookies_file = None
        cookies_browser = None
        
        i = 1
        while i < len(sys.argv):
            if sys.argv[i] == "--cookies-file" and i + 1 < len(sys.argv):
                cookies_file = sys.argv[i + 1]
                i += 2
            elif sys.argv[i] == "--cookies-browser" and i + 1 < len(sys.argv):
                cookies_browser = sys.argv[i + 1]
                i += 2
            else:
                i += 1
        
        # Set environment variables for the downloader
        if cookies_file:
            os.environ['YOUTUBE_COOKIES_FILE'] = cookies_file
        if cookies_browser:
            os.environ['YOUTUBE_COOKIES_BROWSER'] = cookies_browser
    
    print("YouTube Children Voice Classifier")
    print("=" * 40)
    print("Choose an option:")
    print("1. Test with sample audio file")
    print("2. Process YouTube URLs from text file")
    print("3. Clear model cache (free memory)")
    
    choice = input("Enter your choice (1, 2, or 3): ").strip()
    
    if choice == "1":
        test_audio_classifier()
    elif choice == "2":
        txt_file_path = input("Enter the path to the .txt file (relative to this script's parent folder): ").strip()
        if txt_file_path:
            process_youtube_urls_from_file(txt_file_path)
        else:
            print("No file path provided.")
    elif choice == "3":
        AudioClassifier.clear_model_cache()
        print("Model cache cleared. Next classifier creation will reload the model.")
    else:
        print("Invalid choice. Please run the script again and choose 1, 2, or 3.")


if __name__ == "__main__":
    main()

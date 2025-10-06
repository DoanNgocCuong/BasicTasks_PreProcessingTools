#!/usr/bin/env python3
"""
YouTube Audio Classifier with Model Caching and Language Detection

This module provides advanced audio classification capabilities specifically designed for
analyzing YouTube video content. It combines children's voice detection with Vietnamese
language detection, featuring intelligent model caching for optimal performance.

Author: Le Hoang Minh
"""

# @DoanNgocCuong - Embedded exact same logic from AgeDetection.py
import gc
import importlib.util
import logging
import os
import shutil
import sys
import threading
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union, Any

import librosa
import numpy as np
import torch
import torch.nn as nn
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


class ConfigurationURLProcessor:
    """Handles URL file reading and validation."""
    
    @staticmethod
    def read_urls_from_file(file_path: Path) -> List[str]:
        """Read and validate URLs from file."""
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip()]


class ResultSummaryService:
    """Handles result collection and summary reporting."""
    
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.summary_file_path = base_dir / "classification_summary.txt"
    
    def initialize_summary_file(self) -> None:
        """Initialize summary file with headers."""
        with open(self.summary_file_path, 'w', encoding='utf-8') as summary_file:
            summary_file.write("URL,Result\n")
    
    def write_results_batch(self, results_buffer: List[str]) -> None:
        """Write results to file in batch."""
        with open(self.summary_file_path, 'a', encoding='utf-8') as summary_file:
            summary_file.writelines(results_buffer)
    
    @staticmethod
    def print_final_summary(total_urls: int, results: Dict[str, int]) -> None:
        """Print final processing summary."""
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


class DownloaderInitializer:
    """Handles initialization of downloader components."""
    
    def __init__(self, config_class: Optional[Any], downloader_class: Optional[Any]):
        self.config_class = config_class
        self.downloader_class = downloader_class
    
    def initialize_components(self) -> Tuple[Any, Any]:
        """Initialize classifier and downloader components with optional cookie support."""
        if self.config_class is None or self.downloader_class is None:
            raise ImportError("YouTube downloader not available. Please ensure youtube_audio_downloader.py is present.")
        
        classifier = AudioClassifier()
        config = self.config_class()
        
        # Check for cookie settings from environment or command line
        cookies_file = self._get_cookies_file()
        cookies_browser = self._get_cookies_browser()
        
        downloader = self.downloader_class(config, cookies_file, cookies_browser)
        
        return classifier, downloader
    
    def _get_cookies_file(self) -> Optional[str]:
        """Get cookies file from environment or local file."""
        cookies_file = os.getenv('YOUTUBE_COOKIES_FILE')
        
        # Check for cookies.txt file in current directory if no environment variable
        if not cookies_file and os.path.exists('cookies.txt'):
            cookies_file = 'cookies.txt'
            print("🍪 Found cookies.txt file, using it for YouTube access")
        
        return cookies_file
    
    def _get_cookies_browser(self) -> Optional[str]:
        """Get cookies browser from environment."""
        return os.getenv('YOUTUBE_COOKIES_BROWSER')


class CommandLineParser:
    """Handles command line argument parsing."""
    
    @staticmethod
    def parse_cookie_arguments(args: List[str]) -> Tuple[Optional[str], Optional[str]]:
        """Parse cookie arguments from command line."""
        cookies_file = None
        cookies_browser = None
        
        i = 1
        while i < len(args):
            if args[i] == "--cookies-file" and i + 1 < len(args):
                cookies_file = args[i + 1]
                i += 2
            elif args[i] == "--cookies-browser" and i + 1 < len(args):
                cookies_browser = args[i + 1]
                i += 2
            else:
                i += 1
        
        return cookies_file, cookies_browser
    
    @staticmethod
    def show_help() -> None:
        """Show help message."""
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


class Manager:
    """Manages environment configuration and defaults."""
    
    def __init__(self):
        self._load_environment_config()
        self._load_youtube_language_classifier()
    
    def _load_environment_config(self) -> None:
        """Load environment configuration."""
        try:
            from env_config import config
            self.config = config
            self.use_env_config = True
            print("✅ Audio Classifier using environment configuration")
        except ImportError:
            self.config = None
            self.use_env_config = False
            print("⚠️ Environment configuration not available, using defaults")
    
    def _load_youtube_language_classifier(self) -> None:
        """Load YouTube language classifier if available."""
        try:
            from youtube_language_classifier import YouTubeLanguageClassifier
            self.YouTubeLanguageClassifier = YouTubeLanguageClassifier
            self.youtube_transcript_available = True
            print("✅ YouTube Transcript API language detection available")
        except ImportError:
            self.YouTubeLanguageClassifier = None
            self.youtube_transcript_available = False
            print("⚠️ YouTube Transcript API not available, falling back to audio-based detection")
    
    def get_model_config(self, model_name: Optional[str] = None, 
                        child_threshold: Optional[float] = None, 
                        age_threshold: Optional[float] = None) -> Tuple[str, float, float]:
        """Get model configuration with fallback defaults."""
        if self.use_env_config and self.config is not None:
            return (
                model_name or self.config.WAV2VEC2_MODEL,
                child_threshold if child_threshold is not None else self.config.CHILD_THRESHOLD,
                age_threshold if age_threshold is not None else self.config.AGE_THRESHOLD
            )
        else:
            return (
                model_name or "audeering/wav2vec2-large-robust-6-ft-age-gender",
                child_threshold if child_threshold is not None else 0.5,
                age_threshold if age_threshold is not None else 0.3
            )


class ModuleLoader:
    """Handles dynamic loading of YouTube downloader components."""
    
    @staticmethod
    def load_youtube_downloader() -> Tuple[Optional[Any], Optional[Any]]:
        """Load youtube_audio_downloader module if available."""
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


class AudioFileProcessor:
    """Handles audio file processing operations."""
    
    @staticmethod
    def filter_and_rename_files(input_dir: str = "input") -> None:
        """Filter out short audio files and rename remaining files with sequential numbering.
        
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
    
    @staticmethod
    def cleanup_audio_file(audio_file_path: str) -> None:
        """Clean up temporary audio file."""
        try:
            if os.path.exists(audio_file_path):
                os.remove(audio_file_path)
                print(f"  Cleaned up: {audio_file_path}")
        except Exception as cleanup_error:
            print(f"  Warning: Could not clean up {audio_file_path}: {cleanup_error}")


class MemoryManager:
    """Handles CUDA memory management operations."""
    
    @staticmethod
    def clear_cuda_cache() -> None:
        """Clear CUDA cache if available."""
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.synchronize()
    
    @staticmethod
    def clear_cuda_memory_verbose() -> None:
        """Explicitly clear CUDA memory with verbose output."""
        if torch.cuda.is_available():
            print("🧹 Clearing CUDA memory...")
            torch.cuda.empty_cache()
            torch.cuda.synchronize()
            torch.cuda.reset_peak_memory_stats()
            print(f"✅ CUDA memory cleared. Available: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f}GB")
    
    @staticmethod
    def force_garbage_collection() -> None:
        """Force garbage collection."""
        gc.collect()
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
    
    def __init__(self, model_name: Optional[str] = None, child_threshold: Optional[float] = None, age_threshold: Optional[float] = None):
        """
        Initialize classifier with model and confidence thresholds
        
        Args:
            model_name: Model name on Hugging Face (uses env config if None)
            child_threshold: Probability threshold for classifying as child (uses env config if None)
            age_threshold: Age threshold for classifying as child (uses env config if None)
        """
        # Get configuration
        config_manager = ConfigurationManager()
        self.model_name, self.child_threshold, self.age_threshold = config_manager.get_model_config(
            model_name, child_threshold, age_threshold
        )
        
        print(f"🔧 Using configuration:")
        print(f"  Model: {self.model_name}")
        print(f"  Child threshold: {self.child_threshold}")  
        print(f"  Age threshold: {self.age_threshold}")
            
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        logger.info(f"Using device: {self.device}")
        logger.info(f"Model: {self.model_name}")
        logger.info(f"Child threshold: {self.child_threshold}")
        logger.info(f"Age threshold: {self.age_threshold}")
        
        # Clear CUDA cache before loading models
        MemoryManager.clear_cuda_cache()
        
        # Load model and processor with memory optimizations
        self._load_model_and_processor()
        
        # Labels: [female, male, child]
        self.gender_labels = ['female', 'male', 'child']
    
    def _load_model_and_processor(self) -> None:
        """Load model and processor with memory optimizations."""
        try:
            logger.info("Loading model...")
            print(f"🔍 DEBUG: Attempting to load model: {self.model_name}")
            self.processor = Wav2Vec2Processor.from_pretrained(self.model_name)  # type: ignore
            print("✅ DEBUG: Processor loaded successfully")
            
            # Load model with optimized settings
            print(f"🔍 DEBUG: Loading actual model: {self.model_name}")
            self.model = AgeGenderModel.from_pretrained(self.model_name)  # type: ignore
            print("✅ DEBUG: Model loaded successfully")
            self.model = self.model.to(self.device)
            
            # Enable memory-efficient mode
            self.model.eval()
            if torch.cuda.is_available():
                # Enable gradient checkpointing for memory efficiency
                if hasattr(self.model, 'gradient_checkpointing_enable'):
                    self.model.gradient_checkpointing_enable()
                    
                # Try to compile model for better memory usage (PyTorch 2.0+) - but handle triton errors
                if hasattr(torch, 'compile'):
                    try:
                        self.model = torch.compile(self.model, mode='reduce-overhead', backend='aot_eager')
                        logger.info("Model compiled for better performance")
                    except Exception as compile_e:
                        logger.warning(f"Could not compile model (triton issue): {compile_e}")
                        # Continue without compilation - this is not critical
                        pass
                        
            logger.info("Model loaded successfully!")
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            MemoryManager.clear_cuda_cache()
            raise
    def preprocess_audio(self, audio_path: str, target_sr: int = 16000) -> Tuple[Optional[np.ndarray], Optional[int]]:
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
    
    def predict(self, audio_path: str) -> Tuple[Optional[float], Optional[float], Optional[np.ndarray], str]:
        """
        Predict age and gender for audio file
        """
        # Clear CUDA cache before processing
        MemoryManager.clear_cuda_cache()
            
        speech_array, sampling_rate = self.preprocess_audio(audio_path)
        if speech_array is None:
            return None, None, None, "error"
        
        try:
            # Process audio
            inputs = self.processor(speech_array, sampling_rate=sampling_rate)
            input_values = inputs['input_values'][0]
            input_values = input_values.reshape(1, -1)
            
            # Move to device with memory optimization
            input_values = torch.from_numpy(input_values)
            if torch.cuda.is_available():
                # Use non_blocking for better memory efficiency
                input_values = input_values.to(self.device, non_blocking=True)
            else:
                input_values = input_values.to(self.device)
            
            # Prediction with memory efficiency
            with torch.no_grad():
                with torch.cuda.amp.autocast() if torch.cuda.is_available() else torch.no_grad():
                    hidden_states, age_logits, gender_probs = self.model(input_values)
                    
                    # Age prediction (0-1 scale, 0=0 years, 1=100 years)
                    age_normalized = float(age_logits.squeeze().cpu())
                    age_years = age_normalized * 100  # Convert to years
                    
                    # Gender prediction probabilities [female, male, child]
                    gender_probs = gender_probs.squeeze().cpu().numpy()
                    
                    # Clear intermediate tensors
                    del input_values, hidden_states, age_logits
                    MemoryManager.clear_cuda_cache()
                    
                    return age_normalized, age_years, gender_probs, "success"
                
        except Exception as e:
            logger.error(f"Error predicting for {audio_path}: {e}")
            # Clear cache on error
            MemoryManager.clear_cuda_cache()
            return None, None, None, "error"
    
    def classify_age_group(self, age_normalized: Optional[float], gender_probs: Optional[np.ndarray]) -> Tuple[str, float]:
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


class BatchProcessingService:
    """Handles batch processing of URLs with parallel execution."""
    
    def __init__(self, classifier: Any, downloader: Any, base_dir: Path):
        self.classifier = classifier
        self.downloader = downloader
        self.summary_service = ResultSummaryService(base_dir)
    
    def process_urls(self, urls: List[str]) -> Dict[str, int]:
        """Process each URL and return summary statistics with parallel processing."""
        results = {"children": 0, "non_children": 0, "errors": 0}
        
        # Initialize summary file
        self.summary_service.initialize_summary_file()
        
        # Collect results for batch writing
        results_buffer = []
        
        # Process URLs in parallel with controlled concurrency
        max_workers = min(4, len(urls))  # Limit to 4 concurrent workers
        print(f"Processing {len(urls)} URLs with {max_workers} parallel workers...")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_url = {
                executor.submit(self._process_single_url, url, i): (url, i) 
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
        self.summary_service.write_results_batch(results_buffer)
        
        ResultSummaryService.print_final_summary(len(urls), results)
        return {"children": results["children"], "non_children": results["non_children"], "errors": results["errors"]}
    
    def _process_single_url(self, url: str, index: int) -> str:
        """Process a single URL and return classification result with optimized audio loading."""
        try:
            # Download and convert to audio
            print(f"  [{index+1}] Downloading and converting audio from: {url}")
            audio_file_path = self.downloader.download_audio_from_yturl(url, index=index)
            
            if audio_file_path is None:
                print(f"  [{index+1}] Failed to download/convert audio")
                return "errors"
            
            print(f"  [{index+1}] Audio saved, classifying...")
            
            # Use optimized combined prediction (loads audio only once)
            # Pass YouTube URL for transcript-based language detection
            prediction_result = self.classifier.get_combined_prediction(audio_file_path, youtube_url=url)
            
            # Clean up the audio file immediately after processing
            AudioFileProcessor.cleanup_audio_file(audio_file_path)
            
            # Check prediction result
            if "error" in prediction_result:
                print(f"  [{index+1}] Classification failed: {prediction_result['error']}")
                return "errors"
            
            return self._classify_result(prediction_result, index)
            
        except Exception as e:
            print(f"  [{index+1}] Error processing {url}: {e}")
            return "errors"
    
    def _classify_result(self, prediction_result: Dict[str, Any], index: int) -> str:
        """Classify the prediction result."""
        is_child = prediction_result.get("is_child", False)
        is_vietnamese = prediction_result.get("is_vietnamese", False)
        was_skipped = prediction_result.get("skipped_age_detection", False)
        
        # Handle case where age detection was skipped for non-Vietnamese audio
        if was_skipped:
            print(f"  [{index+1}] ⏩ SKIPPED - Not Vietnamese audio, classified as non-child")
            return "non_children"
        
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


# Utility functions from utils_remove1s_indexing.py
def filter_and_rename(input_dir="input"):
    """Filter out short audio files and rename remaining files with sequential numbering.
    
    This is a backward compatibility wrapper for AudioFileProcessor.filter_and_rename_files()
    """
    AudioFileProcessor.filter_and_rename_files(input_dir)


# Import YouTube downloader components (optional)
Config, YoutubeAudioDownloader = ModuleLoader.load_youtube_downloader()


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


class AudioClassifier:
    """Main audio classifier with model caching and language detection capabilities"""
    
    # Class-level shared instances for memory efficiency
    _shared_classifier: Optional['BaseAudioClassifier'] = None
    _shared_youtube_classifier: Optional[Any] = None
    _lock = threading.Lock()  # Thread safety for shared instances
    _config_manager = ConfigurationManager()
    
    def __init__(self, model_name: Optional[str] = None, child_threshold: Optional[float] = None, age_threshold: Optional[float] = None):
        """
        Initialize classifier with model and confidence thresholds

        Args:
            model_name: Name of the model on Hugging Face (uses env config if None)
            child_threshold: Probability threshold for classifying as child (uses env config if None)
            age_threshold: Age threshold for classifying as child (uses env config if None)
        """
        # Get configuration from the configuration manager
        resolved_model_name, resolved_child_threshold, resolved_age_threshold = self._config_manager.get_model_config(
            model_name, child_threshold, age_threshold
        )
            
        self.classifier = self._get_or_create_classifier(resolved_model_name, resolved_child_threshold, resolved_age_threshold)
    
    def _get_or_create_classifier(self, model_name: str, child_threshold: float, age_threshold: float) -> 'BaseAudioClassifier':
        """Get existing classifier or create new one if parameters differ (thread-safe)"""
        with AudioClassifier._lock:
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
    def clear_model_cache(cls) -> None:
        """Clear cached model instances to free memory (thread-safe)"""
        with cls._lock:
            if cls._shared_classifier is not None:
                print("🗑️ Clearing audio classifier cache...")
                # Clear CUDA cache if available
                MemoryManager.clear_cuda_cache()
                cls._shared_classifier = None
                print("✅ Audio classifier cache cleared")
            
            if cls._shared_youtube_classifier is not None:
                print("🗑️ Clearing YouTube language classifier cache...")
                cls._shared_youtube_classifier = None
                print("✅ YouTube language classifier cache cleared")
                
            # Force garbage collection
            MemoryManager.force_garbage_collection()
        
    @classmethod
    def clear_cuda_memory(cls) -> None:
        """Explicitly clear CUDA memory"""
        MemoryManager.clear_cuda_memory_verbose()

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
    
    
    def _get_youtube_classifier(self) -> Optional[Any]:
        """Get or create YouTube language classifier instance (thread-safe)"""
        if not self._config_manager.youtube_transcript_available:
            return None
            
        with AudioClassifier._lock:
            if AudioClassifier._shared_youtube_classifier is None:
                print("🚀 Initializing YouTube Transcript API language classifier...")
                AudioClassifier._shared_youtube_classifier = self._config_manager.YouTubeLanguageClassifier()  # type: ignore
                print("✅ YouTube language classifier initialized")
            else:
                print("🔄 Reusing existing YouTube language classifier")
            return AudioClassifier._shared_youtube_classifier

    
    def is_vietnamese_from_youtube_url(self, youtube_url: str) -> bool:
        """
        Determines whether a YouTube video is in Vietnamese using transcript API.
        This is faster and more reliable than audio-based detection for YouTube content.
        When transcripts are not available, assumes the video is Vietnamese.

        Args:
            youtube_url (str): YouTube video URL

        Returns:
            bool: True if the video is Vietnamese or if transcript detection fails, False otherwise.
        """
        youtube_classifier = self._get_youtube_classifier()
        if not youtube_classifier:
            print("⚠️ YouTube transcript API not available, assuming video is Vietnamese")
            return True
        
        try:
            result = youtube_classifier.detect_language_from_url(youtube_url)
            
            if result['error']:
                print(f"⚠️ YouTube transcript detection failed: {result['error']}")
                print("  Assuming video is Vietnamese")
                return True
            
            detected_language = result['detected_language']
            is_vietnamese = result['is_vietnamese']
            confidence = result['confidence']
            
            print(f"  📄 Transcript detected language: {detected_language} (confidence: {confidence:.3f})")
            
            return is_vietnamese
            
        except Exception as e:
            print(f"⚠️ YouTube transcript detection error: {e}")
            print("  Assuming video is Vietnamese")
            return True
    
    def _load_audio_once(self, audio_path: str) -> Optional[Dict[str, Any]]:
        """Load audio for age detection only (language detection now uses transcripts)"""
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
            
            return {
                "age_audio": speech_array_16k.astype(np.float32),
                "sample_rate": 16000
            }
        except Exception as e:
            logger.error(f"Error loading audio {audio_path}: {e}")
            return None

    def _predict_age_from_audio_data(self, audio_data: Optional[Dict[str, Any]]) -> Tuple[Optional[float], Optional[float], Optional[np.ndarray], str]:
        """Predict age/gender from pre-loaded audio data with memory management"""
        if audio_data is None:
            return None, None, None, "error"
        
        try:
            speech_array = audio_data["age_audio"]
            sampling_rate = audio_data["sample_rate"]
            
            # Clear GPU cache before processing
            MemoryManager.clear_cuda_cache()
            
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
                    MemoryManager.clear_cuda_cache()
                    
                    return age_normalized, age_years, gender_probs, "success"
                    
                except torch.cuda.OutOfMemoryError as e:
                    print(f"⚠️ CUDA out of memory during prediction: {e}")
                    # Clear all cached memory
                    MemoryManager.clear_cuda_cache()
                    return None, None, None, "cuda_error"
                except Exception as model_e:
                    # Handle Triton and other model-specific errors
                    error_msg = str(model_e)
                    if "triton" in error_msg.lower():
                        print(f"⚠️ Triton compilation error (non-critical): {model_e}")
                        print("  Continuing without model compilation optimization...")
                    else:
                        print(f"⚠️ Model inference error: {model_e}")
                    
                    # Clean up and continue
                    MemoryManager.clear_cuda_cache()
                    return None, None, None, "model_error"
                    
        except Exception as e:
            logger.error(f"Error predicting from audio data: {e}")
            # Clean up on any error
            MemoryManager.clear_cuda_cache()
            return None, None, None, "error"


    def get_combined_prediction(self, audio_path: str, youtube_url: Optional[str] = None) -> dict:
        """
        Get combined prediction with shared audio loading.
        Uses YouTube transcript API for language detection when available.
        For non-YouTube content, assumes Vietnamese language.
        
        Args:
            audio_path (str): Path to the .wav audio file.
            youtube_url (Optional[str]): YouTube URL for transcript-based language detection.
            
        Returns:
            dict: Combined prediction results with both age/gender and language detection
        """
        try:
            # Load audio once for age detection
            audio_data = self._load_audio_once(audio_path)
            if audio_data is None:
                return {"error": "Failed to load audio file"}
            
            # Get language detection using transcript API for YouTube content
            if youtube_url:
                print("🚀 Using transcript-based language detection...")
                is_vietnamese = self.is_vietnamese_from_youtube_url(youtube_url)
            else:
                print("⚠️  No YouTube URL provided - assuming content is Vietnamese")
                print("   For YouTube videos, provide youtube_url parameter for accurate language detection")
                is_vietnamese = True  # Assume Vietnamese for non-YouTube content
            
            # Skip age detection if not Vietnamese - performance optimization
            if not is_vietnamese:
                print("  ⏩ Skipping age detection - not Vietnamese")
                return {
                    "age_normalized": None,
                    "age_years": None,
                    "gender_probabilities": {
                        "female": None,
                        "male": None,
                        "child": None
                    },
                    "final_label": "adult",  # Default to adult for non-Vietnamese
                    "confidence": 0.0,
                    "is_child": False,
                    "is_vietnamese": False,
                    "skipped_age_detection": True
                }
            
            # Get age/gender prediction from shared audio data (only for Vietnamese)
            age_norm, age_years, gender_probs, status = self._predict_age_from_audio_data(audio_data)
            
            if status == "cuda_error":
                print("  ⚠️ CUDA memory error in age detection - continuing with language detection only")
                return {
                    "age_normalized": None,
                    "age_years": None,
                    "gender_probabilities": {
                        "female": None,
                        "male": None,
                        "child": None
                    },
                    "final_label": "unknown",  # Can't determine age due to CUDA error
                    "confidence": 0.0,
                    "is_child": None,
                    "is_vietnamese": is_vietnamese,
                    "age_detection_failed": "cuda_error"
                }
            elif status == "error" or status == "model_error":
                print("  ⚠️ Age detection failed - continuing with language detection only") 
                return {
                    "age_normalized": None,
                    "age_years": None,
                    "gender_probabilities": {
                        "female": None,
                        "male": None,
                        "child": None
                    },
                    "final_label": "unknown",  # Can't determine age due to error
                    "confidence": 0.0,
                    "is_child": None,
                    "is_vietnamese": is_vietnamese,
                    "age_detection_failed": status
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
        urls = ConfigurationURLProcessor.read_urls_from_file(file_path)
    except Exception as e:
        print(f"Error reading file: {e}")
        return {"error": 1, "children": 0, "non_children": 0}
    
    if not urls:
        print("No URLs found in the file.")
        return {"error": 0, "children": 0, "non_children": 0}
    
    print(f"Found {len(urls)} URLs to process...")
    
    # Initialize components
    try:
        downloader_init = DownloaderInitializer(Config, YoutubeAudioDownloader)
        classifier, downloader = downloader_init.initialize_components()
    except Exception as e:
        print(f"Error initializing components: {e}")
        return {"error": 1, "children": 0, "non_children": 0}
    
    # Process URLs and return results
    batch_processor = BatchProcessingService(classifier, downloader, base_dir)
    return batch_processor.process_urls(urls)


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
            CommandLineParser.show_help()
            return
        
        # Parse cookie arguments
        cookies_file, cookies_browser = CommandLineParser.parse_cookie_arguments(sys.argv)
        
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

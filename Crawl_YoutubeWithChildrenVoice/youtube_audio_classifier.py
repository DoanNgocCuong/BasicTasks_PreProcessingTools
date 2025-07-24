#!/usr/bin/env python3
"""
YouTube Audio Classifier with Model Caching and Language Detection

This module provides advanced audio classification capabilities specifically designed for
analyzing YouTube video content. It combines children's voice detection with Vietnamese
language detection, featuring intelligent model caching for optimal performance.

Key Features:
    - Children's voice detection using pre-trained age/gender classification models
    - Vietnamese language detection using OpenAI Whisper models
    - Intelligent model caching to prevent repeated downloads and loading
    - Dual-analysis workflow optimized for YouTube content processing
    - Batch processing capabilities for URL collections
    - Comprehensive error handling and logging
    - Memory management with manual cache clearing options

Machine Learning Models:
    - Age/Gender Classification: audeering/wav2vec2-large-robust-24-ft-age-gender
    - Language Detection: OpenAI Whisper (configurable model size)
    - Model caching: Shared instances across multiple classifier objects

Architecture:
    - AudioClassifier: Main classification engine with caching
    - Model Management: Automatic loading, caching, and memory management
    - Integration Layer: Seamless connection with youtube_audio_downloader

Classification Pipeline:
    1. Audio preprocessing and validation
    2. Language detection using Whisper models
    3. Age/gender classification using wav2vec2 models
    4. Confidence scoring and threshold application
    5. Combined result aggregation and reporting

Caching System:
    - Class-level model sharing across instances
    - Parameter-based cache validation
    - Memory-efficient model reuse
    - Manual cache clearing for memory management

Output Formats:
    - Boolean results for quick decision making
    - Detailed prediction dictionaries with confidence scores
    - Batch processing summaries with statistics

Use Cases:
    - Content moderation for child-appropriate material
    - Dataset curation for Vietnamese children's content
    - Audio content analysis and classification
    - Research applications in child speech recognition
    - Educational content filtering and organization

Dependencies:
    - transformers: For age/gender classification models
    - whisper: For language detection
    - torch: For neural network inference
    - librosa: For audio preprocessing

Performance Optimizations:
    - Model caching prevents repeated loading
    - Batch processing reduces overhead
    - Efficient memory management
    - Configurable confidence thresholds

Usage:
    python youtube_audio_classifier.py
    
    Options:
    1. Test with sample audio file
    2. Process YouTube URLs from text file  
    3. Clear model cache

    As a module:
    from youtube_audio_classifier import AudioClassifier
    
    classifier = AudioClassifier()
    is_child = classifier.is_child_audio("path/to/audio.wav")
    is_vietnamese = classifier.is_vietnamese("path/to/audio.wav")

Author: Le Hoang Minh
Created: 2025
Version: 1.0
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

import torch
import torch.nn as nn
import librosa
import numpy as np
import whisper
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
    
    def __init__(self, model_name="audeering/wav2vec2-large-robust-24-ft-age-gender", 
                 child_threshold=0.5, age_threshold=0.3):
        """
        Initialize classifier with model and confidence thresholds
        
        Args:
            model_name: Model name on Hugging Face
            child_threshold: Probability threshold for classifying as child
            age_threshold: Age threshold for classifying as child (0.3 ~ 30 years)
        """
        self.model_name = model_name
        self.child_threshold = child_threshold
        self.age_threshold = age_threshold
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        logger.info(f"Using device: {self.device}")
        
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
            cls._shared_classifier = None
            print("✅ Audio classifier cache cleared")
        
        if cls._shared_whisper_model is not None:
            print("🗑️ Clearing Whisper model cache...")
            cls._shared_whisper_model = None
            print("✅ Whisper model cache cleared")

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
    
    def _get_whisper_model(self):
        """Get or load Whisper model for language detection"""
        if AudioClassifier._shared_whisper_model is None:
            print("🚀 Loading Whisper tiny model for language detection...")
            AudioClassifier._shared_whisper_model = whisper.load_model("tiny")
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
            
            # Load audio and detect language
            audio = whisper.load_audio(audio_path)
            audio = whisper.pad_or_trim(audio)
            
            # Make log-Mel spectrogram and move to the same device as the model
            mel = whisper.log_mel_spectrogram(audio).to(whisper_model.device)
            
            # Detect the spoken language
            _, probs = whisper_model.detect_language(mel)
            
            # Ensure probs is a dict (as expected by whisper)
            if isinstance(probs, list) and len(probs) > 0 and isinstance(probs[0], dict):
                probs = probs[0]
            
            if not isinstance(probs, dict):
                print("Language detection failed: probs is not a dict")
                return None
            
            detected_language, confidence = max(probs.items(), key=lambda x: x[1])
            print(f"  Language detection: {detected_language} (confidence: {confidence:.3f})")
            
            # Return True if Vietnamese is detected with reasonable confidence
            return detected_language == "vi" and confidence > 0.1
            
        except Exception as e:
            print(f"Language detection error: {e}")
            return None
    
    def get_detailed_prediction(self, audio_path: str) -> dict:
        """
        Get detailed prediction results including age, gender probabilities, classification, and language detection.

        Args:
            audio_path (str): Path to the .wav audio file.

        Returns:
            dict: Detailed prediction results with age, gender probabilities, final classification, and language detection.
        """
        try:
            age_norm, age_years, gender_probs, status = self.classifier.predict(audio_path)

            if status == "error":
                return {"error": "Failed to process audio file"}

            final_label, confidence = self.classifier.classify_age_group(age_norm, gender_probs)
            is_vietnamese = self.is_vietnamese(audio_path)

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
            return {"error": f"An error occurred: {e}"}


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
    """Initialize classifier and downloader components"""
    if Config is None or YoutubeAudioDownloader is None:
        raise ImportError("YouTube downloader not available. Please ensure youtube_audio_downloader.py is present.")
    
    classifier = AudioClassifier()
    config = Config()
    downloader = YoutubeAudioDownloader(config)
    
    return classifier, downloader


def _process_urls(urls: list, classifier, downloader, base_dir: Path) -> Dict[str, int]:
    """Process each URL and return summary statistics"""
    results = {"children": 0, "non_children": 0, "errors": 0}
    summary_file_path = base_dir / "classification_summary.txt"
    
    # Initialize summary file
    with open(summary_file_path, 'w', encoding='utf-8') as summary_file:
        summary_file.write("URL,Result\n")
    
    # Process each URL
    for i, url in enumerate(urls):
        print(f"\nProcessing URL {i+1}/{len(urls)}: {url}")
        result = _process_single_url(url, i, classifier, downloader)
        
        # Update results and log to file
        results[result] += 1
        with open(summary_file_path, 'a', encoding='utf-8') as summary_file:
            summary_file.write(f"{url},{result.title()}\n")
    
    _print_final_summary(len(urls), results)
    return {"children": results["children"], "non_children": results["non_children"], "errors": results["errors"]}


def _process_single_url(url: str, index: int, classifier, downloader) -> str:
    """Process a single URL and return classification result"""
    try:
        # Download and convert to audio
        print(f"  Downloading and converting audio...")
        audio_file_path = downloader.download_audio_from_yturl(url, index=index)
        
        if audio_file_path is None:
            print(f"  Failed to download/convert audio from: {url}")
            return "errors"
        
        print(f"  Audio saved to: {audio_file_path}")
        
        # Classify the audio
        print(f"  Classifying audio...")
        is_child = classifier.is_child_audio(audio_file_path)
        
        # Clean up the audio file
        _cleanup_audio_file(audio_file_path)
        
        if is_child is None:
            print(f"  Classification failed")
            return "errors"
        elif is_child:
            print(f"  ✓ CHILD voice detected")
            return "children"
        else:
            print(f"  ✗ NON-CHILD voice detected")
            return "non_children"
            
    except Exception as e:
        print(f"  Error processing {url}: {e}")
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
    """Main function with interactive menu"""
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

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
    - Dynamic import of AgeDetection module

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

import sys
import os
import whisper
import importlib.util
from pathlib import Path
from typing import Optional, List, Dict

# Import the AudioClassifier from AgeDetection.py using dynamic import
# (Required because folder name starts with numbers, which can't be imported directly)
age_detection_path = Path(__file__).parent.parent / "19_AudioClassificationAndFiltering_20250623"
age_detection_file = age_detection_path / "AgeDetection.py"

if age_detection_file.exists():
    spec = importlib.util.spec_from_file_location("AgeDetection", age_detection_file)
    if spec and spec.loader:
        age_detection_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(age_detection_module)
        BaseAudioClassifier = age_detection_module.AudioClassifier
    else:
        raise ImportError(f"Could not load AgeDetection module from {age_detection_file}")
else:
    raise ImportError(f"AgeDetection.py not found at {age_detection_file}")

# Import the classes from youtube_audio_downloader.py
converter_path = Path(__file__).parent / "youtube_audio_downloader.py"
if converter_path.exists():
    spec = importlib.util.spec_from_file_location("youtube_audio_downloader", converter_path)
    if spec and spec.loader:
        converter_module = importlib.util.module_from_spec(spec)
        sys.modules["youtube_audio_downloader"] = converter_module
        spec.loader.exec_module(converter_module)
        Config = converter_module.Config
        YoutubeAudioDownloader = converter_module.YoutubeAudioDownloader
    else:
        raise ImportError(f"Could not load youtube_audio_downloader module from {converter_path}")
else:
    raise ImportError(f"youtube_audio_downloader.py not found at {converter_path}")

class AudioClassifier:
    # Class-level variable to store the shared model instance
    _shared_classifier = None
    # Class-level variable to store the shared Whisper model for language detection
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
        # Use shared classifier if it exists and has the same parameters
        if (AudioClassifier._shared_classifier is not None and
            AudioClassifier._shared_classifier.model_name == model_name and
            AudioClassifier._shared_classifier.child_threshold == child_threshold and
            AudioClassifier._shared_classifier.age_threshold == age_threshold):
            print("🔄 Reusing existing model (model already loaded)")
            self.classifier = AudioClassifier._shared_classifier
        else:
            # Create new classifier and store it as shared instance
            print("🚀 Loading model for the first time...")
            self.classifier = BaseAudioClassifier(
                model_name=model_name,
                child_threshold=child_threshold,
                age_threshold=age_threshold
            )
            AudioClassifier._shared_classifier = self.classifier
            print("✅ Model loaded and cached for future use")
    
    @classmethod
    def clear_model_cache(cls):
        """
        Clear the cached model instance. Use this if you want to force reload the model
        with different parameters or if you encounter memory issues.
        """
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
            # Load Whisper model for language detection if not already loaded
            if AudioClassifier._shared_whisper_model is None:
                print("🚀 Loading Whisper tiny model for language detection...")
                AudioClassifier._shared_whisper_model = whisper.load_model("tiny")
                print("✅ Whisper model loaded and cached")
            else:
                print("🔄 Reusing existing Whisper model")
            
            # Load audio and detect language
            audio = whisper.load_audio(audio_path)
            audio = whisper.pad_or_trim(audio)
            
            # Make log-Mel spectrogram and move to the same device as the model
            mel = whisper.log_mel_spectrogram(audio).to(AudioClassifier._shared_whisper_model.device)
            
            # Detect the spoken language
            _, probs = AudioClassifier._shared_whisper_model.detect_language(mel)
            # Ensure probs is a dict (as expected by whisper)
            if isinstance(probs, list) and len(probs) > 0 and isinstance(probs[0], dict):
                probs = probs[0]
            if isinstance(probs, dict):
                detected_language, confidence = max(probs.items(), key=lambda x: x[1])
            else:
                print("Language detection failed: probs is not a dict")
                return None
            
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

            # Call is_vietnamese to detect if the audio is in Vietnamese
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
    # Resolve the file path relative to this script's parent folder
    base_dir = Path(__file__).parent
    file_path = base_dir / txt_file_path
    
    print(f"Reading URLs from: {file_path.resolve()}")
    
    # Check if the file exists
    if not file_path.exists():
        print(f"File not found: {file_path}")
        return {"error": 1, "children": 0, "non_children": 0}
    
    # Read URLs from the file
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            urls = [line.strip() for line in f if line.strip()]
    except Exception as e:
        print(f"Error reading file: {e}")
        return {"error": 1, "children": 0, "non_children": 0}
    
    if not urls:
        print("No URLs found in the file.")
        return {"error": 0, "children": 0, "non_children": 0}
    
    print(f"Found {len(urls)} URLs to process...")
    
    # Initialize classifier, downloader, and counters
    classifier = AudioClassifier()
    config = Config()
    downloader = YoutubeAudioDownloader(config)
    results = {"children": 0, "non_children": 0, "errors": 0}
    
    # Summary file path
    summary_file_path = base_dir / "classification_summary.txt"
    
    # Write initial summary to file
    with open(summary_file_path, 'w', encoding='utf-8') as summary_file:
        summary_file.write("URL,Result\n")
    
    # Process each URL
    for i, url in enumerate(urls):
        print(f"\nProcessing URL {i+1}/{len(urls)}: {url}")
        
        try:
            # Download and convert to audio
            print(f"  Downloading and converting audio...")
            audio_file_path = downloader.download_audio_from_yturl(url, index=i)
            
            if audio_file_path is None:
                print(f"  Failed to download/convert audio from: {url}")
                results["errors"] += 1
                with open(summary_file_path, 'a', encoding='utf-8') as summary_file:
                    summary_file.write(f"{url},Error\n")
                continue
            
            print(f"  Audio saved to: {audio_file_path}")
            
            # Classify the audio
            print(f"  Classifying audio...")
            is_child = classifier.is_child_audio(audio_file_path)
            
            if is_child is None:
                print(f"  Classification failed for: {audio_file_path}")
                results["errors"] += 1
                with open(summary_file_path, 'a', encoding='utf-8') as summary_file:
                    summary_file.write(f"{url},Error\n")
            elif is_child:
                print(f"  ✓ CHILD voice detected")
                results["children"] += 1
                with open(summary_file_path, 'a', encoding='utf-8') as summary_file:
                    summary_file.write(f"{url},Child\n")
            else:
                print(f"  ✗ NON-CHILD voice detected")
                results["non_children"] += 1
                with open(summary_file_path, 'a', encoding='utf-8') as summary_file:
                    summary_file.write(f"{url},Non-Child\n")
            
            # Clean up the audio file after classification
            try:
                if os.path.exists(audio_file_path):
                    os.remove(audio_file_path)
                    print(f"  Cleaned up: {audio_file_path}")
            except Exception as cleanup_error:
                print(f"  Warning: Could not clean up {audio_file_path}: {cleanup_error}")
                
        except Exception as e:
            print(f"  Error processing {url}: {e}")
            results["errors"] += 1
            with open(summary_file_path, 'a', encoding='utf-8') as summary_file:
                summary_file.write(f"{url},Error\n")
    
    # Print final summary
    print("\n" + "="*50)
    print("PROCESSING COMPLETE - SUMMARY:")
    print("="*50)
    print(f"Total URLs processed: {len(urls)}")
    print(f"Children voices found: {results['children']}")
    print(f"Non-children voices found: {results['non_children']}")
    print(f"Errors/Failed classifications: {results['errors']}")
    print(f"Success rate: {((results['children'] + results['non_children']) / len(urls) * 100):.1f}%")
    print("="*50)
    
    return {
        "children": results["children"],
        "non_children": results["non_children"],
        "errors": results["errors"]
    }

def test_audio_classifier():
    """
    Test the AudioClassifier with a sample audio file.
    """
    sample_audio_path = Path(__file__).parent / "youtube-audio/children-audio.wav"  # Path relative to the parent folder
    
    # Print the absolute path being accessed
    print(f"Accessing file at: {Path(sample_audio_path).resolve()}")
    
    # Check if the sample audio file exists
    if not Path(sample_audio_path).exists():
        print(f"Sample audio file not found: {sample_audio_path}")
        return

    # Initialize the classifier
    classifier = AudioClassifier()

    # Test the classifier
    result = classifier.is_child_audio(str(sample_audio_path))

    if result is None:
        print("An error occurred during classification.")
    elif result:
        print("The audio contains a child's voice.")
    else:
        print("The audio does not contain a child's voice.")

if __name__ == "__main__":
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

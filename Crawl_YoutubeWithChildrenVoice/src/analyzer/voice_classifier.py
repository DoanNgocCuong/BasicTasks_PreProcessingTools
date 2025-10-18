"""
Voice Classifier - Classify voices as children or adults

This module provides machine learning-based voice classification
to identify children's voices in audio content using wav2vec2.
"""

import numpy as np
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple, Generator
from dataclasses import dataclass
import threading
import time
import tempfile
import gc
import os

from ..config import AnalysisConfig
from ..utils import get_output_manager

from typing import TYPE_CHECKING

# Optional imports for wav2vec2
if TYPE_CHECKING:
    import torch
    import torch.nn as nn
    from transformers import Wav2Vec2Processor
    from transformers.models.wav2vec2.modeling_wav2vec2 import (
        Wav2Vec2Model,
        Wav2Vec2PreTrainedModel,
    )
    WAV2VEC_AVAILABLE = True
else:
    try:
        import torch
        import torch.nn as nn
        from transformers import Wav2Vec2Processor
        from transformers.models.wav2vec2.modeling_wav2vec2 import (
            Wav2Vec2Model,
            Wav2Vec2PreTrainedModel,
        )
        WAV2VEC_AVAILABLE = True
    except (ImportError, OSError) as e:
        print(f"Warning: wav2vec2 dependencies not available: {e}")
        torch = None
        nn = None
        Wav2Vec2Processor = None
        Wav2Vec2Model = None
        Wav2Vec2PreTrainedModel = None
        WAV2VEC_AVAILABLE = False


@dataclass
class VoiceClassificationResult:
    """Result of voice classification analysis."""
    is_child_voice: bool
    confidence: float
    features_extracted: Dict[str, float]
    processing_time: float
    model_version: str


# Conditional class definitions
BaseModule = nn.Module if WAV2VEC_AVAILABLE else object
BasePreTrained = Wav2Vec2PreTrainedModel if WAV2VEC_AVAILABLE else object

class ModelHead(BaseModule):  # type: ignore
    """Classification head."""

    def __init__(self, config=None, num_labels=None):
        if BaseModule is not object:
            super().__init__()
            self.dense = nn.Linear(config.hidden_size, config.hidden_size)  # type: ignore
            self.dropout = nn.Dropout(config.final_dropout)  # type: ignore
            self.out_proj = nn.Linear(config.hidden_size, num_labels)  # type: ignore
        else:
            pass

    def forward(self, features, **kwargs):
        if BaseModule is not object:
            x = features
            x = self.dropout(x)
            x = self.dense(x)
            x = torch.tanh(x)  # type: ignore
            x = self.dropout(x)
            x = self.out_proj(x)
            return x
        else:
            return None


class AgeGenderModel(BasePreTrained):  # type: ignore
    """Speech age and gender classifier."""

    def __init__(self, config=None):
        if BasePreTrained is not object:
            super().__init__(config)
            self.config = config
            self.wav2vec2 = Wav2Vec2Model(config)  # type: ignore
            self.age = ModelHead(config, 1)
            self.gender = ModelHead(config, 3)
            self.init_weights()
        else:
            pass

    def forward(self, input_values):
        if BasePreTrained is not object:
            outputs = self.wav2vec2(input_values)
            hidden_states = outputs[0]
            hidden_states = torch.mean(hidden_states, dim=1)  # type: ignore
            logits_age = self.age(hidden_states)
            logits_gender = torch.softmax(self.gender(hidden_states), dim=1)  # type: ignore
            return hidden_states, logits_age, logits_gender
        else:
            return None, None, None


class VoiceClassifier:
    """
    Machine learning model for classifying voices as children or adults using wav2vec2.

    Uses wav2vec2 model with age and gender classification heads to identify children's voices
    with high accuracy. Includes model caching and memory management.
    """

    # Class-level shared instances for memory efficiency
    _shared_classifier: Optional['VoiceClassifier'] = None
    _lock = threading.Lock()  # Thread safety for shared instances

    def __init__(self, config: AnalysisConfig):
        """
        Initialize voice classifier.

        Args:
            config: Analysis configuration
        """
        self.config = config
        self.output = get_output_manager()
        self.wav2vec_available = WAV2VEC_AVAILABLE

        # Set default values from config
        self.model_name = config.wav2vec2_model
        self.child_threshold = config.child_voice_threshold
        self.age_threshold = config.language_confidence_threshold

        if not self.wav2vec_available:
            self.output.warning("wav2vec2 dependencies not available - using fallback classification")
            self.model_version = "fallback-1.0.0"
            return

        # Model parameters (only set when wav2vec is available)
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")  # type: ignore
        self.model_version = "wav2vec2-1.0.0"

        # Initialize model and processor
        self.processor = None
        self.model = None

        self.output.debug("Initialized wav2vec2 voice classifier")

    @classmethod
    def _get_or_create_shared_instance(cls, config: AnalysisConfig) -> 'VoiceClassifier':
        """Get existing classifier or create new one (thread-safe)"""
        with cls._lock:
            if cls._shared_classifier is None:
                print("🚀 Loading wav2vec2 model for the first time...")
                classifier = VoiceClassifier(config)
                classifier._load_model_and_processor()
                cls._shared_classifier = classifier
                print("✅ wav2vec2 model loaded and cached")
            else:
                print("🔄 Reusing existing wav2vec2 model")
            return cls._shared_classifier

    def _load_model_and_processor(self) -> None:
        """Load model and processor with memory optimizations."""
        if not self.wav2vec_available:
            return

        try:
            self.output.debug("Loading wav2vec2 model...")
            self.processor = Wav2Vec2Processor.from_pretrained(self.model_name)  # type: ignore
            self.model = AgeGenderModel.from_pretrained(self.model_name)  # type: ignore
            self.model = self.model.to(self.device)  # type: ignore

            # Enable memory-efficient mode
            self.model.eval()  # type: ignore
            
            # Convert to float16 (half precision) for GPU memory savings
            if torch.cuda.is_available():  # type: ignore
                self.model = self.model.half()  # type: ignore
            
            if torch.cuda.is_available():  # type: ignore
                # Enable gradient checkpointing for memory efficiency
                if hasattr(self.model, 'gradient_checkpointing_enable'):
                    self.model.gradient_checkpointing_enable()  # type: ignore

            self.output.debug("wav2vec2 model loaded successfully!")
        except Exception as e:
            self.output.error(f"Error loading wav2vec2 model: {e}")
            raise

    @staticmethod
    def _clear_cuda_cache() -> None:
        """Clear CUDA cache if available."""
        if not WAV2VEC_AVAILABLE:
            return
        if torch.cuda.is_available():  # type: ignore
            torch.cuda.empty_cache()  # type: ignore
            torch.cuda.synchronize()  # type: ignore

    @classmethod
    def clear_model_cache(cls) -> None:
        """Clear cached model instances to free memory (thread-safe)"""
        with cls._lock:
            if cls._shared_classifier is not None:
                print("🗑️ Clearing wav2vec2 classifier cache...")
                cls._clear_cuda_cache()
                cls._shared_classifier = None
                print("✅ wav2vec2 classifier cache cleared")

    def _preprocess_audio(self, audio_path: Path) -> Optional[np.ndarray]:
        """
        Preprocess audio file for wav2vec2 model.

        Args:
            audio_path: Path to audio file

        Returns:
            Preprocessed audio array or None if error
        """
        try:
            import librosa

            # Load audio at 16kHz (wav2vec2 requirement)
            speech_array, original_sr = librosa.load(audio_path, sr=16000)

            # Normalize audio
            if np.max(np.abs(speech_array)) > 0:
                speech_array = speech_array / np.max(np.abs(speech_array))

            return speech_array.astype(np.float32)

        except Exception as e:
            self.output.error(f"Error preprocessing audio {audio_path}: {e}")
            return None

    def _predict_age_gender(self, speech_array: np.ndarray) -> Tuple[Optional[float], Optional[float], Optional[np.ndarray], str]:
        """
        Predict age and gender from audio array.

        Args:
            speech_array: Audio array

        Returns:
            Tuple of (age_normalized, age_years, gender_probs, status)
        """
        if not self.wav2vec_available:
            return None, None, None, "wav2vec_unavailable"

        try:
            # Clear CUDA cache before processing
            self._clear_cuda_cache()

            # Process audio
            inputs = self.processor(speech_array, sampling_rate=16000)  # type: ignore
            input_values = inputs['input_values'][0]
            input_values = input_values.reshape(1, -1)

            # Move to device and convert to float16 if on GPU
            input_values = torch.from_numpy(input_values).to(self.device)  # type: ignore
            if torch.cuda.is_available():  # type: ignore
                input_values = input_values.half()  # type: ignore

            # Prediction
            with torch.no_grad():  # type: ignore
                hidden_states, age_logits, gender_probs = self.model(input_values)  # type: ignore

                # Age prediction (0-1 scale, 0=0 years, 1=100 years)
                age_normalized = float(age_logits.squeeze().cpu().float())
                age_years = age_normalized * 100  # Convert to years

                # Gender prediction probabilities [female, male, child]
                gender_probs = gender_probs.squeeze().cpu().float().numpy()

                # Clear intermediate tensors
                del input_values, hidden_states, age_logits
                self._clear_cuda_cache()

                return age_normalized, age_years, gender_probs, "success"

        except Exception as e:
            self.output.error(f"Error predicting age/gender: {e}")
            self._clear_cuda_cache()
            return None, None, None, "error"

    def _classify_age_group(self, age_normalized: Optional[float], gender_probs: Optional[np.ndarray]) -> Tuple[str, float]:
        """
        Classify as child or adult based on age and gender predictions.

        Args:
            age_normalized: Normalized age (0-1)
            gender_probs: Gender probabilities [female, male, child]

        Returns:
            Tuple of (label, confidence)
        """
        if gender_probs is None:
            # Fallback to age-only classification if gender probs not available
            if age_normalized is not None and age_normalized < self.age_threshold:
                return "child", age_normalized
            return "adult", 0.5  # Default confidence when data unavailable

        child_prob = gender_probs[2]

        # Check child probability
        if child_prob > self.child_threshold:
            return "child", child_prob

        # Or check age
        if age_normalized is not None and age_normalized < self.age_threshold:
            return "child", age_normalized

        return "adult", 1.0 - child_prob

    def classify_audio_file(self, audio_path: Path) -> VoiceClassificationResult:
        """
        Classify voices in an audio file using wav2vec2 or fallback method.

        Args:
            audio_path: Path to audio file

        Returns:
            Classification result
        """
        start_time = time.time()

        try:
            if not self.wav2vec_available:
                return self._fallback_classification(audio_path, start_time)

            # Ensure model is loaded
            if self.model is None or self.processor is None:
                self._load_model_and_processor()

            # Preprocess audio
            speech_array = self._preprocess_audio(audio_path)
            if speech_array is None:
                return VoiceClassificationResult(
                    is_child_voice=False,
                    confidence=0.0,
                    features_extracted={},
                    processing_time=time.time() - start_time,
                    model_version=self.model_version
                )

            # Get predictions
            age_norm, age_years, gender_probs, status = self._predict_age_gender(speech_array)

            if status == "error":
                return VoiceClassificationResult(
                    is_child_voice=False,
                    confidence=0.0,
                    features_extracted={},
                    processing_time=time.time() - start_time,
                    model_version=self.model_version
                )

            # Classify age group
            final_label, confidence = self._classify_age_group(age_norm, gender_probs)

            # Prepare features dict
            features = {
                "age_normalized": age_norm or 0.0,
                "age_years": age_years or 0.0,
                "gender_female_prob": gender_probs[0] if gender_probs is not None else 0.0,
                "gender_male_prob": gender_probs[1] if gender_probs is not None else 0.0,
                "gender_child_prob": gender_probs[2] if gender_probs is not None else 0.0,
            }

            return VoiceClassificationResult(
                is_child_voice=final_label == "child",
                confidence=confidence,
                features_extracted=features,
                processing_time=time.time() - start_time,
                model_version=self.model_version
            )

        except Exception as e:
            self.output.error(f"Voice classification failed for {audio_path}: {e}")
            return VoiceClassificationResult(
                is_child_voice=False,
                confidence=0.0,
                features_extracted={},
                processing_time=time.time() - start_time,
                model_version=self.model_version
            )

    def _fallback_classification(self, audio_path: Path, start_time: float) -> VoiceClassificationResult:
        """
        Fallback classification using MFCC features when wav2vec2 is not available.

        Args:
            audio_path: Path to audio file
            start_time: Start time for timing

        Returns:
            Classification result using fallback method
        """
        try:
            # Extract MFCC features (similar to old implementation)
            features = self._extract_mfcc_features(audio_path)
            if features is None:
                return VoiceClassificationResult(
                    is_child_voice=False,
                    confidence=0.0,
                    features_extracted={},
                    processing_time=time.time() - start_time,
                    model_version="fallback-mfcc"
                )

            # Simple heuristic: higher spectral centroid suggests younger voice
            centroid = features.get('spectral_centroid', 3000)
            confidence = min(max((centroid - 2000) / 2000, 0.0), 1.0)
            is_child = confidence > self.config.child_voice_threshold

            return VoiceClassificationResult(
                is_child_voice=is_child,
                confidence=confidence,
                features_extracted=features,
                processing_time=time.time() - start_time,
                model_version="fallback-mfcc"
            )

        except Exception as e:
            self.output.error(f"Fallback classification failed: {e}")
            return VoiceClassificationResult(
                is_child_voice=False,
                confidence=0.0,
                features_extracted={},
                processing_time=time.time() - start_time,
                model_version="fallback-error"
            )

    def _extract_mfcc_features(self, audio_path: Path) -> Optional[Dict[str, float]]:
        """
        Extract MFCC features for fallback classification.

        Args:
            audio_path: Path to audio file

        Returns:
            Dictionary of extracted MFCC features
        """
        try:
            import librosa

            # Load audio
            audio, sr = librosa.load(audio_path, sr=16000)

            if len(audio) == 0:
                return None

            # Extract MFCC features
            mfccs = librosa.feature.mfcc(
                y=audio,
                sr=sr,
                n_mfcc=13,
                n_fft=400,
                hop_length=160
            )

            # Compute statistics
            features = {}
            for i in range(13):
                mfcc_coeffs = mfccs[i]
                features[f'mfcc_{i}_mean'] = float(np.mean(mfcc_coeffs))
                features[f'mfcc_{i}_std'] = float(np.std(mfcc_coeffs))

            # Additional features
            features['rms_energy'] = float(np.mean(librosa.feature.rms(y=audio)))
            features['zero_crossing_rate'] = float(np.mean(librosa.feature.zero_crossing_rate(audio)))
            features['spectral_centroid'] = float(np.mean(librosa.feature.spectral_centroid(y=audio, sr=sr)))
            features['spectral_bandwidth'] = float(np.mean(librosa.feature.spectral_bandwidth(y=audio, sr=sr)))

            return features

        except ImportError:
            self.output.warning("librosa not available - cannot perform fallback classification")
            return None
        except Exception as e:
            self.output.error(f"MFCC feature extraction failed: {e}")
            return None

    def analyze_audio_chunk(self, audio_chunk: np.ndarray, sample_rate: int) -> VoiceClassificationResult:
        """
        Analyze a chunk of audio data directly.

        Args:
            audio_chunk: Audio data as numpy array
            sample_rate: Sample rate of audio

        Returns:
            Classification result
        """
        start_time = time.time()

        try:
            if not self.wav2vec_available:
                return VoiceClassificationResult(
                    is_child_voice=False,
                    confidence=0.0,
                    features_extracted={},
                    processing_time=time.time() - start_time,
                    model_version="fallback-1.0.0"
                )

            # Ensure model is loaded
            if self.model is None or self.processor is None:
                self._load_model_and_processor()

            # Resample if needed
            if sample_rate != 16000:
                import librosa
                audio_chunk = librosa.resample(audio_chunk, orig_sr=sample_rate, target_sr=16000)

            # Normalize
            if np.max(np.abs(audio_chunk)) > 0:
                audio_chunk = audio_chunk / np.max(np.abs(audio_chunk))

            # Get predictions
            age_norm, age_years, gender_probs, status = self._predict_age_gender(audio_chunk.astype(np.float32))

            if status == "error":
                return VoiceClassificationResult(
                    is_child_voice=False,
                    confidence=0.0,
                    features_extracted={},
                    processing_time=time.time() - start_time,
                    model_version=self.model_version
                )

            # Classify
            final_label, confidence = self._classify_age_group(age_norm, gender_probs)

            features = {
                "age_normalized": age_norm or 0.0,
                "age_years": age_years or 0.0,
                "gender_female_prob": gender_probs[0] if gender_probs is not None else 0.0,
                "gender_male_prob": gender_probs[1] if gender_probs is not None else 0.0,
                "gender_child_prob": gender_probs[2] if gender_probs is not None else 0.0,
            }

            return VoiceClassificationResult(
                is_child_voice=final_label == "child",
                confidence=confidence,
                features_extracted=features,
                processing_time=time.time() - start_time,
                model_version=self.model_version
            )

        except Exception as e:
            self.output.error(f"Audio chunk analysis failed: {e}")
            return VoiceClassificationResult(
                is_child_voice=False,
                confidence=0.0,
                features_extracted={},
                processing_time=time.time() - start_time,
                model_version=self.model_version
            )

    def _split_audio_file_into_chunks(self, audio_path: Path) -> Generator[Tuple[np.ndarray, int, int], None, None]:
        """
        Split a large audio file into chunks without keeping all in memory.

        Uses librosa's offset/duration to stream chunks directly without loading entire file.
        Each chunk is of duration specified in config.max_chunk_duration_seconds.

        Args:
            audio_path: Path to audio file

        Yields:
            Tuple of (audio_chunk_array, chunk_index, total_chunks) where total_chunks is estimated
        """
        try:
            import librosa
            import soundfile as sf

            chunk_duration_seconds = self.config.max_chunk_duration_seconds
            sr = 16000
            
            # Get total duration without loading entire file
            try:
                with sf.SoundFile(str(audio_path)) as f:
                    total_frames = len(f)
                    file_sr = f.samplerate
                total_duration_seconds = total_frames / file_sr
            except Exception as e:
                self.output.error(f"Could not read audio duration: {e}")
                return

            # Calculate total chunks
            total_chunks = int(np.ceil(total_duration_seconds / chunk_duration_seconds))
            
            # Stream load chunks one at a time using offset/duration
            chunk_index = 0
            offset_seconds = 0.0

            while offset_seconds < total_duration_seconds:
                # Load only this chunk
                chunk, _ = librosa.load(
                    str(audio_path),
                    sr=sr,
                    offset=offset_seconds,
                    duration=chunk_duration_seconds,
                    mono=True
                )

                if len(chunk) == 0:
                    break

                # Normalize chunk
                if np.max(np.abs(chunk)) > 0:
                    chunk = chunk / np.max(np.abs(chunk))

                yield chunk.astype(np.float32), chunk_index, total_chunks

                # Move to next chunk
                offset_seconds += chunk_duration_seconds
                chunk_index += 1

                # Explicit cleanup
                del chunk
                gc.collect()
                self._clear_cuda_cache()

        except Exception as e:
            self.output.error(f"Error splitting audio file {audio_path}: {e}")
            return

    def classify_large_audio_file(self, audio_path: Path, max_chunks: int = 3) -> Dict[str, Any]:
        """
        Classify voices in a large audio file by processing chunks.

        Processes only the first N chunks (default 3) to avoid excessive processing.
        This is useful for long audio files where the voice classification is assumed
        to be consistent.

        Args:
            audio_path: Path to audio file
            max_chunks: Maximum number of chunks to process (default: 3)

        Returns:
            Dictionary containing:
                - is_child_voice: Boolean indicating if child voice detected
                - confidence: Overall confidence score (average of processed chunks)
                - chunks_processed: Number of chunks actually processed
                - total_chunks: Total number of chunks in file
                - chunk_results: List of results for each processed chunk
                - overall_processing_time: Total processing time
                - model_version: Version of model used
        """
        overall_start_time = time.time()
        chunk_results = []
        chunks_processed = 0
        total_chunks_estimate = 0

        try:
            self.output.debug(f"Starting large audio file classification for {audio_path}")

            # Process chunks one at a time
            for chunk_audio, chunk_idx, total_chunks in self._split_audio_file_into_chunks(audio_path):
                total_chunks_estimate = total_chunks

                # Only process first max_chunks
                if chunk_idx >= max_chunks:
                    self.output.debug(f"Reached max chunks limit ({max_chunks}), stopping processing")
                    break

                try:
                    # Analyze this chunk
                    result = self.analyze_audio_chunk(chunk_audio, sample_rate=16000)

                    chunk_results.append({
                        "chunk_index": chunk_idx,
                        "is_child_voice": result.is_child_voice,
                        "confidence": result.confidence,
                        "features_extracted": result.features_extracted,
                        "processing_time": result.processing_time,
                        "model_version": result.model_version
                    })

                    chunks_processed += 1

                    self.output.debug(
                        f"Chunk {chunk_idx}/{total_chunks}: "
                        f"child_voice={result.is_child_voice}, "
                        f"confidence={result.confidence:.2f}"
                    )

                except Exception as e:
                    self.output.error(f"Error processing chunk {chunk_idx}: {e}")
                
                finally:
                    # Always cleanup chunk data, even if error occurred
                    del chunk_audio
                    gc.collect()
                    self._clear_cuda_cache()

            # Calculate overall results
            if chunk_results:
                # Determine overall child voice classification
                # If any chunk has child voice with high confidence, consider it child voice
                child_voices = [r for r in chunk_results if r["is_child_voice"]]
                is_child_overall = len(child_voices) > 0

                # Average confidence across chunks
                avg_confidence = np.mean([r["confidence"] for r in chunk_results])

                overall_processing_time = time.time() - overall_start_time

                result = {
                    "is_child_voice": is_child_overall,
                    "confidence": float(avg_confidence),
                    "chunks_processed": chunks_processed,
                    "total_chunks": total_chunks_estimate,
                    "chunk_results": chunk_results,
                    "overall_processing_time": overall_processing_time,
                    "model_version": self.model_version
                }

                self.output.info(
                    f"Large audio classification complete: "
                    f"is_child={is_child_overall}, "
                    f"confidence={avg_confidence:.2f}, "
                    f"chunks={chunks_processed}/{total_chunks_estimate}"
                )

                return result
            else:
                # No chunks processed successfully
                return {
                    "is_child_voice": False,
                    "confidence": 0.0,
                    "chunks_processed": 0,
                    "total_chunks": total_chunks_estimate,
                    "chunk_results": [],
                    "overall_processing_time": time.time() - overall_start_time,
                    "model_version": self.model_version,
                    "error": "No chunks processed successfully"
                }

        except Exception as e:
            self.output.error(f"Large audio file classification failed for {audio_path}: {e}")
            return {
                "is_child_voice": False,
                "confidence": 0.0,
                "chunks_processed": chunks_processed,
                "total_chunks": total_chunks_estimate,
                "chunk_results": chunk_results,
                "overall_processing_time": time.time() - overall_start_time,
                "model_version": self.model_version,
                "error": str(e)
            }


# Factory function to create classifier with caching
def get_voice_classifier(config: AnalysisConfig) -> VoiceClassifier:
    """Get voice classifier instance with model caching."""
    return VoiceClassifier._get_or_create_shared_instance(config)
import io
import logging
import struct
import wave
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple
from uuid import UUID

from google.cloud import storage
from google.cloud import speech

from app.config import settings

logger = logging.getLogger(__name__)


def convert_float32_to_int16(audio_data: bytes, wav_info: dict) -> bytes:
    """Convert 32-bit float WAV to 16-bit PCM WAV."""
    try:
        sample_rate = wav_info["sample_rate"]
        num_channels = wav_info["channels"]

        # Find the data chunk
        data_start = audio_data.find(b'data')
        if data_start == -1:
            return audio_data

        # Skip 'data' + 4 bytes for chunk size
        data_start += 8
        float_data = audio_data[data_start:]

        # Convert float32 samples to int16
        num_samples = len(float_data) // 4
        int16_samples = []

        for i in range(num_samples):
            float_val = struct.unpack('<f', float_data[i*4:(i+1)*4])[0]
            # Clamp to [-1, 1] and convert to int16
            float_val = max(-1.0, min(1.0, float_val))
            int16_val = int(float_val * 32767)
            int16_samples.append(struct.pack('<h', int16_val))

        int16_data = b''.join(int16_samples)

        # Create new WAV file with PCM format
        output = io.BytesIO()
        with wave.open(output, 'wb') as wav_out:
            wav_out.setnchannels(num_channels)
            wav_out.setsampwidth(2)  # 16-bit = 2 bytes
            wav_out.setframerate(sample_rate)
            wav_out.writeframes(int16_data)

        logger.info(f"Converted float32 to int16: {len(audio_data)} -> {len(output.getvalue())} bytes")
        return output.getvalue()

    except Exception as e:
        logger.error(f"Float32 to int16 conversion failed: {e}")
        return audio_data


def get_wav_info(audio_data: bytes) -> dict:
    """Extract audio info from WAV header."""
    try:
        # WAV header structure:
        # bytes 0-3: "RIFF"
        # bytes 8-11: "WAVE"
        # bytes 20-21: audio format (1=PCM, 3=IEEE float)
        # bytes 22-23: number of channels
        # bytes 24-27: sample rate
        # bytes 34-35: bits per sample
        if len(audio_data) < 36:
            return {}
        if audio_data[:4] != b'RIFF' or audio_data[8:12] != b'WAVE':
            return {}
        audio_format = struct.unpack('<H', audio_data[20:22])[0]
        num_channels = struct.unpack('<H', audio_data[22:24])[0]
        sample_rate = struct.unpack('<I', audio_data[24:28])[0]
        bits_per_sample = struct.unpack('<H', audio_data[34:36])[0]
        return {
            "format": audio_format,  # 1=PCM, 3=IEEE float
            "channels": num_channels,
            "sample_rate": sample_rate,
            "bits_per_sample": bits_per_sample,
        }
    except Exception:
        return {}


# Supported audio formats with their Speech-to-Text encoding
SUPPORTED_AUDIO_FORMATS = {
    ".wav": {
        "content_types": ["audio/wav", "audio/x-wav", "audio/wave"],
        "encoding": speech.RecognitionConfig.AudioEncoding.LINEAR16,
    },
    ".webm": {
        "content_types": ["audio/webm"],
        "encoding": speech.RecognitionConfig.AudioEncoding.WEBM_OPUS,
    },
    ".mp3": {
        "content_types": ["audio/mpeg", "audio/mp3"],
        "encoding": speech.RecognitionConfig.AudioEncoding.MP3,
    },
    ".m4a": {
        "content_types": ["audio/m4a", "audio/mp4", "audio/x-m4a"],
        "encoding": speech.RecognitionConfig.AudioEncoding.MP3,
    },
}

MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5MB


class SpeechService:
    def __init__(self):
        self._storage_client: Optional[storage.Client] = None
        self._speech_client: Optional[speech.SpeechClient] = None

    @property
    def storage_client(self) -> storage.Client:
        if self._storage_client is None:
            self._storage_client = storage.Client()
        return self._storage_client

    @property
    def speech_client(self) -> speech.SpeechClient:
        if self._speech_client is None:
            self._speech_client = speech.SpeechClient()
        return self._speech_client

    def is_local_storage(self) -> bool:
        """Check if we should use local storage (empty static_base_url means local)."""
        return not settings.static_base_url

    def get_bucket_name(self) -> str:
        """Get bucket name from static_base_url."""
        # Example: https://storage.googleapis.com/coach-vocab-static -> coach-vocab-static
        if "coach-vocab-static-prod" in settings.static_base_url:
            return "coach-vocab-static-prod"
        return "coach-vocab-static"

    def validate_audio_format(
        self, filename: str, content_type: str
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Validate audio file format.
        Returns: (is_valid, extension, error_message)
        """
        ext = None
        for supported_ext in SUPPORTED_AUDIO_FORMATS:
            if filename.lower().endswith(supported_ext):
                ext = supported_ext
                break

        if not ext:
            return False, None, "Unsupported file format. Supported: WAV, WebM, MP3, M4A"

        return True, ext, None

    def generate_storage_path(
        self, user_id: UUID, word_id: UUID, extension: str
    ) -> str:
        """
        Generate storage path.
        Format: speech-logs/{user_id}/{timestamp}-{word_id}.{ext}
        """
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"{timestamp}-{word_id}{extension}"
        return f"speech-logs/{user_id}/{filename}"

    async def save_audio(
        self, audio_data: bytes, storage_path: str, content_type: str
    ) -> str:
        """
        Save audio file to local filesystem or GCS.
        Returns: Full path (local path or gs:// URL)
        """
        if self.is_local_storage():
            return self._save_to_local(audio_data, storage_path)
        else:
            return self._upload_to_gcs(audio_data, storage_path, content_type)

    def _save_to_local(self, audio_data: bytes, storage_path: str) -> str:
        """Save audio to local static directory."""
        local_path = Path("static") / storage_path
        local_path.parent.mkdir(parents=True, exist_ok=True)

        with open(local_path, "wb") as f:
            f.write(audio_data)

        return str(local_path)

    def _upload_to_gcs(
        self, audio_data: bytes, storage_path: str, content_type: str
    ) -> str:
        """Upload audio to GCS."""
        bucket_name = self.get_bucket_name()
        bucket = self.storage_client.bucket(bucket_name)
        blob = bucket.blob(storage_path)

        blob.upload_from_string(
            audio_data,
            content_type=content_type,
        )

        return f"gs://{bucket_name}/{storage_path}"

    async def transcribe_audio(
        self, audio_data: bytes, extension: str
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Transcribe audio using Google Cloud Speech-to-Text.
        Returns: (transcript, error_message)
        """
        try:
            format_config = SUPPORTED_AUDIO_FORMATS.get(extension)
            if not format_config:
                return None, f"Unsupported audio format: {extension}"

            encoding = format_config["encoding"]

            audio = speech.RecognitionAudio(content=audio_data)

            # For WAV files, extract info from header
            if extension == ".wav":
                wav_info = get_wav_info(audio_data)
                logger.info(f"WAV file detected: format={wav_info.get('format')} (1=PCM,3=float), "
                           f"channels={wav_info.get('channels')}, sample_rate={wav_info.get('sample_rate')}, "
                           f"bits={wav_info.get('bits_per_sample')}, size={len(audio_data)} bytes")

                # Convert float32 to int16 if needed
                if wav_info.get("format") == 3:  # IEEE float
                    audio_data = convert_float32_to_int16(audio_data, wav_info)
                    audio = speech.RecognitionAudio(content=audio_data)

                sample_rate = wav_info.get("sample_rate")
                num_channels = wav_info.get("channels", 1)

                if sample_rate:
                    config = speech.RecognitionConfig(
                        encoding=encoding,
                        sample_rate_hertz=sample_rate,
                        audio_channel_count=num_channels,
                        language_code="en-US",
                        enable_automatic_punctuation=False,
                    )
                else:
                    # Fallback: let Google auto-detect
                    config = speech.RecognitionConfig(
                        encoding=speech.RecognitionConfig.AudioEncoding.ENCODING_UNSPECIFIED,
                        language_code="en-US",
                        enable_automatic_punctuation=False,
                    )
            else:
                config = speech.RecognitionConfig(
                    encoding=encoding,
                    sample_rate_hertz=48000,
                    language_code="en-US",
                    enable_automatic_punctuation=False,
                )

            logger.info(f"Sending transcription request to Google Speech-to-Text: encoding={config.encoding}, sample_rate={config.sample_rate_hertz}, language={config.language_code}")

            response = self.speech_client.recognize(config=config, audio=audio)

            if not response.results:
                logger.info("Transcription complete: no speech detected")
                return "", None  # No speech detected

            # Concatenate all transcript results
            transcript = " ".join(
                result.alternatives[0].transcript
                for result in response.results
                if result.alternatives
            )

            logger.info(f"Transcription complete: '{transcript}'")
            return transcript.strip(), None

        except Exception as e:
            logger.error(f"Google Speech-to-Text API error: {str(e)}")
            return None, f"Transcription failed: {str(e)}"


# Singleton instance
speech_service = SpeechService()

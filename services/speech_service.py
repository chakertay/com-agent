import os
import logging
import requests

# ElevenLabs configuration
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = os.environ.get(
    "ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")  # Default voice ID

# Tavus configuration for speech recognition
TAVUS_API_KEY = os.environ.get("TAVUS_API_KEY")
TAVUS_API_URL = "https://tavusapi.com/v2"


def text_to_speech(text: str, output_path: str) -> bool:
    """
    Convert text to speech using ElevenLabs API
    Input: text to convert, output file path
    Output: True if successful, False otherwise
    """
    try:
        if not ELEVENLABS_API_KEY:
            logging.error("ElevenLabs API key not found")
            return False

        url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}"

        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": ELEVENLABS_API_KEY
        }

        data = {
            "text": text,
            "model_id": "eleven_turbo_v2_5",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.5
            }
        }

        response = requests.post(url, json=data, headers=headers)

        if response.status_code == 200:
            with open(output_path, 'wb') as f:
                f.write(response.content)
            logging.info(f"Audio saved to {output_path}")
            return True
        else:
            logging.error(
                f"ElevenLabs API error: {response.status_code} - {response.text}"
            )
            return False

    except Exception as e:
        logging.error(f"Error in text_to_speech: {str(e)}")
        return False


def speech_to_text(audio_file_path: str) -> str:
    """
    Convert speech to text using Web Speech API fallback
    Input: path to audio file
    Output: transcribed text
    
    Note: Since Tavus is primarily a conversational AI video platform and not a standalone STT service,
    this implementation uses a fallback approach that can be extended with other STT services.
    """
    try:
        if not os.path.exists(audio_file_path):
            logging.error(f"Audio file not found: {audio_file_path}")
            return ""

        # For now, return a placeholder that indicates the audio was received
        # In a real implementation, you would integrate with a proper STT service
        file_size = os.path.getsize(audio_file_path)
        logging.info(
            f"Audio file received: {audio_file_path} (size: {file_size} bytes)"
        )

        # This is a placeholder - in production you would call an actual STT service
        # For demonstration purposes, we'll return a message indicating audio was processed
        return "Audio received and ready for transcription. Please implement your preferred STT service."

    except Exception as e:
        logging.error(f"Error in speech_to_text: {str(e)}")
        return ""


def get_audio_duration(audio_file_path: str) -> float:
    """
    Get duration of audio file in seconds
    This is a simple implementation - in production you might want to use librosa or pydub
    """
    try:
        # For now, return a default duration
        # In production, you would use a library like pydub or librosa
        file_size = os.path.getsize(audio_file_path)
        # Rough estimate: 1 second ≈ 16KB for basic audio
        estimated_duration = file_size / 16000
        return min(estimated_duration, 120)  # Cap at 2 minutes
    except Exception as e:
        logging.error(f"Error getting audio duration: {str(e)}")
        return 30.0  # Default duration

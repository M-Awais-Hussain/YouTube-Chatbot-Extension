from youtube_transcript_api import YouTubeTranscriptApi
from transformers import pipeline
import pytube
import os
from tempfile import NamedTemporaryFile
import sacremoses  # Added to prevent warning

# Free translation model from Hugging Face
translator = pipeline("translation",
model="Helsinki-NLP/opus-mt-mul-en",
tokenizer="Helsinki-NLP/opus-mt-mul-en")

def get_video_transcript(video_id):
    try:
        # Try English transcript first
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['en'])
        return " ".join([t['text'] for t in transcript_list])

    except:
        try:
            # Try any available language and translate
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
            combined_text = " ".join([t['text'] for t in transcript_list])
            
            # Split into chunks of 500 characters (model limit)
            chunks = [combined_text[i:i+500] for i in range(0, len(combined_text), 500)]
            translated_chunks = []
            
            for chunk in chunks:
                try:
                    translated = translator(chunk, max_length=512)
                    translated_chunks.append(translated[0]['translation_text'])
                except Exception as e:
                    print(f"Translation error: {e}")
                    translated_chunks.append(chunk)  # Fallback to original text
            
            return " ".join(translated_chunks)
        
        except Exception as e:
            print(f"Transcript processing failed: {e}")
            # Fall back to audio transcription
            return transcribe_audio(video_id)

def transcribe_audio(video_id):
    try:
        # Use pytube to download audio
        yt = pytube.YouTube(f'https://www.youtube.com/watch?v={video_id}')
        audio_stream = yt.streams.filter(only_audio=True).first()
        audio_file = audio_stream.download(filename="audio.mp4")

        # Convert to text using ASR (Speech-to-Text)
        from speech_recognition import Recognizer, AudioFile
        recognizer = Recognizer()
        
        with AudioFile(audio_file) as source:
            audio = recognizer.record(source)
        
        text = recognizer.recognize_google(audio)
        return text

    except Exception as e:
        print(f"Audio transcription failed: {e}")
        return None

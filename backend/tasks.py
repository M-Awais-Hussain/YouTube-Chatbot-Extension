from celery import shared_task
from services.transcript import get_video_transcript
from services.retrieval import create_vector_store, create_retriever
from services.cache import video_cache
import logging

logger = logging.getLogger(__name__)

@shared_task
def process_video_task(video_id):
    """Asynchronous task to process a YouTube video"""
    try:
        # Get transcript
        transcript = get_video_transcript(video_id)
        if not transcript:
            return {'error': 'Transcript unavailable or too short'}
        
        # Create vector store and retriever
        vector_store = create_vector_store(transcript)
        retriever = create_retriever(vector_store)
        
        result = {
            'status': 'success',
            'videoId': video_id,
            'chunks': len(vector_store.index_to_docstore_id)
        }
        
        # Store in cache
        video_cache.add(video_id, result)
        
        # Return success
        return result
        
    except Exception as e:
        logger.error(f"Error processing video {video_id}: {str(e)}")
        return {'error': 'Video processing failed'}

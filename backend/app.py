from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from services.transcript import get_video_transcript
from services.retrieval import create_vector_store, create_retriever, answer_with_retriever
from services.llm_service import LLMService
from services.cache import video_cache
from config import Config
import logging
from typing import Dict, Any

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Configure rate limiting
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    storage_uri="memory://",
    default_limits=["30 per minute"]
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize LLM service
llm_service = LLMService()

class VideoProcessor:
    def __init__(self):
        self.active_sessions: Dict[str, Any] = {}

    def process_video(self, video_id: str) -> Dict[str, Any]:
        """Process a YouTube video with caching support"""
        # Check cache first
        cached = video_cache.get(video_id)
        if cached:
            logger.info(f"Returning cached results for video {video_id}")
            return cached['data']
        
        if video_id in self.active_sessions:
            logger.info(f"Video {video_id} is already processed.")
            return {'status': 'already_processed'}
        
        try:
            # Get transcript
            transcript = get_video_transcript(video_id)
            if not transcript or len(transcript) < 100:
                return {'error': 'Transcript unavailable or too short'}
            
            # Create vector store
            vector_store = create_vector_store(transcript)
            
            # Create retriever
            retriever = create_retriever(vector_store)
            
            # Prepare result
            result = {
                'status': 'success',
                'videoId': video_id,
                'chunks': len(vector_store.index_to_docstore_id),
                'transcript': transcript  # store transcript in result for caching
            }
            
            # Cache result with empty chat history
            video_cache.add(video_id, result, chat_history=[])
            
            # Store session
            self.active_sessions[video_id] = {
                'retriever': retriever,
                'transcript': transcript,
                'chunks': len(vector_store.index_to_docstore_id)
            }
            
            return result
        
        except Exception as e:
            logger.error(f"Video processing failed: {str(e)}")
            return {'error': 'Video processing failed'}

processor = VideoProcessor()

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy'})

@app.route('/api/process', methods=['POST'])
@limiter.limit("5 per minute")
def process_video_endpoint():
    """Endpoint to process a YouTube video"""
    data = request.json
    video_id = data.get('videoId')

    if not video_id:
        return jsonify({'error': 'videoId required'}), 400
    
    result = processor.process_video(video_id)
    if 'error' in result:
        return jsonify(result), 400
    return jsonify(result)

@app.route('/api/query', methods=['POST'])
@limiter.limit("3 per minute")
def handle_query():
    """Endpoint to handle user questions"""
    data = request.json
    video_id = data.get('videoId')
    question = data.get('question')

    if not all([video_id, question]):
        return jsonify({'error': 'Missing parameters'}), 400
    
    # Check if video is processed
    if video_id not in processor.active_sessions:
        cached = video_cache.get(video_id)
        if cached:
            # recreate retriever from cached transcript
            transcript = cached['data']['transcript']
            vector_store = create_vector_store(transcript)
            retriever = create_retriever(vector_store)
            processor.active_sessions[video_id] = {
                'retriever': retriever,
                'transcript': transcript,
                'chunks': cached['data']['chunks']
            }
            logger.info(f"Session recreated from cache for video {video_id}")
        else:
            return jsonify({'error': 'Video not processed'}), 404
    
    try:
        retriever = processor.active_sessions[video_id]['retriever']
        
        # Get answer
        answer = answer_with_retriever(question[:300], retriever)
        
        # Retrieve chat history
        cached = video_cache.get(video_id)
        chat_history = cached['chat_history'] if cached else []
        
        # Append current Q&A
        chat_history.append({'question': question, 'answer': answer})
        
        # Update chat history in cache
        video_cache.update_chat_history(video_id, chat_history)
        
        return jsonify({
            'answer': answer,
            'chatHistory': chat_history,  # return chat history as well
            'status': 'success'
        })
    
    except Exception as e:
        logger.error(f"Query processing failed: {str(e)}")
        return jsonify({'error': 'Query processing failed'}), 500

@app.route('/api/clear_session', methods=['POST'])
def clear_session():
    """Clear a processed video session and its chat history"""
    video_id = request.json.get('videoId')
    if video_id:
        if video_id in processor.active_sessions:
            del processor.active_sessions[video_id]
        video_cache.clear(video_id)
    return jsonify({'status': 'success'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=Config.DEBUG)

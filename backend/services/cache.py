import time
from config import Config

class VideoCache:
    def __init__(self):
        self.cache = {}

    def add(self, video_id, data, chat_history=None):
        """Store both the video data and chat history"""
        self.cache[video_id] = {
            'data': data,
            'timestamp': time.time(),
            'chat_history': chat_history or []
        }

    def get(self, video_id):
        """Retrieve the cached video data and chat history"""
        item = self.cache.get(video_id)
        if item and (time.time() - item['timestamp']) < Config.CACHE_EXPIRATION:
            return item
        return None
    
    def update_chat_history(self, video_id, chat_history):
        """Update chat history for a video"""
        if video_id in self.cache:
            self.cache[video_id]['chat_history'] = chat_history
    
    def clear(self, video_id=None):
        """Clear the cache"""
        if video_id:
            self.cache.pop(video_id, None)
        else:
            self.cache.clear()

# Create an instance of VideoCache for usage
video_cache = VideoCache()

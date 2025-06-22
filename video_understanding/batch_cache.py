import json
from pathlib import Path
from typing import Any, Dict, List, Optional


class BatchCache:
    """Handles caching of batch states and responses"""
    
    def __init__(self, cache_dir: str = "batch_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
    
    def load_state_up_to_batch(self, target_batch: int) -> Optional[Dict[str, Any]]:
        """Load accumulated state up to the target batch from cache"""
        if target_batch == 0:
            return None
            
        # Load the most recent cached state before target_batch
        for batch_num in range(target_batch - 1, -1, -1):
            cache_file = self.cache_dir / f"batch_{batch_num:03d}_state.json"
            if cache_file.exists():
                print(f"Loading state from batch {batch_num}")
                with open(cache_file, 'r') as f:
                    cached_data = json.load(f)
                    return {
                        'persistent_goal_state': cached_data.get('persistent_goal_state'),
                        'persistent_current_state': cached_data.get('persistent_current_state'),
                        'persistent_protocol_log': cached_data.get('persistent_protocol_log'),
                        'persistent_warnings': cached_data.get('persistent_warnings')
                    }
        
        print(f"No cached state found for batch {target_batch}, starting fresh")
        return None

    def save_batch_cache(self, batch_num: int, response_data: Dict[str, Any], 
                        persistent_states: Dict[str, Any]) -> None:
        """Save batch response and accumulated state to cache"""
        cache_data = {
            'batch_num': batch_num,
            'response': response_data,
            **persistent_states
        }
        
        cache_file = self.cache_dir / f"batch_{batch_num:03d}_state.json"
        with open(cache_file, 'w') as f:
            json.dump(cache_data, f, indent=2, default=str)
        print(f"Cached state to {cache_file}")
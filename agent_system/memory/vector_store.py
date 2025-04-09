"""
Vector store for agent memory management.
"""
from typing import Dict, List, Any, Optional
import logging
import json
import os
from datetime import datetime

logger = logging.getLogger(__name__)

class VectorStore:
    """
    Simple vector store implementation for storing and retrieving agent memory.
    In a production environment, this would use proper vector embeddings and similarity search.
    """
    
    def __init__(self, storage_path: str = ".memory"):
        self.storage_path = storage_path
        self.memory = {}
        os.makedirs(storage_path, exist_ok=True)
        logger.info(f"VectorStore initialized with storage path: {storage_path}")
        
    def add_entry(self, key: str, data: Any) -> None:
        """
        Add an entry to the memory store.
        
        Args:
            key: Unique identifier for the entry
            data: Data to store (must be serializable)
        """
        timestamp = datetime.now().isoformat()
        
        entry = {
            "timestamp": timestamp,
            "data": data
        }
        
        self.memory[key] = entry
        self._persist_entry(key, entry)
        logger.debug(f"Added entry with key: {key}")
    
    def get_entry(self, key: str) -> Optional[Any]:
        """
        Retrieve an entry by key.
        
        Args:
            key: The key to look up
            
        Returns:
            The stored data or None if not found
        """
        entry = self.memory.get(key)
        if entry:
            return entry["data"]
        
        # Try to load from disk if not in memory
        disk_entry = self._load_entry(key)
        if disk_entry:
            self.memory[key] = disk_entry
            return disk_entry["data"]
            
        return None
    
    def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Search for entries related to the query.
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of matching entries
        """
        # In a real implementation, this would use vector embeddings and similarity search
        # For now, just do a simple text search in keys
        results = []
        
        for key, entry in self.memory.items():
            if query.lower() in key.lower():
                results.append({
                    "key": key,
                    "data": entry["data"],
                    "timestamp": entry["timestamp"]
                })
                
        return results[:limit]
    
    def _persist_entry(self, key: str, entry: Dict[str, Any]) -> None:
        """Save entry to disk."""
        try:
            file_path = os.path.join(self.storage_path, f"{key}.json")
            with open(file_path, 'w') as f:
                json.dump(entry, f)
        except Exception as e:
            logger.error(f"Failed to persist entry {key}: {e}")
    
    def _load_entry(self, key: str) -> Optional[Dict[str, Any]]:
        """Load entry from disk."""
        try:
            file_path = os.path.join(self.storage_path, f"{key}.json")
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load entry {key}: {e}")
        
        return None

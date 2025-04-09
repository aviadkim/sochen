"""
Vector store for persistent memory across agent sessions.
"""
import os
import json
import logging
import pickle
from typing import Dict, List, Any, Optional
import faiss
import numpy as np
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from ..config import GEMINI_API_KEY, get_project_root

logger = logging.getLogger("agent_system.memory")

class MemoryStore:
    """A simple vector store for maintaining agent memory."""
    
    def __init__(self, project_name: str = None):
        """Initialize the memory store.
        
        Args:
            project_name: Optional project name. If not provided, uses the project directory name.
        """
        self.embeddings = GoogleGenerativeAIEmbeddings(
            google_api_key=GEMINI_API_KEY,
            model="embedding-001",
        )
        
        # Determine project name from current directory if not provided
        if project_name is None:
            project_root = get_project_root()
            project_name = os.path.basename(project_root)
        
        self.project_name = project_name
        
        # Set up memory directory within project
        memory_dir = os.path.join(get_project_root(), ".agent_memory")
        os.makedirs(memory_dir, exist_ok=True)
        
        self.index_path = os.path.join(memory_dir, f"{project_name}_index.faiss")
        self.data_path = os.path.join(memory_dir, f"{project_name}_data.pkl")
        
        # Initialize or load existing index
        if os.path.exists(self.index_path) and os.path.exists(self.data_path):
            self._load()
        else:
            self._create_new()
    
    def _create_new(self):
        """Create a new empty vector index."""
        # Start with a simple, single-dimensional index (can be expanded later)
        self.dimension = 768  # Default for embedding-001
        self.index = faiss.IndexFlatL2(self.dimension)
        self.texts = []
        self.metadata = []
        
        logger.info(f"Created new memory store for project {self.project_name}")
    
    def _load(self):
        """Load existing vector index and data."""
        try:
            self.index = faiss.read_index(self.index_path)
            with open(self.data_path, 'rb') as f:
                data = pickle.load(f)
                self.texts = data['texts']
                self.metadata = data['metadata']
                self.dimension = data.get('dimension', 768)
            
            logger.info(f"Loaded memory store with {len(self.texts)} entries for project {self.project_name}")
        except Exception as e:
            logger.error(f"Failed to load existing memory store: {e}")
            self._create_new()
    
    def _save(self):
        """Save the current index and data."""
        try:
            faiss.write_index(self.index, self.index_path)
            with open(self.data_path, 'wb') as f:
                pickle.dump({
                    'texts': self.texts,
                    'metadata': self.metadata,
                    'dimension': self.dimension
                }, f)
            logger.info(f"Saved memory store with {len(self.texts)} entries")
        except Exception as e:
            logger.error(f"Failed to save memory store: {e}")
    
    def add_memory(self, text: str, metadata: Dict[str, Any] = None):
        """Add a memory entry to the store.
        
        Args:
            text: The text content to remember
            metadata: Optional metadata about this memory
        """
        if metadata is None:
            metadata = {}
        
        # Create embedding
        try:
            embedding = self.embeddings.embed_query(text)
            
            # Add to index
            vector = np.array([embedding], dtype=np.float32)
            self.index.add(vector)
            
            # Store text and metadata
            self.texts.append(text)
            self.metadata.append(metadata)
            
            # Save changes
            self._save()
            return True
        except Exception as e:
            logger.error(f"Failed to add memory: {e}")
            return False
    
    def search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """Search for similar memories.
        
        Args:
            query: The search query
            k: Number of results to return
        
        Returns:
            List of dict with 'text', 'metadata', and 'score' keys
        """
        if len(self.texts) == 0:
            return []
        
        try:
            # Create query embedding
            query_embedding = self.embeddings.embed_query(query)
            vector = np.array([query_embedding], dtype=np.float32)
            
            # Search
            k = min(k, len(self.texts))  # Can't return more than we have
            scores, indices = self.index.search(vector, k)
            
            # Format results
            results = []
            for i, idx in enumerate(indices[0]):
                if idx < len(self.texts):  # Safety check
                    results.append({
                        'text': self.texts[idx],
                        'metadata': self.metadata[idx],
                        'score': float(scores[0][i])
                    })
            
            return results
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
    
    def get_related_memories(self, text: str, k: int = 5, agent: str = None, 
                             action_type: str = None) -> str:
        """Get formatted string of related memories for context.
        
        Args:
            text: The context to find related memories for
            k: Number of memories to retrieve
            agent: Optional filter by agent name
            action_type: Optional filter by action type
        
        Returns:
            Formatted string of relevant memories
        """
        memories = self.search(text, k=k*2)  # Fetch extra to allow for filtering
        
        # Apply filters if provided
        if agent or action_type:
            filtered = []
            for mem in memories:
                meta = mem['metadata']
                if agent and meta.get('agent') != agent:
                    continue
                if action_type and meta.get('action_type') != action_type:
                    continue
                filtered.append(mem)
            memories = filtered[:k]  # Trim back down to k
        else:
            memories = memories[:k]
        
        if not memories:
            return ""
        
        # Format into a string
        result = "RELEVANT PAST EXPERIENCES:\n\n"
        for i, mem in enumerate(memories, 1):
            meta = mem['metadata']
            timestamp = meta.get('timestamp', 'unknown time')
            agent_name = meta.get('agent', 'unknown agent')
            result += f"{i}. [{timestamp}] {agent_name}: {mem['text']}\n\n"
        
        return result

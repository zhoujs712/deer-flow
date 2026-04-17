"""ChromaDB-based memory storage provider for DeerFlow."""

import json
import logging
import os
from typing import Any

from deerflow.agents.memory.storage import (
    MemoryStorage,
    create_empty_memory,
    utc_now_iso_z,
)
from deerflow.config.agents_config import AGENT_NAME_PATTERN

logger = logging.getLogger(__name__)


class ChromaMemoryStorage(MemoryStorage):
    """ChromaDB-based memory storage provider.

    This implementation uses ChromaDB to store and retrieve memory data.
    It supports both in-memory and persistent ChromaDB instances.

    Configuration via environment variables:
    - CHROMADB_HOST: ChromaDB server host (default: None, uses local)
    - CHROMADB_PORT: ChromaDB server port (default: 8000)
    - CHROMADB_PERSIST_DIR: Directory for persistent storage (default: .chromadb)
    """

    def __init__(self):
        """Initialize the ChromaDB memory storage."""
        try:
            import chromadb
            from chromadb.utils import embedding_functions
        except ImportError:
            raise ImportError(
                "ChromaDB is not installed. "
                "Install it with: uv pip install chromadb>=0.5.0"
            )

        self._client = None
        self._embedding_fn = None
        self._collections = {}

        host = os.environ.get("CHROMADB_HOST")
        port = os.environ.get("CHROMADB_PORT", "8000")
        persist_dir = os.environ.get("CHROMADB_PERSIST_DIR", ".chromadb")

        if host:
            logger.info("Connecting to ChromaDB server at %s:%s", host, port)
            self._client = chromadb.HttpClient(host=host, port=int(port))
        else:
            logger.info("Using local ChromaDB with persist directory: %s", persist_dir)
            self._client = chromadb.PersistentClient(path=persist_dir)

        self._embedding_fn = embedding_functions.DefaultEmbeddingFunction()
        logger.info("ChromaMemoryStorage initialized successfully")

    def _get_collection_name(self, agent_name: str | None) -> str:
        """Get the collection name for a given agent."""
        if agent_name:
            if not AGENT_NAME_PATTERN.match(agent_name):
                raise ValueError(f"Invalid agent name {agent_name!r}")
            return f"memory_{agent_name}"
        return "memory_global"

    def _get_or_create_collection(self, agent_name: str | None):
        """Get or create a ChromaDB collection for the agent."""
        name = self._get_collection_name(agent_name)
        if name not in self._collections:
            self._collections[name] = self._client.get_or_create_collection(
                name=name,
                embedding_function=self._embedding_fn,
            )
        return self._collections[name]

    def load(self, agent_name: str | None = None) -> dict[str, Any]:
        """Load memory data from ChromaDB for the given agent.

        Args:
            agent_name: Name of the agent (None for global memory)

        Returns:
            Memory data dictionary
        """
        try:
            collection = self._get_or_create_collection(agent_name)
            results = collection.get(ids=["memory_main"], limit=1)

            if not results["documents"]:
                logger.debug("No memory found for agent %s, returning empty", agent_name)
                return create_empty_memory()

            memory_data = json.loads(results["documents"][0])
            logger.debug("Loaded memory for agent %s", agent_name)
            return memory_data

        except Exception as e:
            logger.warning("Failed to load memory from ChromaDB: %s", e, exc_info=True)
            return create_empty_memory()

    def reload(self, agent_name: str | None = None) -> dict[str, Any]:
        """Force reload memory data from ChromaDB.

        Args:
            agent_name: Name of the agent (None for global memory)

        Returns:
            Memory data dictionary
        """
        return self.load(agent_name)

    def save(self, memory_data: dict[str, Any], agent_name: str | None = None) -> bool:
        """Save memory data to ChromaDB.

        Args:
            memory_data: Memory data to save
            agent_name: Name of the agent (None for global memory)

        Returns:
            True if save was successful, False otherwise
        """
        try:
            collection = self._get_or_create_collection(agent_name)
            memory_data["lastUpdated"] = utc_now_iso_z()
            doc = json.dumps(memory_data, ensure_ascii=False)

            collection.upsert(
                documents=[doc],
                ids=["memory_main"],
                metadatas=[{"agent": agent_name or "global", "type": "memory"}],
            )

            logger.info("Memory saved to ChromaDB for agent: %s", agent_name)
            return True

        except Exception as e:
            logger.error("Failed to save memory to ChromaDB: %s", e, exc_info=True)
            return False

    def search_facts(
        self,
        query: str,
        agent_name: str | None = None,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """Semantic search for facts in memory.

        Args:
            query: Search query text
            agent_name: Name of the agent (None for global memory)
            top_k: Number of results to return

        Returns:
            List of matching facts with metadata
        """
        try:
            collection = self._get_or_create_collection(agent_name)
            memory_data = self.load(agent_name)
            facts = memory_data.get("facts", [])

            if not facts:
                return []

            fact_texts = [f.get("content", "") for f in facts]
            fact_ids = [str(i) for i in range(len(facts))]

            temp_collection = self._client.create_collection(
                name=f"temp_search_{agent_name or 'global'}",
                embedding_function=self._embedding_fn,
            )

            try:
                temp_collection.add(
                    documents=fact_texts,
                    ids=fact_ids,
                    metadatas=[{"index": i} for i in range(len(facts))],
                )

                results = temp_collection.query(
                    query_texts=[query],
                    n_results=min(top_k, len(facts)),
                )

                matched_facts = []
                for idx_str in results["ids"][0]:
                    idx = int(idx_str)
                    if idx < len(facts):
                        matched_facts.append(facts[idx])

                return matched_facts

            finally:
                self._client.delete_collection(temp_collection.name)

        except Exception as e:
            logger.error("Failed to search facts: %s", e, exc_info=True)
            return []

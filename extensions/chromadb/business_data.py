"""Business data management for ChromaDB integration."""

import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class BusinessDataManager:
    """Manager for business data storage and retrieval in ChromaDB."""

    def __init__(self, chroma_client):
        """Initialize the business data manager.

        Args:
            chroma_client: ChromaDB client instance
        """
        self._client = chroma_client
        self._collection = self._client.get_or_create_collection(
            name="business_terms",
            metadata={"purpose": "business terminology and domain knowledge"}
        )

    def store_business_terms(
        self,
        terms: List[Dict[str, Any]],
        namespace: str = "default"
    ) -> bool:
        """Store business terms in ChromaDB.

        Args:
            terms: List of business terms with definitions
            namespace: Namespace for organizing terms

        Each term should have:
            - term: str - The business term
            - definition: str - The definition
            - examples: List[str] - Example usage (optional)
            - category: str - Category (optional)

        Returns:
            bool: Success status
        """
        try:
            documents = []
            metadatas = []
            ids = []

            for i, term_data in enumerate(terms):
                term = term_data.get("term")
                definition = term_data.get("definition")
                examples = term_data.get("examples", [])
                category = term_data.get("category", "general")

                if not term or not definition:
                    logger.warning(f"Skipping term without term or definition: {term_data}")
                    continue

                # Create document content
                content_parts = [f"Term: {term}", f"Definition: {definition}"]
                if examples:
                    content_parts.append(f"Examples: {', '.join(examples)}")
                if category:
                    content_parts.append(f"Category: {category}")
                content = "\n".join(content_parts)

                documents.append(content)
                metadatas.append({
                    "term": term,
                    "category": category,
                    "namespace": namespace,
                    "type": "business_term"
                })
                ids.append(f"{namespace}_{term}_{i}")

            if documents:
                self._collection.upsert(
                    documents=documents,
                    metadatas=metadatas,
                    ids=ids
                )
                logger.info(f"Stored {len(documents)} business terms in namespace '{namespace}'")
                return True
            return False

        except Exception as e:
            logger.error("Failed to store business terms: %s", e, exc_info=True)
            return False

    def store_business_documents(
        self,
        documents: List[Dict[str, Any]],
        namespace: str = "default"
    ) -> bool:
        """Store business documents in ChromaDB.

        Args:
            documents: List of business documents
            namespace: Namespace for organizing documents

        Each document should have:
            - title: str - Document title
            - content: str - Document content
            - tags: List[str] - Tags (optional)
            - source: str - Source (optional)

        Returns:
            bool: Success status
        """
        try:
            doc_contents = []
            metadatas = []
            ids = []

            for i, doc in enumerate(documents):
                title = doc.get("title")
                content = doc.get("content")
                tags = doc.get("tags", [])
                source = doc.get("source", "unknown")

                if not title or not content:
                    logger.warning(f"Skipping document without title or content: {doc}")
                    continue

                doc_content = f"Title: {title}\nContent: {content}"
                if tags:
                    doc_content += f"\nTags: {', '.join(tags)}"
                if source:
                    doc_content += f"\nSource: {source}"

                doc_contents.append(doc_content)
                metadatas.append({
                    "title": title,
                    "source": source,
                    "tags": tags,
                    "namespace": namespace,
                    "type": "business_document"
                })
                ids.append(f"{namespace}_doc_{i}")

            if doc_contents:
                self._collection.upsert(
                    documents=doc_contents,
                    metadatas=metadatas,
                    ids=ids
                )
                logger.info(f"Stored {len(doc_contents)} business documents in namespace '{namespace}'")
                return True
            return False

        except Exception as e:
            logger.error("Failed to store business documents: %s", e, exc_info=True)
            return False

    def search_business_terms(
        self,
        query: str,
        namespace: Optional[str] = None,
        top_k: int = 5,
        category: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Search for business terms related to a query.

        Args:
            query: Search query
            namespace: Optional namespace filter
            top_k: Maximum number of results
            category: Optional category filter

        Returns:
            List of matching business terms
        """
        try:
            where = {"type": "business_term"}
            if namespace:
                where["namespace"] = namespace
            if category:
                where["category"] = category

            results = self._collection.query(
                query_texts=[query],
                n_results=top_k,
                where=where
            )

            matched_terms = []
            for i, doc in enumerate(results["documents"][0]):
                metadata = results["metadatas"][0][i]
                distance = results["distances"][0][i]
                
                # Parse the document content
                term_info = {}
                lines = doc.split('\n')
                for line in lines:
                    if line.startswith("Term: "):
                        term_info["term"] = line[6:].strip()
                    elif line.startswith("Definition: "):
                        term_info["definition"] = line[11:].strip()
                    elif line.startswith("Examples: "):
                        term_info["examples"] = line[10:].strip().split(", ")
                    elif line.startswith("Category: "):
                        term_info["category"] = line[10:].strip()
                
                term_info["metadata"] = metadata
                term_info["similarity"] = 1.0 - distance  # Convert distance to similarity
                matched_terms.append(term_info)

            return matched_terms

        except Exception as e:
            logger.error("Failed to search business terms: %s", e, exc_info=True)
            return []

    def search_business_documents(
        self,
        query: str,
        namespace: Optional[str] = None,
        top_k: int = 3,
        tags: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Search for business documents related to a query.

        Args:
            query: Search query
            namespace: Optional namespace filter
            top_k: Maximum number of results
            tags: Optional tag filters

        Returns:
            List of matching business documents
        """
        try:
            where = {"type": "business_document"}
            if namespace:
                where["namespace"] = namespace

            results = self._collection.query(
                query_texts=[query],
                n_results=top_k,
                where=where
            )

            matched_docs = []
            for i, doc in enumerate(results["documents"][0]):
                metadata = results["metadatas"][0][i]
                distance = results["distances"][0][i]
                
                # Filter by tags if specified
                if tags and "tags" in metadata:
                    doc_tags = metadata["tags"]
                    if not any(tag in doc_tags for tag in tags):
                        continue
                
                doc_info = {
                    "title": metadata.get("title", ""),
                    "source": metadata.get("source", ""),
                    "tags": metadata.get("tags", []),
                    "content": doc,
                    "similarity": 1.0 - distance
                }
                matched_docs.append(doc_info)

            return matched_docs

        except Exception as e:
            logger.error("Failed to search business documents: %s", e, exc_info=True)
            return []

    def get_all_terms(self, namespace: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all business terms.

        Args:
            namespace: Optional namespace filter

        Returns:
            List of all business terms
        """
        try:
            where = {"type": "business_term"}
            if namespace:
                where["namespace"] = namespace

            results = self._collection.get(
                where=where
            )

            terms = []
            for i, doc in enumerate(results["documents"]):
                metadata = results["metadatas"][i]
                term_info = {"metadata": metadata, "content": doc}
                terms.append(term_info)

            return terms

        except Exception as e:
            logger.error("Failed to get all terms: %s", e, exc_info=True)
            return []

    def clear_namespace(self, namespace: str) -> bool:
        """Clear all data in a namespace.

        Args:
            namespace: Namespace to clear

        Returns:
            bool: Success status
        """
        try:
            results = self._collection.get(
                where={"namespace": namespace}
            )

            if results["ids"]:
                self._collection.delete(ids=results["ids"])
                logger.info(f"Cleared {len(results['ids'])} items from namespace '{namespace}'")
            return True

        except Exception as e:
            logger.error(f"Failed to clear namespace '{namespace}': %s", e, exc_info=True)
            return False

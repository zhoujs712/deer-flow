"""Intent recognition with business term awareness."""

import logging
from typing import Dict, List, Optional, Any

from chromadb.storage import ChromaMemoryStorage
from chromadb.business_data import BusinessDataManager

logger = logging.getLogger(__name__)


class IntentRecognizer:
    """Intent recognizer with business term awareness."""

    def __init__(self, memory_storage: ChromaMemoryStorage):
        """Initialize the intent recognizer.

        Args:
            memory_storage: ChromaMemoryStorage instance
        """
        self._memory_storage = memory_storage
        # Access the ChromaDB client from the storage instance
        self._client = memory_storage._client
        self._business_manager = BusinessDataManager(self._client)

    def recognize_intent(
        self,
        user_input: str,
        namespace: str = "default",
        top_k_terms: int = 5,
        top_k_docs: int = 2
    ) -> Dict[str, Any]:
        """Recognize intent with business term awareness.

        Args:
            user_input: User input text
            namespace: Business data namespace
            top_k_terms: Number of business terms to return
            top_k_docs: Number of business documents to return

        Returns:
            Dict with intent analysis results
        """
        try:
            # Search for relevant business terms
            business_terms = self._business_manager.search_business_terms(
                query=user_input,
                namespace=namespace,
                top_k=top_k_terms
            )

            # Search for relevant business documents
            business_docs = self._business_manager.search_business_documents(
                query=user_input,
                namespace=namespace,
                top_k=top_k_docs
            )

            # Extract key business terms
            key_terms = [term["term"] for term in business_terms if term.get("similarity", 0) > 0.7]

            # Determine intent based on business terms and input
            intent = self._infer_intent(user_input, key_terms, business_terms)

            return {
                "user_input": user_input,
                "intent": intent,
                "key_business_terms": key_terms,
                "relevant_terms": business_terms,
                "relevant_documents": business_docs,
                "confidence": self._calculate_confidence(business_terms)
            }

        except Exception as e:
            logger.error("Failed to recognize intent: %s", e, exc_info=True)
            return {
                "user_input": user_input,
                "intent": "general_inquiry",
                "key_business_terms": [],
                "relevant_terms": [],
                "relevant_documents": [],
                "confidence": 0.0,
                "error": str(e)
            }

    def _infer_intent(
        self,
        user_input: str,
        key_terms: List[str],
        business_terms: List[Dict[str, Any]]
    ) -> str:
        """Infer intent based on input and business terms.

        Args:
            user_input: User input text
            key_terms: Key business terms
            business_terms: Detailed business terms with similarity scores

        Returns:
            Intent string
        """
        # Simple intent classification based on keywords and business terms
        input_lower = user_input.lower()

        # Check for specific intents
        if any(word in input_lower for word in ["help", "assist", "guide"]):
            return "help_request"
        elif any(word in input_lower for word in ["define", "what is", "meaning", "explain"]):
            return "definition_request"
        elif any(word in input_lower for word in ["example", "usage", "how to"]):
            return "example_request"
        elif any(word in input_lower for word in ["problem", "issue", "error", "trouble"]):
            return "problem_report"
        elif any(word in input_lower for word in ["report", "summary", "update"]):
            return "report_request"
        elif any(word in input_lower for word in ["policy", "rule", "guideline"]):
            return "policy_inquiry"

        # Intent based on business term categories
        categories = set()
        for term in business_terms:
            if term.get("similarity", 0) > 0.8:
                category = term.get("category", "")
                if category:
                    categories.add(category)

        if categories:
            if "product" in categories:
                return "product_inquiry"
            elif "process" in categories:
                return "process_inquiry"
            elif "service" in categories:
                return "service_inquiry"
            elif "policy" in categories:
                return "policy_inquiry"

        # Default intent
        return "general_inquiry"

    def _calculate_confidence(self, business_terms: List[Dict[str, Any]]) -> float:
        """Calculate confidence score based on business term matches.

        Args:
            business_terms: List of matched business terms

        Returns:
            Confidence score between 0.0 and 1.0
        """
        if not business_terms:
            return 0.0

        # Calculate average similarity score
        similarities = [term.get("similarity", 0) for term in business_terms]
        avg_similarity = sum(similarities) / len(similarities)

        # Adjust confidence based on number of matches
        match_count = len([s for s in similarities if s > 0.7])
        confidence = avg_similarity

        if match_count >= 3:
            confidence = min(1.0, confidence * 1.2)
        elif match_count == 0:
            confidence = max(0.1, confidence * 0.5)

        return round(confidence, 2)

    def enhance_prompt(
        self,
        user_input: str,
        namespace: str = "default"
    ) -> str:
        """Enhance prompt with business context.

        Args:
            user_input: User input
            namespace: Business data namespace

        Returns:
            Enhanced prompt with business context
        """
        analysis = self.recognize_intent(user_input, namespace)

        # Build enhanced prompt
        enhanced_prompt = f"User input: {user_input}\n"

        if analysis.get("key_business_terms"):
            terms_str = ", ".join(analysis["key_business_terms"])
            enhanced_prompt += f"Business terms detected: {terms_str}\n"

        if analysis.get("relevant_terms"):
            enhanced_prompt += "Relevant business definitions:\n"
            for term in analysis["relevant_terms"]:
                if term.get("similarity", 0) > 0.7:
                    enhanced_prompt += f"- {term.get('term')}: {term.get('definition', '')}\n"

        if analysis.get("relevant_documents"):
            enhanced_prompt += "Relevant business documents:\n"
            for doc in analysis["relevant_documents"]:
                if doc.get("similarity", 0) > 0.6:
                    enhanced_prompt += f"- {doc.get('title')} (Source: {doc.get('source')})\n"

        enhanced_prompt += f"Detected intent: {analysis.get('intent', 'general_inquiry')}\n"
        enhanced_prompt += f"Confidence: {analysis.get('confidence', 0.0)}\n"

        return enhanced_prompt


class IntentRecognitionTool:
    """Tool for intent recognition with business term awareness."""

    def __init__(self, memory_storage: ChromaMemoryStorage):
        """Initialize the intent recognition tool.

        Args:
            memory_storage: ChromaMemoryStorage instance
        """
        self._recognizer = IntentRecognizer(memory_storage)

    def recognize_intent(
        self,
        user_input: str,
        namespace: Optional[str] = None
    ) -> Dict[str, Any]:
        """Recognize intent from user input.

        Args:
            user_input: User input text
            namespace: Optional business data namespace

        Returns:
            Intent recognition result
        """
        return self._recognizer.recognize_intent(
            user_input,
            namespace=namespace or "default"
        )

    def enhance_prompt(
        self,
        user_input: str,
        namespace: Optional[str] = None
    ) -> str:
        """Enhance prompt with business context.

        Args:
            user_input: User input text
            namespace: Optional business data namespace

        Returns:
            Enhanced prompt
        """
        return self._recognizer.enhance_prompt(
            user_input,
            namespace=namespace or "default"
        )

    def store_business_terms(
        self,
        terms: List[Dict[str, Any]],
        namespace: Optional[str] = None
    ) -> bool:
        """Store business terms for intent recognition.

        Args:
            terms: List of business terms
            namespace: Optional namespace

        Returns:
            Success status
        """
        return self._recognizer._business_manager.store_business_terms(
            terms,
            namespace=namespace or "default"
        )

    def store_business_documents(
        self,
        documents: List[Dict[str, Any]],
        namespace: Optional[str] = None
    ) -> bool:
        """Store business documents for intent recognition.

        Args:
            documents: List of business documents
            namespace: Optional namespace

        Returns:
            Success status
        """
        return self._recognizer._business_manager.store_business_documents(
            documents,
            namespace=namespace or "default"
        )

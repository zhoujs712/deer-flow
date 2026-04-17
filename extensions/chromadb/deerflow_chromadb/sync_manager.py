"""Sync manager for dictionary data updates."""

import logging
import threading
import time
from typing import Dict, List, Optional, Any

from .sql_server import SQLServerExtractor
from .business_data import BusinessDataManager

logger = logging.getLogger(__name__)


class SyncManager:
    """Manager for synchronizing dictionary data from SQL Server to ChromaDB."""

    def __init__(self, chroma_client):
        """Initialize the sync manager.

        Args:
            chroma_client: ChromaDB client instance
        """
        self._chroma_client = chroma_client
        self._business_data_manager = BusinessDataManager(chroma_client)
        self._sql_extractor = SQLServerExtractor()
        self._sync_thread = None
        self._running = False
        self._interval_seconds = 3600  # Default: 1 hour

    def configure_sync(
        self,
        tables_config: List[Dict[str, Any]],
        connection_string: Optional[str] = None,
        interval_seconds: int = 3600
    ) -> bool:
        """Configure the synchronization settings.

        Args:
            tables_config: List of table configurations
            connection_string: SQL Server connection string
            interval_seconds: Sync interval in seconds

        Returns:
            bool: Success status
        """
        self._tables_config = tables_config
        self._interval_seconds = interval_seconds

        # Connect to SQL Server
        if connection_string:
            connected = self._sql_extractor.connect(connection_string)
        else:
            connected = self._sql_extractor.connect_from_env()

        if not connected:
            logger.error("Failed to connect to SQL Server for sync")
            return False

        return True

    def start_sync(self) -> bool:
        """Start the synchronization service.

        Returns:
            bool: Success status
        """
        if self._running:
            logger.warning("Sync service is already running")
            return True

        try:
            self._running = True
            self._sync_thread = threading.Thread(target=self._sync_loop, daemon=True)
            self._sync_thread.start()
            logger.info(f"Started sync service with interval {self._interval_seconds} seconds")
            return True
        except Exception as e:
            logger.error("Failed to start sync service: %s", e, exc_info=True)
            self._running = False
            return False

    def stop_sync(self) -> bool:
        """Stop the synchronization service.

        Returns:
            bool: Success status
        """
        if not self._running:
            logger.warning("Sync service is not running")
            return True

        try:
            self._running = False
            if self._sync_thread:
                self._sync_thread.join(timeout=5)
            logger.info("Stopped sync service")
            return True
        except Exception as e:
            logger.error("Failed to stop sync service: %s", e, exc_info=True)
            return False

    def sync_now(self) -> bool:
        """Manually trigger a synchronization.

        Returns:
            bool: Success status
        """
        return self._perform_sync()

    def _sync_loop(self):
        """Synchronization loop."""
        while self._running:
            try:
                self._perform_sync()
            except Exception as e:
                logger.error("Error in sync loop: %s", e, exc_info=True)
            
            # Wait for the next interval
            for _ in range(self._interval_seconds):
                if not self._running:
                    break
                time.sleep(1)

    def _perform_sync(self) -> bool:
        """Perform synchronization from SQL Server to ChromaDB.

        Returns:
            bool: Success status
        """
        try:
            logger.info("Starting synchronization from SQL Server to ChromaDB")

            # Extract terms from SQL Server
            terms = self._sql_extractor.extract_multiple_tables(self._tables_config)
            
            if not terms:
                logger.warning("No terms extracted from SQL Server")
                return False

            # Store terms in ChromaDB
            # Use a dedicated namespace for SQL Server dictionary data
            success = self._business_data_manager.store_business_terms(
                terms=terms,
                namespace="sql_server_dictionary"
            )

            if success:
                logger.info(f"Successfully synchronized {len(terms)} terms from SQL Server")
            else:
                logger.error("Failed to store terms in ChromaDB")

            return success

        except Exception as e:
            logger.error("Failed to perform sync: %s", e, exc_info=True)
            return False

    def is_running(self) -> bool:
        """Check if the sync service is running.

        Returns:
            bool: Running status
        """
        return self._running

    def get_sync_interval(self) -> int:
        """Get the current sync interval in seconds.

        Returns:
            int: Sync interval in seconds
        """
        return self._interval_seconds


def get_sync_manager(chroma_client) -> SyncManager:
    """Get a sync manager instance.

    Args:
        chroma_client: ChromaDB client instance

    Returns:
        SyncManager: Sync manager instance
    """
    return SyncManager(chroma_client)

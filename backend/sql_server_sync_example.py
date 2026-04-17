"""Example of SQL Server dictionary data synchronization to ChromaDB."""

import os
import time
import logging
from deerflow_chromadb import get_sync_manager
import chromadb

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Main function for SQL Server sync example."""
    logger.info("Starting SQL Server dictionary sync example")

    # Initialize ChromaDB client
    # For production, consider using a persistent directory
    chroma_client = chromadb.Client()

    # Create sync manager
    sync_manager = get_sync_manager(chroma_client)

    # Configure SQL Server connection and tables
    # Option 1: Use environment variables
    # Set these environment variables before running:
    # SQL_SERVER_SERVER, SQL_SERVER_DATABASE, SQL_SERVER_USER, SQL_SERVER_PASSWORD
    
    # Option 2: Use connection string directly
    # connection_string = "DRIVER={ODBC Driver 17 for SQL Server};SERVER=your_server;DATABASE=your_db;UID=your_user;PWD=your_password"

    # Define table configurations
    # Example: Extract from multiple dictionary tables
    tables_config = [
        {
            "table_name": "dbo.dictionary_terms",
            "term_column": "term",
            "definition_column": "definition",
            "category_column": "category",
            "example_column": "examples"
        },
        {
            "table_name": "dbo.product_terms",
            "term_column": "product_name",
            "definition_column": "description",
            "category_column": "product_category"
        }
    ]

    # Configure sync (using environment variables for connection)
    success = sync_manager.configure_sync(
        tables_config=tables_config,
        interval_seconds=3600  # 1 hour sync interval
    )

    if not success:
        logger.error("Failed to configure sync")
        return

    # Start the sync service
    success = sync_manager.start_sync()
    if not success:
        logger.error("Failed to start sync service")
        return

    logger.info("Sync service started successfully")
    logger.info(f"Sync interval: {sync_manager.get_sync_interval()} seconds")

    # Manually trigger an initial sync
    logger.info("Performing initial sync...")
    sync_success = sync_manager.sync_now()
    if sync_success:
        logger.info("Initial sync completed successfully")
    else:
        logger.error("Initial sync failed")

    # Keep the script running to demonstrate the sync service
    try:
        logger.info("Sync service is running. Press Ctrl+C to stop...")
        while True:
            time.sleep(60)  # Check every minute
            logger.info(f"Sync service status: {'Running' if sync_manager.is_running() else 'Stopped'}")
    except KeyboardInterrupt:
        logger.info("Stopping sync service...")
        sync_manager.stop_sync()
        logger.info("Sync service stopped")

if __name__ == "__main__":
    main()

"""SQL Server data extraction for business terms."""

import logging
import os
from typing import Any, Dict, List, Optional
import pyodbc

logger = logging.getLogger(__name__)


class SQLServerExtractor:
    """Extract business terms from SQL Server dictionary tables."""

    def __init__(self):
        """Initialize the SQL Server extractor."""
        self._connection = None

    def connect(self, connection_string: str) -> bool:
        """Connect to SQL Server.

        Args:
            connection_string: SQL Server connection string

        Returns:
            bool: Success status
        """
        try:
            self._connection = pyodbc.connect(connection_string)
            logger.info("Connected to SQL Server successfully")
            return True
        except Exception as e:
            logger.error("Failed to connect to SQL Server: %s", e, exc_info=True)
            return False

    def connect_from_env(self) -> bool:
        """Connect to SQL Server using environment variables.

        Environment variables:
            SQL_SERVER_CONNECTION_STRING: Full connection string
            or
            SQL_SERVER_SERVER: Server name
            SQL_SERVER_DATABASE: Database name
            SQL_SERVER_USER: Username
            SQL_SERVER_PASSWORD: Password

        Returns:
            bool: Success status
        """
        # Try full connection string first
        connection_string = os.environ.get("SQL_SERVER_CONNECTION_STRING")
        if connection_string:
            return self.connect(connection_string)

        # Build connection string from individual variables
        server = os.environ.get("SQL_SERVER_SERVER")
        database = os.environ.get("SQL_SERVER_DATABASE")
        user = os.environ.get("SQL_SERVER_USER")
        password = os.environ.get("SQL_SERVER_PASSWORD")

        if not all([server, database, user, password]):
            logger.error("Missing SQL Server connection environment variables")
            return False

        connection_string = (
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={server};"
            f"DATABASE={database};"
            f"UID={user};"
            f"PWD={password}"
        )

        return self.connect(connection_string)

    def extract_dictionary_terms(
        self,
        table_name: str,
        term_column: str = "term",
        definition_column: str = "definition",
        category_column: Optional[str] = None,
        example_column: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Extract dictionary terms from SQL Server table.

        Args:
            table_name: Name of the dictionary table
            term_column: Column name for terms
            definition_column: Column name for definitions
            category_column: Optional column name for categories
            example_column: Optional column name for examples

        Returns:
            List of business terms in the required format
        """
        if not self._connection:
            logger.error("Not connected to SQL Server")
            return []

        try:
            cursor = self._connection.cursor()

            # Build query
            columns = [term_column, definition_column]
            if category_column:
                columns.append(category_column)
            if example_column:
                columns.append(example_column)

            query = f"SELECT {', '.join(columns)} FROM {table_name}"
            logger.info(f"Executing query: {query}")

            cursor.execute(query)
            rows = cursor.fetchall()

            terms = []
            for row in rows:
                term_data = {
                    "term": row[0],
                    "definition": row[1]
                }

                if category_column and len(row) > 2 and row[2]:
                    term_data["category"] = row[2]
                else:
                    term_data["category"] = "general"

                if example_column and len(row) > 3 and row[3]:
                    # Split examples if stored as comma-separated string
                    examples = row[3].split(',') if isinstance(row[3], str) else [row[3]]
                    term_data["examples"] = [example.strip() for example in examples]
                else:
                    term_data["examples"] = []

                terms.append(term_data)

            logger.info(f"Extracted {len(terms)} terms from {table_name}")
            return terms

        except Exception as e:
            logger.error("Failed to extract dictionary terms: %s", e, exc_info=True)
            return []
        finally:
            if 'cursor' in locals():
                cursor.close()

    def extract_multiple_tables(
        self,
        tables_config: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Extract terms from multiple dictionary tables.

        Args:
            tables_config: List of table configurations
                Each config should have:
                - table_name: Name of the table
                - term_column: Column name for terms
                - definition_column: Column name for definitions
                - category_column: Optional column name for categories
                - example_column: Optional column name for examples

        Returns:
            Combined list of business terms
        """
        all_terms = []

        for config in tables_config:
            terms = self.extract_dictionary_terms(**config)
            all_terms.extend(terms)

        logger.info(f"Extracted total {len(all_terms)} terms from {len(tables_config)} tables")
        return all_terms

    def close(self):
        """Close the SQL Server connection."""
        if self._connection:
            try:
                self._connection.close()
                logger.info("Closed SQL Server connection")
            except Exception as e:
                logger.error("Failed to close SQL Server connection: %s", e)

    def __enter__(self):
        """Enter context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager and close connection."""
        self.close()


def get_sql_server_extractor() -> SQLServerExtractor:
    """Get a SQL Server extractor instance.

    Returns:
        SQLServerExtractor: Extractor instance
    """
    return SQLServerExtractor()

import pytest
import psycopg2
from unittest.mock import patch, MagicMock
from datetime import datetime
from mIAm.postgres_db.postgres_db_manager import PostgresDBManager


@pytest.fixture
def db_manager():
    """Create a DB manager with mocked connection."""
    # Create the manager with a dummy connection string
    with patch('psycopg2.connect') as mock_connect:
        # Mock the connection and cursor
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Configure the cursor to return specific values
        mock_cursor.__enter__.return_value = mock_cursor
        
        # Create the manager
        manager = PostgresDBManager("postgresql://test:test@localhost:5432/test", initialize_db=False)
        
        # Yield the manager and the mocked cursor for tests to use
        yield manager, mock_cursor


class TestThreadManagement:
    """Test thread management methods in PostgresDBManager."""

    def test_create_thread(self, db_manager):
        """Test creating a new thread."""
        manager, mock_cursor = db_manager
        
        # Configure the cursor to return valid data
        mock_cursor.fetchone.side_effect = [
            (1,),  # User exists check
            (123,)  # Thread ID
        ]
        
        # Call the method
        user_id = 1
        thread_name = "Test Thread"
        thread_id = manager.create_thread(user_id, thread_name)
        
        # Assertions
        assert thread_id == 123
        
        # Verify SQL execution
        execute_calls = mock_cursor.execute.call_args_list
        
        # First call - check if user exists
        assert "SELECT id FROM users WHERE id = %s" in execute_calls[0][0][0]
        assert execute_calls[0][0][1] == (user_id,)
        
        # Second call - insert the thread
        assert "INSERT INTO threads" in execute_calls[1][0][0]
        assert execute_calls[1][0][1] == (user_id, thread_name)
        
        # Third call - update user's thread count
        assert "UPDATE users SET thread_number" in execute_calls[2][0][0]
        assert execute_calls[2][0][1] == (user_id,)

    def test_create_thread_user_not_found(self, db_manager):
        """Test creating a thread for a non-existent user."""
        manager, mock_cursor = db_manager
        
        # Configure the cursor to return no user
        mock_cursor.fetchone.return_value = None
        
        # Call the method and check for exception
        with pytest.raises(Exception):
            manager.create_thread(999, "Test Thread")

    def test_get_user_threads(self, db_manager):
        """Test retrieving user threads."""
        manager, mock_cursor = db_manager
        
        # Mock the return value for threads
        thread_data = [
            {
                'id': 1, 
                'thread_name': 'Thread 1', 
                'is_active': True,
                'created_at': datetime.now(),
                'updated_at': datetime.now()
            },
            {
                'id': 2, 
                'thread_name': 'Thread 2', 
                'is_active': True,
                'created_at': datetime.now(),
                'updated_at': datetime.now()
            }
        ]
        mock_cursor.fetchall.return_value = thread_data
        
        # Call the method
        user_id = 1
        threads = manager.get_user_threads(user_id)
        
        # Assertions
        assert len(threads) == 2
        assert threads[0]['id'] == 1
        assert threads[1]['thread_name'] == 'Thread 2'
        
        # Verify SQL execution
        execute_call = mock_cursor.execute.call_args
        assert "FROM threads t" in execute_call[0][0]
        assert "WHERE t.user_id = %s" in execute_call[0][0]
        assert execute_call[0][1] == (user_id,)

    def test_get_user_threads_empty(self, db_manager):
        """Test retrieving threads for a user with no threads."""
        manager, mock_cursor = db_manager
        
        # Mock empty return
        mock_cursor.fetchall.return_value = []
        
        # Call the method
        threads = manager.get_user_threads(1)
        
        # Assertions
        assert threads == []


if __name__ == "__main__":
    pytest.main(["-xvs", __file__])
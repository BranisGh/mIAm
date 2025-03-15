import os
import logging
from typing import Dict, List, Optional, Any, Tuple, Union
import psycopg2
from psycopg2.extras import RealDictCursor
import json
from datetime import datetime, date
from uuid import uuid4
from contextlib import contextmanager
import bcrypt



class PostgresDBManager:
    """PostgreSQL database manager for LangGraph with complete user management."""
    
    def __init__(self, conn_string: str, initialize_db: bool = True):
        """
        Initialize the database manager.
        
        Args:
            conn_string: PostgreSQL connection string
            initialize_db: If True, initialize tables if they don't exist
        """
        self.conn_string = conn_string
        
        if initialize_db:
            self._initialize_database()
    
    @contextmanager
    def connection(self):
        """Provide a transactional scope around a series of database operations."""
        connection = psycopg2.connect(self.conn_string)
        try:
            yield connection
            connection.commit()
        except Exception as e:
            connection.rollback()
            print(f"Database error: {str(e)}")
            raise e # Re-raise the exception
        finally:
            connection.close()

    @contextmanager
    def cursor(self, cursor_factory=None):
        """Provide a cursor for database operations."""
        with self.connection() as connection:
            cursor = connection.cursor(cursor_factory=cursor_factory)
            try:
                yield cursor
            finally:
                cursor.close()
                
    def _initialize_database(self) -> None:
        """Initialize the database with necessary tables."""
        try:
            with self.cursor() as cursor:
                # Users table
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    first_name VARCHAR(50) NOT NULL,
                    last_name VARCHAR(50) NOT NULL,
                    email VARCHAR(100) UNIQUE NOT NULL,
                    password VARCHAR(100) NOT NULL,
                    phone VARCHAR(15) UNIQUE,
                    birth_date DATE,
                    address TEXT,
                    city VARCHAR(50),
                    country VARCHAR(50),
                    thread_number INT DEFAULT 0,
                    token_number INT DEFAULT 0,
                    last_login TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """)
                
                # Threads (conversations) table
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS threads (
                    id SERIAL PRIMARY KEY,
                    user_id INT REFERENCES users(id) ON DELETE CASCADE,
                    thread_name VARCHAR(100),
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """)
                
                print("Database initialized successfully")
        except Exception as e:
            print(f"Failed to initialize database: {str(e)}")
            raise e
    
    def _hash_password(self, password: str) -> str:
        """Hash a password using bcrypt."""
        password_bytes = password.encode('utf-8')
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password_bytes, salt)
        return hashed.decode('utf-8')
    
    def _verify_password(self, stored_password: str, provided_password: str) -> bool:
        """Verify a password against its hashed version."""
        stored_bytes = stored_password.encode('utf-8')
        provided_bytes = provided_password.encode('utf-8')
        return bcrypt.checkpw(provided_bytes, stored_bytes)
    
    def register_user(
            self,
            first_name: str,
            last_name: str,
            email: str,
            password: str,
            phone: Optional[str] = None,
            birth_date: Optional[Union[str, date]] = None,
            address: Optional[str] = None,
            city: Optional[str] = None,
            country: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Register a new user in the database.
        
        Args:
            first_name: User's first name
            last_name: User's last name
            email: User's email (unique)
            password: Plain text password
            phone: Phone number (optional)
            birth_date: Birth date (optional)
            address: Address (optional)
            city: City (optional)
            country: Country (optional)
            
        Returns:
            ID of the created user
            
        Raises:
            DatabaseError: If registration fails
        """
        try:
            # Convert birth date if it's a string
            if isinstance(birth_date, str) and birth_date:
                birth_date = datetime.strptime(birth_date, "%Y-%m-%d").date()
            
            # Hash the password
            hashed_password = self._hash_password(password)
            
            with self.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(
                    """
                    INSERT INTO users 
                    (first_name, last_name, email, password, phone, birth_date, address, city, country) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (first_name, last_name, email, hashed_password, phone, birth_date, address, city, country)
                )
                cursor.execute(
                    """SELECT * FROM users WHERE email = %s
                    """,
                    (email,)
                )
                user = cursor.fetchone()
                if not user:
                    print(f"Registration failed: Email {email} not found")
                    raise
            
            # Remove password from return dictionary
            del user['password']
                    
            print(f"User registered successfully: \n {user} )")
            return dict(user)
                
        except psycopg2.errors.UniqueViolation:
            print(f"Registration failed: Email {email} already exists")
            raise 
        except Exception as e:
            print(f"Registration error: {str(e)}")
            raise e
    
    def authenticate_user(self, email: str, password: str) -> Dict[str, Any]:
        """
        Authenticate a user and update their last login.
        
        Args:
            email: User's email
            password: Plain text password
            
        Returns:
            Dictionary containing user information
            
        Raises:
            AuthenticationError: If authentication fails
        """
        try:
            with self.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(
                    "SELECT * FROM users WHERE email = %s",
                    (email,)
                )
                user = cursor.fetchone()
                
                if not user:
                    print(f"Authentication failed: Email {email} not found")
                    raise
                
                if not self._verify_password(user['password'], password):
                    print(f"Authentication failed: Incorrect password for {email}")
                    raise 
                
                # Update last login timestamp
                cursor.execute(
                    "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = %s",
                    (user['id'],)
                )
                
                # Remove password from return dictionary
                del user['password']
                
                print(f"User authenticated successfully: {email}")
                return dict(user)
                
        except Exception as e:
            raise e
        except Exception as e:
            print(f"Authentication error: {str(e)}")
            raise e
    
    def get_user_profile(self, user_id: int) -> Dict[str, Any]:
        """
        Get a user's profile.
        
        Args:
            user_id: User ID
            
        Returns:
            Dictionary containing user information (without password)
        """
        try:
            with self.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(
                    """
                    SELECT id, first_name, last_name, email, phone, birth_date, 
                           address, city, country, thread_number, token_number,
                           created_at, last_login
                    FROM users WHERE id = %s
                    """,
                    (user_id,)
                )
                user = cursor.fetchone()
                
                if not user:
                    raise 
                
                return dict(user)
        except Exception as e:
            print(f"Error getting user profile: {str(e)}")
            raise e
    
    def update_user_profile(
            self,
            user_id: int,
            first_name: Optional[str] = None,
            last_name: Optional[str] = None,
            phone: Optional[str] = None,
            birth_date: Optional[Union[str, date]] = None,
            address: Optional[str] = None,
            city: Optional[str] = None,
            country: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update a user's profile.
        
        Args:
            user_id: User ID
            first_name: New first name (optional)
            last_name: New last name (optional)
            phone: New phone number (optional)
            birth_date: New birth date (optional)
            address: New address (optional)
            city: New city (optional)
            country: New country (optional)
            
        Returns:
            Dictionary containing updated information
        """
        # Convert birth date if it's a string
        if isinstance(birth_date, str) and birth_date:
            birth_date = datetime.strptime(birth_date, "%Y-%m-%d").date()
        
        # Build query dynamically
        update_fields = []
        params = []
        
        if first_name is not None:
            update_fields.append("first_name = %s")
            params.append(first_name)
        
        if last_name is not None:
            update_fields.append("last_name = %s")
            params.append(last_name)
        
        if phone is not None:
            update_fields.append("phone = %s")
            params.append(phone)
        
        if birth_date is not None:
            update_fields.append("birth_date = %s")
            params.append(birth_date)
        
        if address is not None:
            update_fields.append("address = %s")
            params.append(address)
        
        if city is not None:
            update_fields.append("city = %s")
            params.append(city)
        
        if country is not None:
            update_fields.append("country = %s")
            params.append(country)
        
        if not update_fields:
            return self.get_user_profile(user_id)
        
        try:
            with self.cursor() as cursor:
                query = f"UPDATE users SET {', '.join(update_fields)} WHERE id = %s"
                params.append(user_id)
                cursor.execute(query, params)
                
                if cursor.rowcount == 0:
                    raise 
                
                return self.get_user_profile(user_id)
                
        except Exception as e:
            print("Error updating user profile: {str(e)}")
            raise e
        
    def change_password(self, user_id: int, current_password: str, new_password: str) -> bool:
        """
        Change a user's password.
        
        Args:
            user_id: User ID
            current_password: Current password
            new_password: New password
            
        Returns:
            True if change was successful
            
        Raises:
            AuthenticationError: If current password is incorrect
        """
        try:
            with self.cursor() as cursor:
                # Verify current password
                cursor.execute(
                    "SELECT password FROM users WHERE id = %s",
                    (user_id,)
                )
                result = cursor.fetchone()
                
                if not result:
                    print(f"User ID {user_id} not found")
                    raise 
                
                stored_password = result[0]
                
                if not self._verify_password(stored_password, current_password):
                    print(f"Incorrect password for user ID {user_id}")
                    raise 
                
                # Update password
                hashed_password = self._hash_password(new_password)
                cursor.execute(
                    "UPDATE users SET password = %s WHERE id = %s",
                    (hashed_password, user_id)
                )
                
                print(f"Password changed successfully for user ID {user_id}")
                return True
                
        except Exception as e:
            print(f"Error changing password: {str(e)}")
            raise f"Unable to change password: {str(e)}"
    
    
    def delete_user(self, user_id: int) -> bool:
        """
        Remove a user from the database.   
        
        Args:
            user_id (int): _description_

        Returns:
            bool: _description_
        """
        try:
            with self.cursor() as cursor:
                threads = self.get_user_threads(user_id)
                for thread in threads:
                    self.delete_thread(thread['id'])
                cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
                return True
        except Exception as e:  
            print(f"Error deleting user: {str(e)}")
    
    
    def create_thread(self, user_id: int, thread_name: Optional[str] = None) -> int:
        """
        Create a new thread (conversation) for a user.
        
        Args:
            user_id: User ID
            thread_name: Optional name for the thread
            
        Returns:
            Thread ID
        """
        try:
            with self.cursor() as cursor:
                # Check if user exists
                cursor.execute("SELECT id FROM users WHERE id = %s", (user_id,))
                if not cursor.fetchone():
                    raise 
                
                # Create thread
                cursor.execute(
                    """
                    INSERT INTO threads (user_id, thread_name)
                    VALUES (%s, %s)
                    RETURNING id
                    """,
                    (user_id, thread_name or f"Thread {datetime.now().strftime('%Y-%m-%d %H:%M')}")
                )
                thread_id = cursor.fetchone()[0]
                
                # Increment thread count for user
                cursor.execute(
                    "UPDATE users SET thread_number = thread_number + 1 WHERE id = %s",
                    (user_id,)
                )
                
                print(f"Thread created successfully: {thread_id} for user {user_id}")
                return thread_id
                
        except Exception as e:
            print(f"Error creating thread: {str(e)}")
            raise e
    
    def get_user_threads(self, user_id: int) -> List[Dict[str, Any]]:
        """
        Get all threads (conversations) for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            List of thread dictionaries
        """
        try:
            with self.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(
                    """
                    SELECT t.id, t.thread_name, t.is_active, t.created_at, t.updated_at 
                    FROM threads t
                    WHERE t.user_id = %s
                    ORDER BY t.created_at DESC;
                    """, (user_id,))
                threads = cursor.fetchall()
                return [dict(thread) for thread in threads]
                
        except Exception as e:
            print(f"Error getting user threads: {str(e)}")
            raise e
    
    def get_thread_details(self, thread_id: int) -> Dict[str, Any]:
        """
        Get details of a specific thread.
        
        Args:
            thread_id: Thread ID
            
        Returns:
            Thread details dictionary
        """
        try:
            with self.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(
                    """
                    SELECT t.id, t.user_id, t.thread_name, t.is_active, t.created_at, t.updated_at,
                           (SELECT COUNT(*) FROM messages m WHERE m.thread_id = t.id) as message_count
                    FROM threads t
                    WHERE t.id = %s
                    """,
                    (thread_id,)
                )
                thread = cursor.fetchone()
                
                if not thread:
                    raise 
                
                return dict(thread)
                
        except Exception as e:
            print(f"Error getting thread details: {str(e)}")
            raise e
    
    def update_thread(self, thread_id: int, thread_name: str = None, is_active: bool = None) -> Dict[str, Any]:
        """
        Update a thread's details.
        
        Args:
            thread_id: Thread ID
            thread_name: New thread name (optional)
            is_active: New active status (optional)
            
        Returns:
            Updated thread details
        """
        update_fields = []
        params = []
        
        if thread_name is not None:
            update_fields.append("thread_name = %s")
            params.append(thread_name)
        
        if is_active is not None:
            update_fields.append("is_active = %s")
            params.append(is_active)
        
        if not update_fields:
            return self.get_thread_details(thread_id)
        
        # Always update the updated_at timestamp
        update_fields.append("updated_at = CURRENT_TIMESTAMP")
        
        try:
            with self.cursor() as cursor:
                query = f"UPDATE threads SET {', '.join(update_fields)} WHERE id = %s"
                params.append(thread_id)
                cursor.execute(query, params)
                
                if cursor.rowcount == 0:
                    raise 
                
                return self.get_thread_details(thread_id)
                
        except Exception as e:
            print(f"Error updating thread: {str(e)}")
            raise 
    
    def delete_thread(self, thread_id: int) -> bool:
        """
        Delete a thread and all associated messages and checkpoints.
        
        Args:
            thread_id: Thread ID
            
        Returns:
            True if deletion was successful
        """
        try:
            with self.cursor() as cursor:
                 # Check if thread exists and get user_id
                cursor.execute(
                    "SELECT user_id FROM threads WHERE id = %s",
                    (thread_id,)
                )
                result = cursor.fetchone()
                
                if not result:
                    print(f"Thread ID {thread_id} not found")
                    raise 
                
                user_id = result[0]
                
                # Delete all messages in the thread
                cursor.execute("DELETE FROM checkpoint_blobs where thread_id = %s" ,(str(thread_id),))
                cursor.execute("DELETE FROM checkpoint_writes where thread_id = %s", (str(thread_id),))
                cursor.execute("DELETE FROM checkpoints where thread_id = %s", (str(thread_id),))
                cursor.execute("DELETE FROM threads where id = %s", (thread_id,))
                
                # Decrement thread count for user
                cursor.execute(
                    "UPDATE users SET thread_number = thread_number - 1 WHERE id = %s",
                    (user_id,)
                )
                
                print(f"Thread {thread_id} deleted successfully")
                return True
                
        except Exception as e:
            print(f"Error deleting thread: {str(e)}")
            raise e
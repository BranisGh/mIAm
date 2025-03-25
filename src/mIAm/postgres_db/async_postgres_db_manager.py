import os
import logging
from typing import Dict, List, Optional, Any, Tuple, Union
import asyncio
import asyncpg
from datetime import datetime, date
from uuid import uuid4
import bcrypt

class AsyncPostgresDBManager:
    """Asynchronous PostgreSQL database manager for LangGraph with complete user management."""
    
    def __init__(self, conn_string: str, initialize_db: bool = True):
        """
        Initialize the database manager.
        
        Args:
            conn_string: PostgreSQL connection string
            initialize_db: If True, initialize tables if they don't exist
        """
        self.conn_string = conn_string
        self._pool = None
        
        if initialize_db:
            self._initialize_database()
    
    async def _get_connection_pool(self):
        """Create a connection pool if it doesn't exist."""
        if self._pool is None:
            try:
                self._pool = await asyncpg.create_pool(
                    dsn=self.conn_string,
                    min_size=1,
                    max_size=10
                )
            except Exception as e:
                print(f"Failed to create connection pool: {str(e)}")
                raise
        return self._pool
    
    async def _initialize_database(self) -> None:
        """Initialize the database with necessary tables."""
        try:
            async with await self._get_connection_pool() as connection:
                async with connection.transaction():
                    # Users table
                    await connection.execute("""
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
                    await connection.execute("""
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
            raise
    
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
    
    async def register_user(
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
        Register a new user in the database asynchronously.
        
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
            Dictionary of created user information
            
        Raises:
            DatabaseError: If registration fails
        """
        try:
            # Convert birth date if it's a string
            if isinstance(birth_date, str) and birth_date:
                birth_date = datetime.strptime(birth_date, "%Y-%m-%d").date()
            
            # Hash the password
            hashed_password = self._hash_password(password)
            
            async with await self._get_connection_pool() as connection:
                async with connection.transaction():
                    user = await connection.fetchrow(
                        """
                        INSERT INTO users 
                        (first_name, last_name, email, password, phone, birth_date, address, city, country) 
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                        RETURNING *
                        """,
                        first_name, last_name, email, hashed_password, phone, 
                        birth_date, address, city, country
                    )
                    
                    # Remove password from return dictionary
                    user_dict = dict(user)
                    del user_dict['password']
                    
                    print(f"User registered successfully: \n {user_dict}")
                    return user_dict
                
        except asyncpg.UniqueViolationError:
            print(f"Registration failed: Email {email} already exists")
            raise 
        except Exception as e:
            print(f"Registration error: {str(e)}")
            raise
    
    async def authenticate_user(self, email: str, password: str) -> Dict[str, Any]:
        """
        Authenticate a user and update their last login asynchronously.
        
        Args:
            email: User's email
            password: Plain text password
            
        Returns:
            Dictionary containing user information
            
        Raises:
            AuthenticationError: If authentication fails
        """
        try:
            async with await self._get_connection_pool() as connection:
                async with connection.transaction():
                    # Fetch user by email
                    user = await connection.fetchrow(
                        "SELECT * FROM users WHERE email = $1",
                        email
                    )
                    
                    if not user:
                        print(f"Authentication failed: Email {email} not found")
                        raise ValueError("User not found")
                    
                    # Verify password
                    if not self._verify_password(user['password'], password):
                        print(f"Authentication failed: Incorrect password for {email}")
                        raise ValueError("Incorrect password")
                    
                    # Update last login timestamp
                    await connection.execute(
                        "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = $1",
                        user['id']
                    )
                    
                    # Remove password from return dictionary
                    user_dict = dict(user)
                    del user_dict['password']
                    
                    print(f"User authenticated successfully: {email}")
                    return user_dict
                
        except Exception as e:
            print(f"Authentication error: {str(e)}")
            raise
    
    async def get_user_profile(self, user_id: int) -> Dict[str, Any]:
        """
        Get a user's profile asynchronously.
        
        Args:
            user_id: User ID
            
        Returns:
            Dictionary containing user information (without password)
        """
        try:
            async with await self._get_connection_pool() as connection:
                user = await connection.fetchrow(
                    """
                    SELECT id, first_name, last_name, email, phone, birth_date, 
                           address, city, country, thread_number, token_number,
                           created_at, last_login
                    FROM users WHERE id = $1
                    """,
                    user_id
                )
                
                if not user:
                    raise ValueError(f"User with ID {user_id} not found")
                
                return dict(user)
        except Exception as e:
            print(f"Error getting user profile: {str(e)}")
            raise
    
    async def update_user_profile(
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
        Update a user's profile asynchronously.
        
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
        params = [user_id]
        
        if first_name is not None:
            update_fields.append(f"first_name = ${len(params)+1}")
            params.append(first_name)
        
        if last_name is not None:
            update_fields.append(f"last_name = ${len(params)+1}")
            params.append(last_name)
        
        if phone is not None:
            update_fields.append(f"phone = ${len(params)+1}")
            params.append(phone)
        
        if birth_date is not None:
            update_fields.append(f"birth_date = ${len(params)+1}")
            params.append(birth_date)
        
        if address is not None:
            update_fields.append(f"address = ${len(params)+1}")
            params.append(address)
        
        if city is not None:
            update_fields.append(f"city = ${len(params)+1}")
            params.append(city)
        
        if country is not None:
            update_fields.append(f"country = ${len(params)+1}")
            params.append(country)
        
        # If no fields to update, return current profile
        if not update_fields:
            return await self.get_user_profile(user_id)
        
        try:
            async with await self._get_connection_pool() as connection:
                async with connection.transaction():
                    query = f"UPDATE users SET {', '.join(update_fields)} WHERE id = $1"
                    await connection.execute(query, *params)
                    
                    return await self.get_user_profile(user_id)
                
        except Exception as e:
            print(f"Error updating user profile: {str(e)}")
            raise
    
    async def change_password(self, user_id: int, current_password: str, new_password: str) -> bool:
        """
        Change a user's password asynchronously.
        
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
            async with await self._get_connection_pool() as connection:
                async with connection.transaction():
                    # Verify current password
                    result = await connection.fetchrow(
                        "SELECT password FROM users WHERE id = $1",
                        user_id
                    )
                    
                    if not result:
                        print(f"User ID {user_id} not found")
                        raise ValueError("User not found")
                    
                    stored_password = result['password']
                    
                    if not self._verify_password(stored_password, current_password):
                        print(f"Incorrect password for user ID {user_id}")
                        raise ValueError("Incorrect current password")
                    
                    # Update password
                    hashed_password = self._hash_password(new_password)
                    await connection.execute(
                        "UPDATE users SET password = $1 WHERE id = $2",
                        hashed_password, user_id
                    )
                    
                    print(f"Password changed successfully for user ID {user_id}")
                    return True
                
        except Exception as e:
            print(f"Error changing password: {str(e)}")
            raise
    
    async def delete_user(self, user_id: int) -> bool:
        """
        Remove a user from the database asynchronously.   
        
        Args:
            user_id: User ID to delete

        Returns:
            bool: True if deletion was successful
        """
        try:
            async with await self._get_connection_pool() as connection:
                async with connection.transaction():
                    # Get and delete user threads first
                    threads = await self.get_user_threads(user_id)
                    for thread in threads:
                        await self.delete_thread(thread['id'])
                    
                    # Delete the user
                    await connection.execute(
                        "DELETE FROM users WHERE id = $1", 
                        user_id
                    )
                    
                    return True
        except Exception as e:  
            print(f"Error deleting user: {str(e)}")
            raise
    
    async def create_thread(self, user_id: int, thread_name: Optional[str] = None) -> int:
        """
        Create a new thread (conversation) for a user asynchronously.
        
        Args:
            user_id: User ID
            thread_name: Optional name for the thread
            
        Returns:
            Thread ID
        """
        try:
            async with await self._get_connection_pool() as connection:
                async with connection.transaction():
                    # Check if user exists
                    user = await connection.fetchrow(
                        "SELECT id FROM users WHERE id = $1", 
                        user_id
                    )
                    if not user:
                        raise ValueError(f"User {user_id} not found")
                    
                    # Create thread
                    thread = await connection.fetchrow(
                        """
                        INSERT INTO threads (user_id, thread_name)
                        VALUES ($1, $2)
                        RETURNING id
                        """,
                        user_id, 
                        thread_name or f"Thread {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                    )
                    
                    # Increment thread count for user
                    await connection.execute(
                        "UPDATE users SET thread_number = thread_number + 1 WHERE id = $1",
                        user_id
                    )
                    
                    thread_id = thread['id']
                    print(f"Thread created successfully: {thread_id} for user {user_id}")
                    return thread_id
                
        except Exception as e:
            print(f"Error creating thread: {str(e)}")
            raise
    
    async def get_user_threads(self, user_id: int) -> List[Dict[str, Any]]:
        """
        Get all threads (conversations) for a user asynchronously.
        
        Args:
            user_id: User ID
            
        Returns:
            List of thread dictionaries
        """
        try:
            async with await self._get_connection_pool() as connection:
                threads = await connection.fetch(
                    """
                    SELECT t.id, t.thread_name, t.is_active, t.created_at, t.updated_at 
                    FROM threads t
                    WHERE t.user_id = $1
                    ORDER BY t.created_at DESC;
                    """, user_id)
                return [dict(thread) for thread in threads]
                
        except Exception as e:
            print(f"Error getting user threads: {str(e)}")
            raise
    
    async def get_thread_details(self, thread_id: int) -> Dict[str, Any]:
        """
        Get details of a specific thread asynchronously.
        
        Args:
            thread_id: Thread ID
            
        Returns:
            Thread details dictionary
        """
        try:
            async with await self._get_connection_pool() as connection:
                thread = await connection.fetchrow(
                    """
                    SELECT t.id, t.user_id, t.thread_name, t.is_active, t.created_at, t.updated_at,
                           (SELECT COUNT(*) FROM messages m WHERE m.thread_id = t.id) as message_count
                    FROM threads t
                    WHERE t.id = $1
                    """,
                    thread_id
                )
                
                if not thread:
                    raise ValueError(f"Thread {thread_id} not found")
                
                return dict(thread)
                
        except Exception as e:
            print(f"Error getting thread details: {str(e)}")
            raise
    
    async def update_thread(self, thread_id: int, thread_name: str = None, is_active: bool = None) -> Dict[str, Any]:
        """
        Update a thread's details asynchronously.
        
        Args:
            thread_id: Thread ID
            thread_name: New thread name (optional)
            is_active: New active status (optional)
            
        Returns:
            Updated thread details
        """
        update_fields = []
        params = [thread_id]
        
        if thread_name is not None:
            update_fields.append(f"thread_name = ${len(params)+1}")
            params.append(thread_name)
        
        if is_active is not None:
            update_fields.append(f"is_active = ${len(params)+1}")
            params.append(is_active)
        
        # If no fields to update, return current thread details
        if not update_fields:
            return await self.get_thread_details(thread_id)
        
        # Always update the updated_at timestamp
        update_fields.append("updated_at = CURRENT_TIMESTAMP")
        
        try:
            async with await self._get_connection_pool() as connection:
                async with connection.transaction():
                    query = f"UPDATE threads SET {', '.join(update_fields)} WHERE id = $1"
                    await connection.execute(query, *params)
                    
                    return await self.get_thread_details(thread_id)
                
        except Exception as e:
            print(f"Error updating thread: {str(e)}")
            raise
    
    async def delete_thread(self, thread_id: int) -> bool:
        """
        Delete a thread and all associated messages and checkpoints asynchronously.
        
        Args:
            thread_id: Thread ID
            
        Returns:
            True if deletion was successful
        """
        try:
            async with await self._get_connection_pool() as connection:
                async with connection.transaction():
                    # Check if thread exists and get user_id
                    thread = await connection.fetchrow(
                        "SELECT user_id FROM threads WHERE id = $1",
                        thread_id
                    )
                    
                    if not thread:
                        print(f"Thread ID {thread_id} not found")
                        raise ValueError("Thread not found")
                    
                    user_id = thread['user_id']
                    
                    # Delete all associated records
                    await connection.execute("DELETE FROM checkpoint_blobs WHERE thread_id = $1", str(thread_id))
                    await connection.execute("DELETE FROM checkpoint_writes WHERE thread_id = $1", str(thread_id))
                    await connection.execute("DELETE FROM checkpoints WHERE thread_id = $1", str(thread_id))
                    await connection.execute("DELETE FROM threads WHERE id = $1", thread_id)
                    
                    # Decrement thread count for user
                    await connection.execute(
                        "UPDATE users SET thread_number = thread_number - 1 WHERE id = $1",
                        user_id
                    )
                    
                    print(f"Thread {thread_id} deleted successfully")
                    return True
                
        except Exception as e:
            print(f"Error deleting thread: {str(e)}")
            raise
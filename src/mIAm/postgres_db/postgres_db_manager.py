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
import re
from mIAm import setup_logger
from mIAm.postgres_db.exceptions import(
    InvalidAuthenticationDataError, 
    DatabaseConnectionError, 
    InvalidRegestrationDataError, 
    InvalidFirstNameError, 
    InvalidLastNameError, 
    InvalidEmailError, 
    InvalidPhoneError,
    InvalidBirthDateError,
    InvalidPasswordError,
    InvalidAddressError,
    InvalidCityError,
    InvalidCountryError,
    UserAlreadyExistsError,
    UserNotFoundError,
    InvalidCredentialsError
)

# Initialize logger
LOGGER = setup_logger(
    console_logging_enabled=False, 
    log_level=logging.INFO
)


# Database manager
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
            LOGGER.info("Database operation successful")
        except Exception as e:
            connection.rollback()
            LOGGER.error(f"Database connexion error: {str(e)}")
            raise DatabaseConnectionError(f"connexion error: {str(e)}")
        finally:
            LOGGER.info("Closing database connection")
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
                LOGGER.info("Users table created")
                
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
                LOGGER.info("Threads table created")
                LOGGER.info("Database initialized successfully")
        except Exception as e:
            LOGGER.error(f"Failed to initialize database: {str(e)}")
            raise InvalidAuthenticationDataError(f"Failed to initialize database: {str(e)}")
    
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
    
    
    def validate_regestration_data(self, first_name: Optional[str] = None, last_name: Optional[str] = None, 
                 email: Optional[str] = None, phone: Optional[str] = None,
                 password: Optional[str] = None, birth_date: Optional[Union[str, date]] = None,
                 address: Optional[str] = None, city: Optional[str] = None, 
                 country: Optional[str] = None, collect_all_errors: bool = False) -> Dict[str, Any]:
        """
        Validates regestration user data before insertion, collecting all validation errors.
        
        Args:
            first_name: User's first name
            last_name: User's last name
            email: User's email address
            phone: User's phone number (optional)
            password: User's password
            birth_date: User's birth date (string YYYY-MM-DD or date object)
            address: User's address (optional)
            city: User's city (optional)
            country: User's country (optional)
            collect_all_errors: If True, collects all validation errors before raising
            
        Returns:
            Dict with processed data including hashed password and date objects
            
        Raises:
            InvalidRegestrationDataError: If any validation fails, with details of all failed validations
        """
        validation_errors = []
        processed_data = {}
        
        # First name validation
        if first_name is None or first_name.strip() == "":
            error = "First name is required"
            LOGGER.info(error)
            if not collect_all_errors:
                raise InvalidFirstNameError(error)
            validation_errors.append({"field": "first_name", "error": error})
        elif not re.match(r"^[A-Za-zÀ-ÖØ-öø-ÿ' -]{2,50}$", first_name):
            error = f"First name: '{first_name}' contains invalid characters or length (2-50 chars allowed)"
            LOGGER.info(error)
            if not collect_all_errors:
                raise InvalidFirstNameError(error)
            validation_errors.append({"field": "first_name", "error": error})
        else:
            processed_data["first_name"] = first_name.strip()
        
        # Last name validation
        if last_name is None or last_name.strip() == "":
            error = "Last name is required"
            LOGGER.info(error)
            if not collect_all_errors:
                raise InvalidLastNameError(error)
            validation_errors.append({"field": "last_name", "error": error})
        elif not re.match(r"^[A-Za-zÀ-ÖØ-öø-ÿ' -]{2,50}$", last_name):
            error = f"Last name: '{last_name}' contains invalid characters or length (2-50 chars allowed)"
            LOGGER.info(error)
            if not collect_all_errors:
                raise InvalidLastNameError(error)
            validation_errors.append({"field": "last_name", "error": error})
        else:
            processed_data["last_name"] = last_name.strip()
        
        # Email validation
        if email is None or email.strip() == "":
            error = "Email is required"
            LOGGER.info(error)
            if not collect_all_errors:
                raise InvalidEmailError(error)
            validation_errors.append({"field": "email", "error": error})
        elif not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email):
            error = f"Email: '{email}' is invalid"
            LOGGER.info(error)
            if not collect_all_errors:
                raise InvalidEmailError(error)
            validation_errors.append({"field": "email", "error": error})
        elif len(email) > 100:
            error = f"Email: '{email}' is too long (max 100 characters)"
            LOGGER.info(error)
            if not collect_all_errors:
                raise InvalidEmailError(error)
            validation_errors.append({"field": "email", "error": error})
        else:
            processed_data["email"] = email.strip().lower()
        
        # Phone validation (optional)
        if phone is not None and phone.strip() != "":
            if not re.match(r"^\+?[0-9]\d{1,14}$", phone.strip()):
                error = f"Phone: '{phone}' is invalid (format E.164 recommended)"
                LOGGER.info(error)
                if not collect_all_errors:
                    raise InvalidPhoneError(error)
                validation_errors.append({"field": "phone", "error": error})
            elif len(phone.strip()) > 15:
                error = f"Phone: '{phone}' is too long (max 15 characters)"
                LOGGER.info(error)
                if not collect_all_errors:
                    raise InvalidPhoneError(error)
                validation_errors.append({"field": "phone", "error": error})
            else:
                processed_data["phone"] = phone.strip()
        else:
            processed_data["phone"] = None
        
        # Password validation
        if password is None or password.strip() == "":
            error = "Password is required"
            LOGGER.info(error)
            if not collect_all_errors:
                raise InvalidPasswordError(error)
            validation_errors.append({"field": "password", "error": error})
        elif len(password) < 8:
            error = "Password must be at least 8 characters long"
            LOGGER.info(error)
            if not collect_all_errors:
                raise InvalidPasswordError(error)
            validation_errors.append({"field": "password", "error": error})
        elif not re.search(r"[A-Z]", password):
            error = "Password must contain at least one uppercase letter"
            LOGGER.info(error)
            if not collect_all_errors:
                raise InvalidPasswordError(error)
            validation_errors.append({"field": "password", "error": error})
        elif not re.search(r"[a-z]", password):
            error = "Password must contain at least one lowercase letter"
            LOGGER.info(error)
            if not collect_all_errors:
                raise InvalidPasswordError(error)
            validation_errors.append({"field": "password", "error": error})
        elif not re.search(r"[0-9]", password):
            error = "Password must contain at least one number"
            LOGGER.info(error)
            if not collect_all_errors:
                raise InvalidPasswordError(error)
            validation_errors.append({"field": "password", "error": error})
        elif not re.search(r"[^A-Za-z0-9]", password):
            error = "Password must contain at least one special character"
            LOGGER.info(error)
            if not collect_all_errors:
                raise InvalidPasswordError(error)
            validation_errors.append({"field": "password", "error": error})
        else:
            # Hash the password if validation passes
            processed_data["hashed_password"] = self._hash_password(password)
        
        # Birth date validation
        if birth_date is not None:
            try:
                # Convert string to date if needed
                if isinstance(birth_date, str):
                    if not birth_date.strip():
                        processed_data["birth_date"] = None
                    else:
                        try:
                            processed_date = datetime.strptime(birth_date.strip(), "%Y-%m-%d").date()
                            processed_data["birth_date"] = processed_date
                            
                            # Check if user is at least 18 years old
                            today = date.today()
                            age = today.year - processed_date.year - ((today.month, today.day) < (processed_date.month, processed_date.day))
                            if age < 18:
                                error = "User must be at least 18 years old"
                                LOGGER.info(error)
                                if not collect_all_errors:
                                    raise InvalidBirthDateError(error)
                                validation_errors.append({"field": "birth_date", "error": error})
                        except ValueError:
                            error = f"Birth date: '{birth_date}' is invalid (use YYYY-MM-DD format)"
                            LOGGER.info(error)
                            if not collect_all_errors:
                                raise InvalidBirthDateError(error)
                            validation_errors.append({"field": "birth_date", "error": error})
                else:
                    # It's already a date object
                    processed_data["birth_date"] = birth_date
                    
                    # Check if user is at least 18 years old
                    today = date.today()
                    age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
                    if age < 18:
                        error = "User must be at least 18 years old"
                        LOGGER.info(error)
                        if not collect_all_errors:
                            raise InvalidBirthDateError(error)
                        validation_errors.append({"field": "birth_date", "error": error})
                        
            except Exception as e:
                error = f"Birth date validation error: {str(e)}"
                LOGGER.error(error)
                if not collect_all_errors:
                    raise InvalidBirthDateError(error)
                validation_errors.append({"field": "birth_date", "error": error})
        else:
            processed_data["birth_date"] = None
            
        # Address validation (optional)
        if address is not None:
            if isinstance(address, str):
                if address.strip():
                    # Check for reasonable length
                    if len(address.strip()) > 500:
                        error = "Address is too long (max 500 characters)"
                        LOGGER.info(error)
                        if not collect_all_errors:
                            raise InvalidAddressError(error)
                        validation_errors.append({"field": "address", "error": error})
                    else:
                        processed_data["address"] = address.strip()
                else:
                    processed_data["address"] = None
            else:
                error = "Address must be a string"
                LOGGER.info(error)
                if not collect_all_errors:
                    raise InvalidAddressError(error)
                validation_errors.append({"field": "address", "error": error})
        else:
            processed_data["address"] = None
        
        # City validation (optional)
        if city is not None:
            if isinstance(city, str):
                if city.strip():
                    # Check for valid city name (letters, spaces, hyphens, periods)
                    if not re.match(r"^[A-Za-zÀ-ÖØ-öø-ÿ\s\-\.,']{2,50}$", city.strip()):
                        error = f"City: '{city}' contains invalid characters or length (2-50 chars allowed)"
                        LOGGER.info(error)
                        if not collect_all_errors:
                            raise InvalidCityError(error)
                        validation_errors.append({"field": "city", "error": error})
                    else:
                        processed_data["city"] = city.strip()
                else:
                    processed_data["city"] = None
            else:
                error = "City must be a string"
                LOGGER.info(error)
                if not collect_all_errors:
                    raise InvalidCityError(error)
                validation_errors.append({"field": "city", "error": error})
        else:
            processed_data["city"] = None
        
        # Country validation (optional)
        if country is not None:
            if isinstance(country, str):
                if country.strip():
                    # Check for valid country name (letters, spaces, hyphens)
                    if not re.match(r"^[A-Za-zÀ-ÖØ-öø-ÿ\s\-]{2,50}$", country.strip()):
                        error = f"Country: '{country}' contains invalid characters or length (2-50 chars allowed)"
                        LOGGER.info(error)
                        if not collect_all_errors:
                            raise InvalidCountryError(error)
                        validation_errors.append({"field": "country", "error": error})
                    else:
                        processed_data["country"] = country.strip()
                else:
                    processed_data["country"] = None
            else:
                error = "Country must be a string"
                LOGGER.info(error)
                if not collect_all_errors:
                    raise InvalidCountryError(error)
                validation_errors.append({"field": "country", "error": error})
        else:
            processed_data["country"] = None
        
        # If collecting all errors and we have some, raise them together
        if collect_all_errors and validation_errors:
            error_message = f"Validation failed with {len(validation_errors)} error(s)"
            LOGGER.error(error_message)
            # print(validation_errors)
            raise InvalidRegestrationDataError(error_message, validation_errors)
        
        LOGGER.info("Data validation successful")
        return processed_data
    
    
    def validate_authentication_data(
        self,
        email: Optional[str],
        password: Optional[str],                  
        collect_all_errors: bool = False
    ) -> Dict[str, Any]:
        """
        Validates regestration user data before insertion, collecting all validation errors.
        
        Args:
            first_name: User's first name
            last_name: User's last name
            email: User's email address
            phone: User's phone number (optional)
            password: User's password
            birth_date: User's birth date (string YYYY-MM-DD or date object)
            address: User's address (optional)
            city: User's city (optional)
            country: User's country (optional)
            collect_all_errors: If True, collects all validation errors before raising
            
        Returns:
            Dict with processed data including hashed password and date objects
            
        Raises:
            InvalidRegestrationDataError: If any validation fails, with details of all failed validations
        """
        validation_errors = []
        processed_data = {}
        
        
        # Email validation
        if email is None or email.strip() == "":
            error = "Email is required"
            LOGGER.info(error)
            if not collect_all_errors:
                raise InvalidEmailError(error)
            validation_errors.append({"field": "email", "error": error})
        else:
            processed_data["email"] = email.strip().lower()
        
        # Password validation
        if password is None or password.strip() == "":
            error = "Password is required"
            LOGGER.info(error)
            if not collect_all_errors:
                raise InvalidPasswordError(error)
            validation_errors.append({"field": "password", "error": error})
        else:
            # Hash the password if validation passes
            processed_data["password"] = password
        
        # If collecting all errors and we have some, raise them together
        if collect_all_errors and validation_errors:
            error_message = f"Validation failed with {len(validation_errors)} error(s)"
            LOGGER.error(error_message)
            raise InvalidAuthenticationDataError(error_message, validation_errors)
        
        LOGGER.info("Data validation successful")
        return processed_data
            
            
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
            InvalidAuthenticationDataError: If registration fails
        """
        try:
            # Checking informations
            processed_data = self.validate_regestration_data(
                first_name=first_name, last_name=last_name, email=email,
                phone=phone, password=password, birth_date=birth_date,
                address=address, city=city, country=country, collect_all_errors=True
            )
            
            first_name = processed_data["first_name"]
            last_name = processed_data["last_name"]
            email = processed_data["email"]
            hashed_password = processed_data["hashed_password"]
            phone = processed_data["phone"]
            birth_date = processed_data["birth_date"]
            address = processed_data["address"]
            city = processed_data["city"]
            country = processed_data["country"]
            
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
                    LOGGER.info(f"Registration failed: Email {email} not found")
                    raise UserNotFoundError(f"Registration failed: Email {email} not found")
            
            # Remove password from return dictionary
            del user['password']
                    
            LOGGER.info(f"User registered successfully: \n {user} )")
            return dict(user)
        except InvalidRegestrationDataError as e:
            raise e        
        except psycopg2.errors.UniqueViolation:
            LOGGER.info(f"Registration failed: Email {email} or Phone {phone} already exists")
            raise UserAlreadyExistsError(f"Registration failed: Email {email} or Phone {phone} already exists")
        except Exception as e:
            LOGGER.info(f"Registration error: {str(e)}")
            raise InvalidAuthenticationDataError(f"Registration error: {str(e)}")
    
    
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
            processed_data = self.validate_authentication_data(
                email=email,
                password=password,                  
                collect_all_errors=True
            )
            
            email = processed_data["email"]
            password = processed_data["password"]
            
            with self.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(
                    "SELECT * FROM users WHERE email = %s",
                    (email,)
                )
                user = cursor.fetchone()
                
                if not user:
                    LOGGER.info(f"Authentication failed: Email {email} not found")
                    raise UserNotFoundError(f"Authentication failed: Email {email} not found")
                
                if not self._verify_password(user['password'], password):
                    LOGGER.info(f"Authentication failed: Incorrect password for {email}")
                    raise InvalidPasswordError(f"Authentication failed: Incorrect password for {email}")
                
                # Update last login timestamp
                cursor.execute(
                    "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = %s",
                    (user['id'],)
                )
                
                # Remove password from return dictionary
                del user['password']
                
                print(f"User authenticated successfully: {email}")
                return dict(user)
                
        except InvalidAuthenticationDataError as e:
            LOGGER.info(f"Authentication error: {str(e)}")
            raise e
        except UserNotFoundError as e:
            raise e
        except InvalidPasswordError as e:
            raise e
        except Exception as e:
            LOGGER.info(f"Authentication error: {str(e)}")
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
                    raise UserNotFoundError(f"User ID {user_id} not found")
                
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
                
                LOGGER.info(f"Thread created successfully: {thread_id} for user {user_id}")
                return thread_id
                
        except Exception as e:
            LOGGER.info(f"Error creating thread: {str(e)}")
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
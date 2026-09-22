"""
JWT Authentication System for Enterprise Applications

This module demonstrates secure JWT token management with key rotation,
refresh token handling, and comprehensive security features suitable for
production systems like Lawstronaut's legal document management or
Optimizely's AI conversation platform.

Key concepts covered:
- Secure JWT generation and validation with RS256
- Token refresh and rotation strategies
- Key management and rotation
- Claims validation and security
- Token blacklisting and revocation

Real-world applications:
- Legal document access control with jurisdiction-specific permissions
- AI system authentication with role-based model access
- Multi-tenant SaaS authentication with organization isolation

Author: Technical Interview Preparation Guide
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import jwt
import secrets
import hashlib
import json
import redis
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
import logging
from contextlib import contextmanager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# =============================================================================
# JWT TOKEN MANAGEMENT SYSTEM
# =============================================================================

class TokenType(Enum):
    ACCESS = "access"
    REFRESH = "refresh"
    RESET = "reset"
    VERIFICATION = "verification"

@dataclass
class TokenClaims:
    """Structured token claims for type safety"""
    user_id: str
    email: str
    roles: List[str]
    permissions: List[str]
    organization_id: Optional[str] = None
    jurisdiction: Optional[str] = None  # For legal document access
    clearance_level: Optional[str] = None  # For classified document access
    token_type: str = TokenType.ACCESS.value
    
class KeyManager:
    """Manages RSA key pairs for JWT signing and verification"""
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis = redis_client or redis.Redis(decode_responses=True)
        self.current_key_id = None
        self.private_key = None
        self.public_key = None
        self._initialize_keys()
    
    def _initialize_keys(self):
        """Initialize or load existing keys"""
        try:
            # Try to load existing key from Redis
            key_data = self.redis.get("jwt:current_key")
            if key_data:
                key_info = json.loads(key_data)
                self.current_key_id = key_info["key_id"]
                self.private_key = serialization.load_pem_private_key(
                    key_info["private_key"].encode(),
                    password=None,
                    backend=default_backend()
                )
                self.public_key = self.private_key.public_key()
                logger.info(f"Loaded existing JWT key: {self.current_key_id}")
            else:
                self._generate_new_key_pair()
        except Exception as e:
            logger.error(f"Failed to initialize keys: {e}")
            self._generate_new_key_pair()
    
    def _generate_new_key_pair(self):
        """Generate new RSA key pair for JWT signing"""
        self.private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
        self.public_key = self.private_key.public_key()
        self.current_key_id = secrets.token_hex(8)
        
        # Store key in Redis
        private_pem = self.private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        key_info = {
            "key_id": self.current_key_id,
            "private_key": private_pem.decode(),
            "created_at": datetime.utcnow().isoformat()
        }
        
        self.redis.set("jwt:current_key", json.dumps(key_info))
        logger.info(f"Generated new JWT key: {self.current_key_id}")
    
    def rotate_keys(self):
        """Rotate to new key pair while keeping old key for verification"""
        # Store old key for verification during transition
        if self.current_key_id:
            old_public_pem = self.public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
            
            self.redis.setex(
                f"jwt:public_key:{self.current_key_id}",
                timedelta(days=7),  # Keep old keys for 7 days
                old_public_pem.decode()
            )
        
        # Generate new key pair
        self._generate_new_key_pair()
        logger.info("JWT keys rotated successfully")
    
    def get_public_key(self, key_id: str) -> Optional[str]:
        """Get public key for token verification"""
        if key_id == self.current_key_id:
            return self.public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            ).decode()
        
        # Check stored old keys
        return self.redis.get(f"jwt:public_key:{key_id}")

class JWTAuthenticator:
    """Enterprise-grade JWT authentication system"""
    
    def __init__(self, 
                 key_manager: KeyManager,
                 redis_client: Optional[redis.Redis] = None,
                 issuer: str = "lawstronaut-api",
                 audiences: List[str] = None):
        self.key_manager = key_manager
        self.redis = redis_client or redis.Redis(decode_responses=True)
        self.issuer = issuer
        self.audiences = audiences or ["api", "web"]
        self.token_blacklist_key = "jwt:blacklist"
    
    def create_access_token(self, 
                          claims: TokenClaims, 
                          expires_in_minutes: int = 60) -> str:
        """Create secure access token with comprehensive claims"""
        now = datetime.utcnow()
        payload = {
            **asdict(claims),
            "iat": now,
            "exp": now + timedelta(minutes=expires_in_minutes),
            "iss": self.issuer,
            "aud": self.audiences,
            "jti": secrets.token_hex(16),  # Unique token ID
            "kid": self.key_manager.current_key_id  # Key ID for rotation
        }
        
        return jwt.encode(
            payload, 
            self.key_manager.private_key, 
            algorithm="RS256",
            headers={"kid": self.key_manager.current_key_id}
        )
    
    def create_refresh_token(self, 
                           user_id: str, 
                           expires_in_days: int = 30) -> str:
        """Create long-lived refresh token"""
        now = datetime.utcnow()
        payload = {
            "user_id": user_id,
            "token_type": TokenType.REFRESH.value,
            "iat": now,
            "exp": now + timedelta(days=expires_in_days),
            "iss": self.issuer,
            "jti": secrets.token_hex(16)
        }
        
        return jwt.encode(
            payload,
            self.key_manager.private_key,
            algorithm="RS256"
        )
    
    def verify_token(self, token: str, token_type: TokenType = TokenType.ACCESS) -> Optional[Dict[str, Any]]:
        """Verify and decode JWT token with comprehensive validation"""
        try:
            # Decode header to get key ID
            unverified_header = jwt.get_unverified_header(token)
            key_id = unverified_header.get("kid")
            
            if not key_id:
                logger.warning("Token missing key ID")
                return None
            
            # Get public key for verification
            public_key_pem = self.key_manager.get_public_key(key_id)
            if not public_key_pem:
                logger.warning(f"Unknown key ID: {key_id}")
                return None
            
            public_key = serialization.load_pem_public_key(
                public_key_pem.encode(),
                backend=default_backend()
            )
            
            # Verify and decode token
            payload = jwt.decode(
                token,
                public_key,
                algorithms=["RS256"],
                issuer=self.issuer,
                audience=self.audiences,
                options={"require": ["exp", "iat", "iss", "aud"]}
            )
            
            # Validate token type
            if payload.get("token_type") != token_type.value:
                logger.warning(f"Invalid token type: {payload.get('token_type')}")
                return None
            
            # Check if token is blacklisted
            jti = payload.get("jti")
            if jti and self.redis.sismember(self.token_blacklist_key, jti):
                logger.warning(f"Token is blacklisted: {jti}")
                return None
            
            return payload
            
        except jwt.ExpiredSignatureError:
            logger.warning("Token has expired")
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
        except Exception as e:
            logger.error(f"Token verification error: {e}")
        
        return None
    
    def refresh_access_token(self, refresh_token: str) -> Optional[Tuple[str, str]]:
        """Generate new access token from refresh token"""
        payload = self.verify_token(refresh_token, TokenType.REFRESH)
        if not payload:
            return None
        
        user_id = payload["user_id"]
        
        # Get user's current claims (in production, fetch from database)
        user_claims = self._get_user_claims(user_id)
        if not user_claims:
            return None
        
        # Create new access token
        new_access_token = self.create_access_token(user_claims)
        
        # Optionally create new refresh token (refresh token rotation)
        new_refresh_token = self.create_refresh_token(user_id)
        
        # Blacklist old refresh token
        old_jti = payload.get("jti")
        if old_jti:
            self.blacklist_token(old_jti, payload["exp"])
        
        return new_access_token, new_refresh_token
    
    def blacklist_token(self, jti: str, exp_timestamp: float):
        """Add token to blacklist until expiration"""
        exp_datetime = datetime.fromtimestamp(exp_timestamp)
        ttl = max(0, int((exp_datetime - datetime.utcnow()).total_seconds()))
        
        if ttl > 0:
            self.redis.sadd(self.token_blacklist_key, jti)
            self.redis.expire(self.token_blacklist_key, ttl)
            logger.info(f"Token blacklisted: {jti}")
    
    def logout(self, access_token: str, refresh_token: Optional[str] = None):
        """Logout user by blacklisting tokens"""
        # Blacklist access token
        access_payload = self.verify_token(access_token)
        if access_payload and access_payload.get("jti"):
            self.blacklist_token(access_payload["jti"], access_payload["exp"])
        
        # Blacklist refresh token if provided
        if refresh_token:
            refresh_payload = self.verify_token(refresh_token, TokenType.REFRESH)
            if refresh_payload and refresh_payload.get("jti"):
                self.blacklist_token(refresh_payload["jti"], refresh_payload["exp"])
        
        logger.info(f"User logged out: {access_payload.get('user_id') if access_payload else 'unknown'}")
    
    def _get_user_claims(self, user_id: str) -> Optional[TokenClaims]:
        """Get current user claims from database (mock implementation)"""
        # In production, this would query the database for current user information
        # This is a mock implementation for demonstration
        
        mock_users = {
            "user123": TokenClaims(
                user_id="user123",
                email="attorney@lawstronaut.com",
                roles=["attorney", "researcher"],
                permissions=["documents:read", "documents:write", "cases:manage"],
                organization_id="lawfirm_001",
                jurisdiction="US-NY",
                clearance_level="confidential"
            ),
            "user456": TokenClaims(
                user_id="user456",
                email="researcher@lawstronaut.com",
                roles=["researcher"],
                permissions=["documents:read", "research:write"],
                organization_id="lawfirm_001",
                jurisdiction="US-CA",
                clearance_level="public"
            )
        }
        
        return mock_users.get(user_id)

# =============================================================================
# INTEGRATION AND DEMONSTRATION
# =============================================================================

class AuthenticationService:
    """Complete authentication service integrating all components"""
    
    def __init__(self):
        self.redis_client = redis.Redis(decode_responses=True)
        self.key_manager = KeyManager(self.redis_client)
        self.jwt_auth = JWTAuthenticator(self.key_manager, self.redis_client)
    
    def login(self, email: str, password: str) -> Optional[Dict[str, str]]:
        """Authenticate user and return tokens"""
        # Verify credentials (mock implementation)
        user_id = self._verify_credentials(email, password)
        if not user_id:
            return None
        
        # Get user claims
        claims = self.jwt_auth._get_user_claims(user_id)
        if not claims:
            return None
        
        # Create tokens
        access_token = self.jwt_auth.create_access_token(claims)
        refresh_token = self.jwt_auth.create_refresh_token(user_id)
        
        logger.info(f"User logged in: {email}")
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": 3600  # 1 hour
        }
    
    def _verify_credentials(self, email: str, password: str) -> Optional[str]:
        """Verify user credentials (mock implementation)"""
        # In production, this would hash the password and check against database
        mock_credentials = {
            "attorney@lawstronaut.com": ("password123", "user123"),
            "researcher@lawstronaut.com": ("password456", "user456")
        }
        
        stored_password, user_id = mock_credentials.get(email, (None, None))
        if stored_password and stored_password == password:
            return user_id
        return None
    
    def validate_access(self, token: str, required_permission: str) -> bool:
        """Validate token and check permissions"""
        payload = self.jwt_auth.verify_token(token)
        if not payload:
            return False
        
        user_permissions = payload.get("permissions", [])
        return required_permission in user_permissions
    
    def get_user_context(self, token: str) -> Optional[Dict[str, Any]]:
        """Get user context from token for request processing"""
        payload = self.jwt_auth.verify_token(token)
        if not payload:
            return None
        
        return {
            "user_id": payload["user_id"],
            "email": payload["email"],
            "roles": payload["roles"],
            "organization_id": payload.get("organization_id"),
            "jurisdiction": payload.get("jurisdiction"),
            "clearance_level": payload.get("clearance_level")
        }

async def demonstrate_jwt_authentication():
    """
    Comprehensive demonstration of JWT authentication system
    suitable for enterprise legal document management systems.
    """
    
    print(f"=== {__doc__.split('.')[0]} ===")
    print("Demonstrating enterprise JWT authentication with key rotation and security features\n")
    
    # Initialize authentication service
    auth_service = AuthenticationService()
    
    print("1. User Login and Token Generation")
    print("-" * 40)
    
    # Simulate user login
    login_result = auth_service.login("attorney@lawstronaut.com", "password123")
    if login_result:
        access_token = login_result["access_token"]
        refresh_token = login_result["refresh_token"]
        print(f"✓ Login successful")
        print(f"  Access Token: {access_token[:50]}...")
        print(f"  Refresh Token: {refresh_token[:50]}...")
        print(f"  Expires in: {login_result['expires_in']} seconds\n")
    else:
        print("✗ Login failed\n")
        return
    
    print("2. Token Validation and User Context")
    print("-" * 40)
    
    # Validate token and get user context
    user_context = auth_service.get_user_context(access_token)
    if user_context:
        print("✓ Token validation successful")
        print(f"  User ID: {user_context['user_id']}")
        print(f"  Email: {user_context['email']}")
        print(f"  Roles: {', '.join(user_context['roles'])}")
        print(f"  Organization: {user_context['organization_id']}")
        print(f"  Jurisdiction: {user_context['jurisdiction']}")
        print(f"  Clearance Level: {user_context['clearance_level']}\n")
    
    print("3. Permission-Based Access Control")
    print("-" * 40)
    
    # Test different permission checks
    permissions_to_test = [
        "documents:read",
        "documents:write", 
        "cases:manage",
        "admin:system"  # This should fail
    ]
    
    for permission in permissions_to_test:
        has_access = auth_service.validate_access(access_token, permission)
        status = "✓ Allowed" if has_access else "✗ Denied"
        print(f"  {permission}: {status}")
    
    print()
    
    print("4. Token Refresh Flow")
    print("-" * 40)
    
    # Refresh the access token
    refresh_result = auth_service.jwt_auth.refresh_access_token(refresh_token)
    if refresh_result:
        new_access_token, new_refresh_token = refresh_result
        print("✓ Token refresh successful")
        print(f"  New Access Token: {new_access_token[:50]}...")
        print(f"  New Refresh Token: {new_refresh_token[:50]}...\n")
        
        # Update tokens
        access_token = new_access_token
        refresh_token = new_refresh_token
    
    print("5. Key Rotation Demonstration")
    print("-" * 40)
    
    # Store current key ID
    old_key_id = auth_service.key_manager.current_key_id
    print(f"  Current Key ID: {old_key_id}")
    
    # Rotate keys
    auth_service.key_manager.rotate_keys()
    new_key_id = auth_service.key_manager.current_key_id
    print(f"  New Key ID: {new_key_id}")
    
    # Old token should still be valid (using old key)
    old_context = auth_service.get_user_context(access_token)
    if old_context:
        print("✓ Old token still valid (graceful key rotation)")
    
    # Create new token with new key
    new_login = auth_service.login("attorney@lawstronaut.com", "password123")
    if new_login:
        new_token_context = auth_service.get_user_context(new_login["access_token"])
        if new_token_context:
            print("✓ New token created with new key\n")
    
    print("6. Logout and Token Blacklisting")
    print("-" * 40)
    
    # Logout user (blacklist tokens)
    auth_service.jwt_auth.logout(access_token, refresh_token)
    
    # Try to use blacklisted token
    blacklisted_context = auth_service.get_user_context(access_token)
    if not blacklisted_context:
        print("✓ Token successfully blacklisted after logout")
    else:
        print("✗ Token still valid after logout (unexpected)")
    
    print()
    print("=== JWT Authentication System Demo Complete ===")
    print("\nKey Features Demonstrated:")
    print("- Secure RS256 JWT token generation and validation")
    print("- Comprehensive claims with role-based permissions")
    print("- Token refresh with automatic rotation")
    print("- Key rotation with graceful transition")
    print("- Token blacklisting for secure logout")
    print("- Enterprise-grade security features for legal document access")

if __name__ == "__main__":
    import asyncio
    
    # Configure logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    # Run demonstration
    asyncio.run(demonstrate_jwt_authentication())

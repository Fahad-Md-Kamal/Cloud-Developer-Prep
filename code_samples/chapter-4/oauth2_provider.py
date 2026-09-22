"""
OAuth2 Provider Implementation for Enterprise Applications

This module demonstrates a complete OAuth2 authorization server implementation
suitable for enterprise environments like Lawstronaut's legal API ecosystem
or Optimizely's AI platform integration. Supports multiple OAuth2 flows
with enterprise security features.

Key concepts covered:
- OAuth2 Authorization Code Flow with PKCE
- Client Credentials Flow for service-to-service auth
- Scope-based authorization and permission management
- Token introspection and revocation
- Multi-tenant client management

Real-world applications:
- Legal API access for third-party law firm integrations
- AI model access control for different client applications
- Enterprise SSO integration with existing identity providers

Author: Technical Interview Preparation Guide
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import secrets
import hashlib
import base64
import json
import redis
import uuid
from urllib.parse import urlparse, parse_qs, urlencode
from fastapi import FastAPI, Request, Response, HTTPException, Depends, Form
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# =============================================================================
# OAUTH2 DATA MODELS AND ENUMS
# =============================================================================

class GrantType(Enum):
    AUTHORIZATION_CODE = "authorization_code"
    CLIENT_CREDENTIALS = "client_credentials"
    REFRESH_TOKEN = "refresh_token"

class ResponseType(Enum):
    CODE = "code"
    TOKEN = "token"  # Implicit flow (not recommended)

class ClientType(Enum):
    CONFIDENTIAL = "confidential"  # Can store secrets securely
    PUBLIC = "public"  # Cannot store secrets (mobile, SPA)

@dataclass
class OAuth2Client:
    """OAuth2 client application registration"""
    client_id: str
    client_name: str
    client_type: ClientType
    client_secret: Optional[str]  # Only for confidential clients
    redirect_uris: List[str]
    allowed_scopes: List[str]
    allowed_grant_types: List[GrantType]
    organization_id: Optional[str] = None  # For multi-tenant support
    created_at: datetime = None
    is_active: bool = True

@dataclass 
class AuthorizationCode:
    """Authorization code for OAuth2 flow"""
    code: str
    client_id: str
    user_id: str
    redirect_uri: str
    scope: str
    code_challenge: Optional[str] = None
    code_challenge_method: Optional[str] = None
    created_at: datetime = None
    expires_at: datetime = None

@dataclass
class AccessToken:
    """OAuth2 access token"""
    access_token: str
    token_type: str = "Bearer"
    expires_in: int = 3600
    scope: Optional[str] = None
    refresh_token: Optional[str] = None
    client_id: Optional[str] = None
    user_id: Optional[str] = None
    created_at: datetime = None

# Request/Response models for FastAPI
class TokenRequest(BaseModel):
    grant_type: str
    code: Optional[str] = None
    redirect_uri: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    code_verifier: Optional[str] = None
    scope: Optional[str] = None
    refresh_token: Optional[str] = None

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    scope: Optional[str] = None
    refresh_token: Optional[str] = None

class IntrospectionResponse(BaseModel):
    active: bool
    scope: Optional[str] = None
    client_id: Optional[str] = None
    user_id: Optional[str] = None
    exp: Optional[int] = None
    iat: Optional[int] = None

# =============================================================================
# OAUTH2 AUTHORIZATION SERVER
# =============================================================================

class OAuth2Storage:
    """Redis-based storage for OAuth2 data"""
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis = redis_client or redis.Redis(decode_responses=True)
    
    def store_client(self, client: OAuth2Client):
        """Store OAuth2 client registration"""
        client_data = asdict(client)
        # Convert datetime and enum objects to strings
        if client_data['created_at']:
            client_data['created_at'] = client_data['created_at'].isoformat()
        client_data['client_type'] = client.client_type.value
        client_data['allowed_grant_types'] = [gt.value for gt in client.allowed_grant_types]
        
        self.redis.hset(f"oauth2:client:{client.client_id}", mapping=client_data)
        logger.info(f"Stored OAuth2 client: {client.client_name}")
    
    def get_client(self, client_id: str) -> Optional[OAuth2Client]:
        """Retrieve OAuth2 client by ID"""
        client_data = self.redis.hgetall(f"oauth2:client:{client_id}")
        if not client_data:
            return None
        
        # Convert back from strings
        client_data['client_type'] = ClientType(client_data['client_type'])
        client_data['allowed_grant_types'] = [GrantType(gt) for gt in json.loads(client_data['allowed_grant_types'])]
        client_data['redirect_uris'] = json.loads(client_data['redirect_uris'])
        client_data['allowed_scopes'] = json.loads(client_data['allowed_scopes'])
        client_data['is_active'] = client_data['is_active'] == 'True'
        if client_data.get('created_at'):
            client_data['created_at'] = datetime.fromisoformat(client_data['created_at'])
        
        return OAuth2Client(**client_data)
    
    def store_authorization_code(self, auth_code: AuthorizationCode):
        """Store authorization code with expiration"""
        code_data = asdict(auth_code)
        code_data['created_at'] = auth_code.created_at.isoformat()
        code_data['expires_at'] = auth_code.expires_at.isoformat()
        
        # Store with 10-minute expiration
        self.redis.setex(
            f"oauth2:code:{auth_code.code}",
            timedelta(minutes=10),
            json.dumps(code_data)
        )
    
    def get_and_delete_authorization_code(self, code: str) -> Optional[AuthorizationCode]:
        """Retrieve and delete authorization code (single use)"""
        code_data = self.redis.get(f"oauth2:code:{code}")
        if not code_data:
            return None
        
        # Delete immediately (single use)
        self.redis.delete(f"oauth2:code:{code}")
        
        code_dict = json.loads(code_data)
        code_dict['created_at'] = datetime.fromisoformat(code_dict['created_at'])
        code_dict['expires_at'] = datetime.fromisoformat(code_dict['expires_at'])
        
        return AuthorizationCode(**code_dict)
    
    def store_access_token(self, token: AccessToken):
        """Store access token with expiration"""
        token_data = {
            "client_id": token.client_id,
            "user_id": token.user_id,
            "scope": token.scope,
            "created_at": token.created_at.isoformat(),
            "expires_at": (token.created_at + timedelta(seconds=token.expires_in)).isoformat()
        }
        
        # Store access token
        self.redis.setex(
            f"oauth2:token:{token.access_token}",
            timedelta(seconds=token.expires_in),
            json.dumps(token_data)
        )
        
        # Store refresh token if present
        if token.refresh_token:
            refresh_data = {
                "access_token": token.access_token,
                "client_id": token.client_id,
                "user_id": token.user_id,
                "scope": token.scope
            }
            self.redis.setex(
                f"oauth2:refresh:{token.refresh_token}",
                timedelta(days=30),  # Refresh tokens last 30 days
                json.dumps(refresh_data)
            )
    
    def get_access_token_info(self, access_token: str) -> Optional[Dict[str, Any]]:
        """Get access token information for introspection"""
        token_data = self.redis.get(f"oauth2:token:{access_token}")
        if not token_data:
            return None
        
        token_info = json.loads(token_data)
        token_info['created_at'] = datetime.fromisoformat(token_info['created_at'])
        token_info['expires_at'] = datetime.fromisoformat(token_info['expires_at'])
        
        return token_info
    
    def revoke_token(self, token: str):
        """Revoke access or refresh token"""
        # Try both access and refresh token keys
        self.redis.delete(f"oauth2:token:{token}")
        self.redis.delete(f"oauth2:refresh:{token}")
        logger.info(f"Token revoked: {token[:10]}...")

class PKCEValidator:
    """PKCE (Proof Key for Code Exchange) validation for enhanced security"""
    
    @staticmethod
    def generate_code_verifier() -> str:
        """Generate code verifier for PKCE"""
        return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')
    
    @staticmethod
    def generate_code_challenge(verifier: str, method: str = "S256") -> str:
        """Generate code challenge from verifier"""
        if method == "S256":
            digest = hashlib.sha256(verifier.encode('utf-8')).digest()
            return base64.urlsafe_b64encode(digest).decode('utf-8').rstrip('=')
        elif method == "plain":
            return verifier
        else:
            raise ValueError(f"Unsupported code challenge method: {method}")
    
    @staticmethod
    def verify_code_challenge(verifier: str, challenge: str, method: str = "S256") -> bool:
        """Verify code verifier against challenge"""
        try:
            expected_challenge = PKCEValidator.generate_code_challenge(verifier, method)
            return expected_challenge == challenge
        except Exception:
            return False

class OAuth2AuthorizationServer:
    """Complete OAuth2 authorization server implementation"""
    
    def __init__(self, 
                 storage: OAuth2Storage,
                 base_url: str = "http://localhost:8000"):
        self.storage = storage
        self.base_url = base_url
        self.pkce = PKCEValidator()
        
        # Initialize with sample clients
        self._initialize_sample_clients()
    
    def _initialize_sample_clients(self):
        """Initialize sample OAuth2 clients for demonstration"""
        clients = [
            OAuth2Client(
                client_id="lawstronaut_web",
                client_name="Lawstronaut Web Application",
                client_type=ClientType.CONFIDENTIAL,
                client_secret=self._hash_secret("web_client_secret_123"),
                redirect_uris=["http://localhost:3000/auth/callback"],
                allowed_scopes=["documents:read", "documents:write", "cases:manage"],
                allowed_grant_types=[GrantType.AUTHORIZATION_CODE, GrantType.REFRESH_TOKEN],
                organization_id="lawfirm_001",
                created_at=datetime.utcnow()
            ),
            OAuth2Client(
                client_id="optimizely_api", 
                client_name="Optimizely AI API Client",
                client_type=ClientType.CONFIDENTIAL,
                client_secret=self._hash_secret("api_client_secret_456"),
                redirect_uris=[],  # No redirect for client credentials
                allowed_scopes=["ai:models:access", "conversations:read", "analytics:write"],
                allowed_grant_types=[GrantType.CLIENT_CREDENTIALS],
                organization_id="optimizely_org",
                created_at=datetime.utcnow()
            ),
            OAuth2Client(
                client_id="mobile_app_public",
                client_name="Mobile Legal Research App", 
                client_type=ClientType.PUBLIC,
                client_secret=None,  # Public client
                redirect_uris=["com.lawstronaut.mobile://oauth/callback"],
                allowed_scopes=["documents:read", "research:write"],
                allowed_grant_types=[GrantType.AUTHORIZATION_CODE],
                organization_id="lawfirm_001",
                created_at=datetime.utcnow()
            )
        ]
        
        for client in clients:
            self.storage.store_client(client)
    
    def _hash_secret(self, secret: str) -> str:
        """Hash client secret for secure storage"""
        return hashlib.sha256(secret.encode()).hexdigest()
    
    def _verify_secret(self, provided_secret: str, stored_hash: str) -> bool:
        """Verify client secret against stored hash"""
        return self._hash_secret(provided_secret) == stored_hash
    
    def create_authorization_url(self, 
                               client_id: str,
                               redirect_uri: str,
                               scope: str,
                               state: Optional[str] = None,
                               code_challenge: Optional[str] = None,
                               code_challenge_method: Optional[str] = None) -> Tuple[str, Optional[str]]:
        """Create authorization URL for OAuth2 flow"""
        # Validate client
        client = self.storage.get_client(client_id)
        if not client or not client.is_active:
            raise ValueError("Invalid or inactive client")
        
        # Validate redirect URI
        if redirect_uri not in client.redirect_uris:
            raise ValueError("Invalid redirect URI")
        
        # Validate scopes
        requested_scopes = set(scope.split(' '))
        allowed_scopes = set(client.allowed_scopes)
        if not requested_scopes.issubset(allowed_scopes):
            raise ValueError("Invalid scope requested")
        
        # Generate authorization code
        auth_code = secrets.token_urlsafe(32)
        
        # Store authorization code
        authorization = AuthorizationCode(
            code=auth_code,
            client_id=client_id,
            user_id="user123",  # In production, get from authenticated session
            redirect_uri=redirect_uri,
            scope=scope,
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(minutes=10)
        )
        
        self.storage.store_authorization_code(authorization)
        
        # Build authorization URL
        params = {
            'code': auth_code,
        }
        if state:
            params['state'] = state
        
        auth_url = f"{redirect_uri}?{urlencode(params)}"
        
        logger.info(f"Created authorization URL for client: {client_id}")
        return auth_url, auth_code
    
    def exchange_code_for_token(self, token_request: TokenRequest) -> TokenResponse:
        """Exchange authorization code for access token"""
        if token_request.grant_type != GrantType.AUTHORIZATION_CODE.value:
            raise HTTPException(status_code=400, detail="Unsupported grant type")
        
        # Validate client
        client = self.storage.get_client(token_request.client_id)
        if not client:
            raise HTTPException(status_code=401, detail="Invalid client")
        
        # Verify client secret for confidential clients
        if client.client_type == ClientType.CONFIDENTIAL:
            if not token_request.client_secret or not self._verify_secret(token_request.client_secret, client.client_secret):
                raise HTTPException(status_code=401, detail="Invalid client credentials")
        
        # Get and validate authorization code
        auth_code = self.storage.get_and_delete_authorization_code(token_request.code)
        if not auth_code:
            raise HTTPException(status_code=400, detail="Invalid or expired authorization code")
        
        # Validate code hasn't expired
        if datetime.utcnow() > auth_code.expires_at:
            raise HTTPException(status_code=400, detail="Authorization code expired")
        
        # Validate client ID matches
        if auth_code.client_id != token_request.client_id:
            raise HTTPException(status_code=400, detail="Client ID mismatch")
        
        # Validate redirect URI matches
        if auth_code.redirect_uri != token_request.redirect_uri:
            raise HTTPException(status_code=400, detail="Redirect URI mismatch")
        
        # Validate PKCE if present
        if auth_code.code_challenge and token_request.code_verifier:
            if not self.pkce.verify_code_challenge(
                token_request.code_verifier, 
                auth_code.code_challenge, 
                auth_code.code_challenge_method or "S256"
            ):
                raise HTTPException(status_code=400, detail="Invalid code verifier")
        
        # Generate access token
        access_token = secrets.token_urlsafe(32)
        refresh_token = secrets.token_urlsafe(32)
        expires_in = 3600  # 1 hour
        
        # Store access token
        token = AccessToken(
            access_token=access_token,
            expires_in=expires_in,
            scope=auth_code.scope,
            refresh_token=refresh_token,
            client_id=auth_code.client_id,
            user_id=auth_code.user_id,
            created_at=datetime.utcnow()
        )
        
        self.storage.store_access_token(token)
        
        logger.info(f"Issued access token for client: {token_request.client_id}")
        
        return TokenResponse(
            access_token=access_token,
            expires_in=expires_in,
            scope=auth_code.scope,
            refresh_token=refresh_token
        )
    
    def client_credentials_grant(self, token_request: TokenRequest) -> TokenResponse:
        """Handle client credentials grant for service-to-service authentication"""
        if token_request.grant_type != GrantType.CLIENT_CREDENTIALS.value:
            raise HTTPException(status_code=400, detail="Unsupported grant type")
        
        # Validate client
        client = self.storage.get_client(token_request.client_id)
        if not client or not client.is_active:
            raise HTTPException(status_code=401, detail="Invalid client")
        
        # Verify client supports client credentials grant
        if GrantType.CLIENT_CREDENTIALS not in client.allowed_grant_types:
            raise HTTPException(status_code=400, detail="Grant type not allowed for this client")
        
        # Verify client secret
        if not token_request.client_secret or not self._verify_secret(token_request.client_secret, client.client_secret):
            raise HTTPException(status_code=401, detail="Invalid client credentials")
        
        # Validate requested scopes
        if token_request.scope:
            requested_scopes = set(token_request.scope.split(' '))
            allowed_scopes = set(client.allowed_scopes)
            if not requested_scopes.issubset(allowed_scopes):
                raise HTTPException(status_code=400, detail="Invalid scope requested")
            scope = token_request.scope
        else:
            scope = ' '.join(client.allowed_scopes)
        
        # Generate access token (no refresh token for client credentials)
        access_token = secrets.token_urlsafe(32)
        expires_in = 3600  # 1 hour
        
        # Store access token
        token = AccessToken(
            access_token=access_token,
            expires_in=expires_in,
            scope=scope,
            client_id=client.client_id,
            user_id=None,  # No user for client credentials
            created_at=datetime.utcnow()
        )
        
        self.storage.store_access_token(token)
        
        logger.info(f"Issued client credentials token for: {client.client_name}")
        
        return TokenResponse(
            access_token=access_token,
            expires_in=expires_in,
            scope=scope
        )
    
    def introspect_token(self, token: str) -> IntrospectionResponse:
        """Introspect access token to get metadata"""
        token_info = self.storage.get_access_token_info(token)
        
        if not token_info:
            return IntrospectionResponse(active=False)
        
        # Check if token has expired
        if datetime.utcnow() > token_info['expires_at']:
            return IntrospectionResponse(active=False)
        
        return IntrospectionResponse(
            active=True,
            scope=token_info.get('scope'),
            client_id=token_info.get('client_id'),
            user_id=token_info.get('user_id'),
            exp=int(token_info['expires_at'].timestamp()),
            iat=int(token_info['created_at'].timestamp())
        )
    
    def revoke_token(self, token: str, client_id: str, client_secret: Optional[str] = None):
        """Revoke access or refresh token"""
        # Validate client
        client = self.storage.get_client(client_id)
        if not client:
            raise HTTPException(status_code=401, detail="Invalid client")
        
        # Verify client secret for confidential clients
        if client.client_type == ClientType.CONFIDENTIAL:
            if not client_secret or not self._verify_secret(client_secret, client.client_secret):
                raise HTTPException(status_code=401, detail="Invalid client credentials")
        
        # Revoke the token
        self.storage.revoke_token(token)
        logger.info(f"Token revoked by client: {client_id}")

# =============================================================================
# FASTAPI OAUTH2 ENDPOINTS
# =============================================================================

# Initialize OAuth2 server
storage = OAuth2Storage()
oauth2_server = OAuth2AuthorizationServer(storage)
security = HTTPBearer()

app = FastAPI(
    title="OAuth2 Authorization Server",
    description="Enterprise OAuth2 provider for legal document and AI system access",
    version="1.0.0"
)

@app.get("/oauth2/authorize")
async def authorize(
    client_id: str,
    redirect_uri: str,
    scope: str,
    response_type: str = "code",
    state: Optional[str] = None,
    code_challenge: Optional[str] = None,
    code_challenge_method: Optional[str] = None
):
    """OAuth2 authorization endpoint"""
    try:
        if response_type != "code":
            raise HTTPException(status_code=400, detail="Unsupported response type")
        
        # Create authorization URL and redirect
        auth_url, auth_code = oauth2_server.create_authorization_url(
            client_id=client_id,
            redirect_uri=redirect_uri,
            scope=scope,
            state=state,
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method
        )
        
        return RedirectResponse(url=auth_url)
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/oauth2/token", response_model=TokenResponse)
async def token(token_request: TokenRequest):
    """OAuth2 token endpoint"""
    try:
        if token_request.grant_type == GrantType.AUTHORIZATION_CODE.value:
            return oauth2_server.exchange_code_for_token(token_request)
        elif token_request.grant_type == GrantType.CLIENT_CREDENTIALS.value:
            return oauth2_server.client_credentials_grant(token_request)
        else:
            raise HTTPException(status_code=400, detail="Unsupported grant type")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/oauth2/introspect", response_model=IntrospectionResponse)
async def introspect(
    token: str = Form(),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Token introspection endpoint"""
    # In production, validate client credentials from Authorization header
    return oauth2_server.introspect_token(token)

@app.post("/oauth2/revoke")
async def revoke(
    token: str = Form(),
    client_id: str = Form(),
    client_secret: Optional[str] = Form(None)
):
    """Token revocation endpoint"""
    try:
        oauth2_server.revoke_token(token, client_id, client_secret)
        return {"message": "Token revoked successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Revocation endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/oauth2/clients")
async def list_clients():
    """List registered OAuth2 clients (for demonstration)"""
    # In production, this would be protected and paginated
    clients = []
    for client_id in ["lawstronaut_web", "optimizely_api", "mobile_app_public"]:
        client = storage.get_client(client_id)
        if client:
            clients.append({
                "client_id": client.client_id,
                "client_name": client.client_name,
                "client_type": client.client_type.value,
                "allowed_scopes": client.allowed_scopes,
                "allowed_grant_types": [gt.value for gt in client.allowed_grant_types]
            })
    return {"clients": clients}

@app.get("/")
async def root():
    """OAuth2 server information"""
    return {
        "name": "Enterprise OAuth2 Authorization Server",
        "version": "1.0.0",
        "endpoints": {
            "authorization": "/oauth2/authorize",
            "token": "/oauth2/token",
            "introspection": "/oauth2/introspect",
            "revocation": "/oauth2/revoke"
        },
        "supported_grant_types": [
            "authorization_code",
            "client_credentials",
            "refresh_token"
        ],
        "supported_scopes": [
            "documents:read",
            "documents:write", 
            "cases:manage",
            "ai:models:access",
            "conversations:read",
            "analytics:write"
        ]
    }

# =============================================================================
# DEMONSTRATION AND TESTING
# =============================================================================

async def demonstrate_oauth2_flows():
    """
    Demonstrate OAuth2 authorization flows for enterprise applications.
    """
    
    print(f"=== {__doc__.split('.')[0]} ===")
    print("Demonstrating OAuth2 authorization flows for enterprise systems\n")
    
    print("1. Client Credentials Flow (Service-to-Service)")
    print("-" * 50)
    
    # Simulate client credentials flow
    client_creds_request = TokenRequest(
        grant_type="client_credentials",
        client_id="optimizely_api",
        client_secret="api_client_secret_456",
        scope="ai:models:access conversations:read"
    )
    
    try:
        token_response = oauth2_server.client_credentials_grant(client_creds_request)
        print(f"✓ Client credentials token issued")
        print(f"  Access Token: {token_response.access_token[:30]}...")
        print(f"  Scope: {token_response.scope}")
        print(f"  Expires in: {token_response.expires_in} seconds\n")
        
        client_token = token_response.access_token
        
    except Exception as e:
        print(f"✗ Client credentials flow failed: {e}\n")
        return
    
    print("2. Authorization Code Flow (User Authorization)")
    print("-" * 50)
    
    # Simulate authorization code flow
    try:
        # Generate PKCE parameters for public client
        code_verifier = PKCEValidator.generate_code_verifier()
        code_challenge = PKCEValidator.generate_code_challenge(code_verifier)
        
        print(f"  PKCE Code Verifier: {code_verifier[:30]}...")
        print(f"  PKCE Code Challenge: {code_challenge[:30]}...")
        
        # Create authorization URL
        auth_url, auth_code = oauth2_server.create_authorization_url(
            client_id="lawstronaut_web",
            redirect_uri="http://localhost:3000/auth/callback",
            scope="documents:read documents:write",
            state="random_state_123",
            code_challenge=code_challenge,
            code_challenge_method="S256"
        )
        
        print(f"\n  ✓ Authorization URL created")
        print(f"  Auth Code: {auth_code[:20]}...")
        print(f"  Callback URL: {auth_url[:60]}...")
        
        # Exchange code for token
        auth_code_request = TokenRequest(
            grant_type="authorization_code",
            code=auth_code,
            redirect_uri="http://localhost:3000/auth/callback",
            client_id="lawstronaut_web",
            client_secret="web_client_secret_123",
            code_verifier=code_verifier
        )
        
        user_token_response = oauth2_server.exchange_code_for_token(auth_code_request)
        print(f"\n  ✓ Authorization code exchanged for tokens")
        print(f"  Access Token: {user_token_response.access_token[:30]}...")
        print(f"  Refresh Token: {user_token_response.refresh_token[:30]}...")
        print(f"  Scope: {user_token_response.scope}\n")
        
        user_token = user_token_response.access_token
        
    except Exception as e:
        print(f"✗ Authorization code flow failed: {e}\n")
        return
    
    print("3. Token Introspection")
    print("-" * 25)
    
    # Introspect both tokens
    for token_name, token in [("Client Token", client_token), ("User Token", user_token)]:
        introspection = oauth2_server.introspect_token(token)
        if introspection.active:
            print(f"  ✓ {token_name} is active")
            print(f"    Client ID: {introspection.client_id}")
            print(f"    User ID: {introspection.user_id or 'N/A'}")
            print(f"    Scope: {introspection.scope}")
            exp_time = datetime.fromtimestamp(introspection.exp)
            print(f"    Expires: {exp_time.strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            print(f"  ✗ {token_name} is not active")
        print()
    
    print("4. Token Revocation")
    print("-" * 20)
    
    # Revoke client token
    try:
        oauth2_server.revoke_token(
            token=client_token,
            client_id="optimizely_api",
            client_secret="api_client_secret_456"
        )
        print("  ✓ Client token revoked")
        
        # Verify token is no longer active
        revoked_introspection = oauth2_server.introspect_token(client_token)
        if not revoked_introspection.active:
            print("  ✓ Revoked token is no longer active")
        
    except Exception as e:
        print(f"  ✗ Token revocation failed: {e}")
    
    print()
    print("=== OAuth2 Authorization Server Demo Complete ===")
    print("\nKey Features Demonstrated:")
    print("- Client Credentials Flow for service-to-service authentication")
    print("- Authorization Code Flow with PKCE for user authorization")
    print("- Comprehensive token introspection and validation")
    print("- Secure token revocation with client authentication")
    print("- Multi-tenant client management with scope-based authorization")
    print("- Enterprise-grade security features for legal and AI systems")

if __name__ == "__main__":
    import asyncio
    
    # Run demonstration
    asyncio.run(demonstrate_oauth2_flows())

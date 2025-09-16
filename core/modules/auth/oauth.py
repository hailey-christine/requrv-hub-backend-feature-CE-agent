from fastapi import APIRouter, HTTPException
from fastapi.security import HTTPBearer
from authlib.integrations.starlette_client import OAuth
from starlette.requests import Request
from core.modules.auth.model import SignInOutput
from pydantic import BaseModel
from core.settings import settings
from enum import Enum
from core.settings import auth
from core.services.prisma import prisma
from fastapi.responses import RedirectResponse


oauth_router = APIRouter(prefix="/oauth", tags=["oauth"])
oauth_scheme = HTTPBearer()

class AuthProvider(Enum):
    EMAIL = "EMAIL"
    GOOGLE = "GOOGLE"
    APPLE = "APPLE"
    GITHUB = "GITHUB"

class UserCreateInput(BaseModel):
    name: str | None = ""
    surname: str | None = ""
    email: str | None = None
    email_verified: bool | None = False
    confirmed: bool | None = False
    auth_provider: AuthProvider

oauth = OAuth()

CONF_URL = 'https://accounts.google.com/.well-known/openid-configuration'

GITHUB_CLIENT_ID: str = settings.requrv_github_client_id
GITHUB_CLIENT_SECRET: str = settings.requrv_github_client_secret
GITHUB_REDIRECT_URI: str = settings.requrv_github_redirect_uri

oauth.register(
    name='google',
    server_metadata_url=CONF_URL,
    client_kwargs={
        'scope': 'openid email profile',
        'prompt': 'select_account',  # force to select account
    },
    client_id=settings.requrv_google_client_id,
    client_secret=settings.requrv_google_client_secret,
)

oauth.register(
    name='github',
    client_id=GITHUB_CLIENT_ID,
    client_secret=GITHUB_CLIENT_SECRET,
    access_token_url='https://github.com/login/oauth/access_token',
    access_token_params=None,
    authorize_url='https://github.com/login/oauth/authorize',
    authorize_params=None,
    api_base_url='https://api.github.com/',
    client_kwargs={'scope': 'user:email'},
    
)


#region Google OAuth

@oauth_router.get("/google") 
async def login_via_google(request: Request):
    redirect_uri = request.url_for('auth_via_google')
    return await oauth.google.authorize_redirect(request, redirect_uri)

@oauth_router.get("/google/callback")
async def auth_via_google(request: Request):
    try:
        token = await oauth.google.authorize_access_token(request)
        # print("Google OAuth token received:", token)
        user_info = token['userinfo']
        user_data = UserCreateInput(
            name=user_info.get("given_name", ""),
            surname=user_info.get("family_name", ""),
            email=user_info.get("email") or "",
            email_verified=user_info.get("email_verified", False),
            confirmed=True,
            auth_provider=AuthProvider.GOOGLE,
        )

        if not user_data.email:
            raise HTTPException(status_code=400, detail="Email not provided by Google")

        # Create or login user
        user = await _handle_oauth_user(AuthProvider.GOOGLE, user_data)
        jwt = auth.create_access_token(user.id)
        return RedirectResponse(settings.requrv_fe_auth_callback +"?token=" + jwt)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Google authentication failed: {str(e)}")
    
#endregion

#region GitHub OAuth

@oauth_router.get("/github")
async def login_via_github(request: Request):
    github = oauth.create_client('github')
    redirect_uri = GITHUB_REDIRECT_URI
    return await github.authorize_redirect(request, redirect_uri)

@oauth_router.get("/github/callback")
async def auth_via_github(request: Request):
    try:
        token = await oauth.github.authorize_access_token(request)
        resp = await oauth.github.get('user', token=token)
        resp.raise_for_status()
        profile = resp.json()

        user_data = UserCreateInput(
            email = profile.get("email"),
            email_verified = True,
            confirmed=True,
            auth_provider=AuthProvider.GITHUB,
        )

        if not user_data.email:
            raise HTTPException(status_code=400, detail="Email not provided by GitHub")

        # Create or login user
        user = await _handle_oauth_user(AuthProvider.GITHUB, user_data)
        jwt = auth.create_access_token(user.id)
        return RedirectResponse(settings.requrv_fe_auth_callback +"?token=" + jwt)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"GitHub authentication failed: {str(e)}")

#endregion

# TODO: after login, implement "complete your profile" -> registrer organization if missing
async def _handle_oauth_user(provider: AuthProvider, user_info: UserCreateInput) -> str:
    """
    Handle OAuth user creation/login for any provider
    """
    
    try:
        # Check if user exists by email
        existing_user = await prisma.user.find_unique(
            where={"email": user_info.email},
            include={"organization": True}
        )
        
        if existing_user:
            # User exists - update OAuth info if needed and login
            update_data = {}
            
            if not existing_user.verified_email:
                update_data["verified_email"] = True
                
            if not existing_user.confirmed:
                update_data["confirmed"] = True  # Auto-confirm OAuth users
                
            if existing_user.auth_provider == "EMAIL":
                update_data["auth_provider"] = provider
                
            if update_data:
                updated_user = await prisma.user.update(
                    where={"id": existing_user.id},
                    data=update_data
                )
                user = updated_user
            else:
                user = existing_user
        else:
            # prisma expects a plain dict with DB field names
            create_payload = {
                "name": user_info.name,
                "surname": user_info.surname,
                "email": user_info.email,
                "verified_email": user_info.email_verified,
                "confirmed": user_info.confirmed,
                "auth_provider": user_info.auth_provider.value if isinstance(user_info.auth_provider, AuthProvider) else user_info.auth_provider,
            }
            user = await prisma.user.create(data=create_payload)
        # Check if user is blocked
        if user.blocked:
            raise HTTPException(status_code=500, detail="User is blocked")
        
        return user
    except Exception as e:
        print("Error handling OAuth user:", e)
        raise HTTPException(status_code=500, detail=f"Error handling OAuth user: {str(e)}")


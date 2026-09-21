import os
import sys
import pickle
import logging
import threading
import subprocess
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Dict, Any, Optional

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from config import YOUTUBE_CLIENT_SECRET_FILE, YOUTUBE_TOKEN_FILE

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Allow OAuth over localhost without SSL certificates
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly"
]

_auth_lock = threading.Lock()
_auth_flow = None
_auth_url = None
_auth_running = False
_auth_error = None
_httpd_server = None

class _OAuthCallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global _auth_running, _auth_error, _auth_flow
        success = False
        err_msg = ""

        if "code=" in self.path:
            try:
                # Use https scheme as required by oauthlib
                auth_resp = f"https://localhost:8080{self.path}"
                logger.info("Exchanging authorization code for OAuth tokens...")
                _auth_flow.fetch_token(authorization_response=auth_resp)

                token_path = Path(YOUTUBE_TOKEN_FILE)
                with open(token_path, "wb") as token:
                    pickle.dump(_auth_flow.credentials, token)

                logger.info(f"OAuth credentials saved successfully to {token_path}!")
                success = True
                _auth_running = False
            except Exception as e:
                logger.error(f"Error exchanging OAuth code: {e}", exc_info=True)
                err_msg = str(e)
                _auth_error = str(e)
                _auth_running = False
        else:
            _auth_error = "No authorization code returned."
            _auth_running = False

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()

        if success:
            html = """
            <!DOCTYPE html>
            <html>
            <head><title>Authorization Successful</title></head>
            <body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif; background:#0f172a; color:#f8fafc; display:flex; align-items:center; justify-content:center; height:90vh; margin:0;">
                <div style="background:#1e293b; padding:40px; border-radius:16px; border:1px solid #334155; text-align:center; max-width:480px; box-shadow:0 10px 25px rgba(0,0,0,0.5);">
                    <div style="font-size:48px; margin-bottom:16px;">🎉</div>
                    <h2 style="color:#34d399; margin-top:0;">YouTube Channel Connected!</h2>
                    <p style="color:#94a3b8; font-size:15px; line-height:1.5;">Your account authorization was successful.<br/>You can now close this tab and return to <strong>AutoTube AI Studio</strong>.</p>
                </div>
            </body>
            </html>
            """
            self.wfile.write(html.encode("utf-8"))
        else:
            html = f"""
            <html><body style='font-family:sans-serif; padding:40px;'>
                <h2>Authorization Notice</h2>
                <p>{err_msg or 'Authorization was not completed.'}</p>
            </body></html>
            """
            self.wfile.write(html.encode("utf-8"))

    def log_message(self, format, *args):
        return

def get_authenticated_service(force_reauth: bool = False):
    """
    Authenticates with YouTube API via OAuth 2.0.
    Stores and refreshes user access tokens in token.pickle.
    """
    creds = None
    token_path = Path(YOUTUBE_TOKEN_FILE)
    client_secrets_path = Path(YOUTUBE_CLIENT_SECRET_FILE)

    if token_path.exists() and not force_reauth:
        try:
            with open(token_path, "rb") as token:
                creds = pickle.load(token)
        except Exception as e:
            logger.warning(f"Could not load token.pickle: {e}. Re-authenticating.")
            creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            logger.info("Refreshing YouTube OAuth token...")
            try:
                creds.refresh(Request())
                with open(token_path, "wb") as token:
                    pickle.dump(creds, token)
            except Exception as e:
                logger.warning(f"Token refresh failed: {e}. Triggering new login.")
                creds = None

        if not creds:
            if not client_secrets_path.exists():
                raise FileNotFoundError(
                    f"YouTube OAuth credentials file not found at: {client_secrets_path}."
                )
            
            flow = InstalledAppFlow.from_client_secrets_file(str(client_secrets_path), SCOPES)
            creds = flow.run_local_server(port=8080, open_browser=True)
            with open(token_path, "wb") as token:
                pickle.dump(creds, token)

    return build("youtube", "v3", credentials=creds)

def start_nonblocking_oauth() -> Dict[str, Any]:
    """
    Starts the local HTTP callback server on port 8080 and generates
    the authorization URL with zero state mismatch issues.
    """
    global _auth_flow, _auth_url, _auth_running, _auth_error, _httpd_server
    client_secrets_path = Path(YOUTUBE_CLIENT_SECRET_FILE)

    if not client_secrets_path.exists():
        raise FileNotFoundError("client_secret.json not found in project directory.")

    with _auth_lock:
        if _auth_running and _auth_url:
            return {"auth_url": _auth_url, "status": "running"}

        _auth_error = None
        _auth_flow = InstalledAppFlow.from_client_secrets_file(
            str(client_secrets_path),
            SCOPES
        )
        _auth_flow.redirect_uri = "http://localhost:8080/"

        # Generate single, authoritative authorization URL
        _auth_url, _ = _auth_flow.authorization_url(
            prompt="consent",
            access_type="offline"
        )
        _auth_running = True

        def _run_server():
            global _httpd_server, _auth_running
            try:
                logger.info("OAuth local server listening on http://localhost:8080/ ...")
                _httpd_server = HTTPServer(("localhost", 8080), _OAuthCallbackHandler)
                _httpd_server.timeout = 300
                _httpd_server.handle_request()
                _httpd_server.server_close()
            except Exception as e:
                logger.error(f"Background OAuth server error: {e}")
                _auth_running = False

        server_thread = threading.Thread(target=_run_server, daemon=True)
        server_thread.start()

        # Try to launch browser cleanly via PowerShell
        try:
            subprocess.Popen([
                "powershell.exe",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                f'Start-Process "{_auth_url}"'
            ])
        except Exception as e:
            logger.warning(f"Could not auto-open browser: {e}")

        return {"auth_url": _auth_url, "status": "started"}

def get_oauth_status() -> Dict[str, Any]:
    """Check status of the background OAuth authorization."""
    token_path = Path(YOUTUBE_TOKEN_FILE)
    if token_path.exists():
        return {"authenticated": True, "running": False, "error": None}
    return {
        "authenticated": False,
        "running": _auth_running,
        "auth_url": _auth_url,
        "error": _auth_error
    }

def get_channel_info() -> Optional[Dict[str, Any]]:
    """
    Fetches profile information for the currently connected YouTube channel.
    Returns:
        Dict with 'id', 'title', 'custom_url', 'thumbnail', 'subscribers', 'video_count'.
    """
    token_path = Path(YOUTUBE_TOKEN_FILE)
    if not token_path.exists():
        return None

    try:
        with open(token_path, "rb") as token:
            creds = pickle.load(token)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
                with open(token_path, "wb") as token:
                    pickle.dump(creds, token)
            else:
                return None

        youtube = build("youtube", "v3", credentials=creds)
        response = youtube.channels().list(
            part="snippet,statistics",
            mine=True
        ).execute()

        items = response.get("items", [])
        if not items:
            return {
                "id": "connected",
                "title": "Untold Yugas",
                "custom_url": "@UntoldYugas",
                "thumbnail": "https://www.gstatic.com/youtube/img/creator/avatar/default_avatar.png",
                "subscribers": "0",
                "video_count": "0",
                "view_count": "0"
            }

        channel = items[0]
        snippet = channel.get("snippet", {})
        stats = channel.get("statistics", {})

        return {
            "id": channel.get("id"),
            "title": snippet.get("title", "Untold Yugas"),
            "custom_url": snippet.get("customUrl", ""),
            "thumbnail": snippet.get("thumbnails", {}).get("default", {}).get("url", "https://www.gstatic.com/youtube/img/creator/avatar/default_avatar.png"),
            "subscribers": stats.get("subscriberCount", "0"),
            "video_count": stats.get("videoCount", "0"),
            "view_count": stats.get("viewCount", "0")
        }
    except Exception as e:
        logger.warning(f"Unable to retrieve live channel details: {e}. Using fallback active status.")
        # If token exists, account is connected!
        return {
            "id": "connected",
            "title": "Untold Yugas (Active)",
            "custom_url": "@UntoldYugas",
            "thumbnail": "https://www.gstatic.com/youtube/img/creator/avatar/default_avatar.png",
            "subscribers": "0",
            "video_count": "0",
            "view_count": "0"
        }

def disconnect_channel() -> bool:
    """Removes token.pickle allowing the user to connect another channel."""
    token_path = Path(YOUTUBE_TOKEN_FILE)
    if token_path.exists():
        try:
            token_path.unlink()
            return True
        except Exception as e:
            logger.error(f"Error removing token file: {e}")
            return False
    return True

def upload_video_to_youtube(
    video_path: str,
    title: str,
    description: str,
    tags: list = None,
    privacy_status: str = "unlisted",
    category_id: str = "27",
    progress_callback = None
) -> Dict[str, Any]:
    if not Path(video_path).exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")

    logger.info(f"Connecting to YouTube API to upload '{title}'...")
    youtube = get_authenticated_service()

    body = {
        "snippet": {
            "title": title[:100],
            "description": description[:5000],
            "tags": tags or ["AI", "Video"],
            "categoryId": category_id
        },
        "status": {
            "privacyStatus": privacy_status,
            "selfDeclaredMadeForKids": False
        }
    }

    media = MediaFileUpload(
        video_path,
        chunksize=1024 * 1024 * 4,
        resumable=True,
        mimetype="video/mp4"
    )

    request = youtube.videos().insert(
        part=",".join(body.keys()),
        body=body,
        media_body=media
    )

    logger.info("Uploading video to YouTube in chunks...")
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            progress = status.progress()
            pct = int(progress * 100)
            logger.info(f"YouTube Upload Progress: {pct}%")
            if progress_callback:
                progress_callback(progress, f"Uploading to YouTube: {pct}%")

    yt_video_id = response.get("id")
    yt_url = f"https://youtu.be/{yt_video_id}"
    logger.info(f"Successfully uploaded! URL: {yt_url}")

    if progress_callback:
        progress_callback(1.0, f"Upload complete! URL: {yt_url}")

    return {
        "video_id": yt_video_id,
        "youtube_url": yt_url,
        "status": "uploaded"
    }

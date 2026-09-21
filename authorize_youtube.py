import sys
import subprocess
from pathlib import Path

# Set UTF-8 encoding
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from modules.youtube_uploader import get_authenticated_service, SCOPES
from config import YOUTUBE_CLIENT_SECRET_FILE, YOUTUBE_TOKEN_FILE
from google_auth_oauthlib.flow import InstalledAppFlow
import pickle

def main():
    print("\n=======================================================")
    print("🔐 Starting YouTube Channel One-Time Authorization...")
    print("=======================================================")
    
    client_secrets_path = Path(YOUTUBE_CLIENT_SECRET_FILE)
    if not client_secrets_path.exists():
        print(f"❌ Error: {client_secrets_path} not found!")
        return

    flow = InstalledAppFlow.from_client_secrets_file(str(client_secrets_path), SCOPES)
    flow.redirect_uri = "http://localhost:8080/"
    auth_url, _ = flow.authorization_url(prompt="consent", access_type="offline")

    print("\nOpening your browser to:")
    print(auth_url)
    print("\n" + "="*55)
    print("💡 IMPORTANT TIP FOR MULTI-ACCOUNT USERS:")
    print("If you see '400 That's an error / malformed request',")
    print("simply COPY the URL above, open an INCOGNITO / PRIVATE")
    print("browser window, paste it there, and log in!")
    print("="*55 + "\n")

    try:
        subprocess.Popen(["powershell", "-c", f'Start-Process "{auth_url}"'], shell=True)
    except Exception:
        pass

    print("Waiting for you to click Allow in your browser...")
    creds = flow.run_local_server(port=8080, open_browser=False)

    token_path = Path(YOUTUBE_TOKEN_FILE)
    with open(token_path, "wb") as token:
        pickle.dump(creds, token)

    print("\n🎉 SUCCESS! YouTube channel authorization is complete!")
    print("Credentials have been saved to 'token.pickle'.")
    print("You can now refresh the dashboard and upload videos directly!\n")

if __name__ == "__main__":
    main()

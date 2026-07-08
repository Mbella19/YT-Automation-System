"""
YouTube upload via the YouTube Data API v3.

IMPORTANT: uploads require OAuth2 user credentials — an API key is NOT sufficient
(the API key path only works for public read operations). So this module manages
an OAuth token separately from the Gemini API key:

  1. Put your OAuth *client* secrets JSON at YOUTUBE_CLIENT_SECRETS (default
     `client_secrets.json`) — created in Google Cloud Console as an "OAuth client
     ID" of type "Desktop app".
  2. First run: `python -m utils.youtube_uploader` performs the consent flow and
     saves a reusable token to YOUTUBE_TOKEN_FILE (default `youtube_token.json`).
  3. After that, uploads run non-interactively and auto-refresh the token.

Uploads default to PRIVATE so nothing is published without you making it public.
"""
import os
from pathlib import Path

from utils.logger import setup_logger

logger = setup_logger()

# Upload scope. Kept minimal (upload only).
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


class YouTubeUploader:
    def __init__(self, client_secrets_file="client_secrets.json",
                 token_file="youtube_token.json"):
        self.client_secrets_file = str(client_secrets_file)
        self.token_file = str(token_file)
        self._service = None

    # ---------------- auth ----------------

    def is_authorized(self):
        """True if a saved token exists (upload can run without a browser)."""
        return Path(self.token_file).exists()

    def _load_credentials(self):
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request

        creds = None
        if Path(self.token_file).exists():
            creds = Credentials.from_authorized_user_file(self.token_file, SCOPES)

        if creds and creds.valid:
            return creds
        if creds and creds.expired and creds.refresh_token:
            logger.info("Refreshing YouTube OAuth token...")
            creds.refresh(Request())
            self._save_credentials(creds)
            return creds
        return None

    def _save_credentials(self, creds):
        with open(self.token_file, "w", encoding="utf-8") as f:
            f.write(creds.to_json())

    def authorize_interactive(self):
        """
        Run the one-time OAuth consent flow (opens a browser / prints a URL) and
        persist the token. Call this from a terminal, not from the web request.
        """
        from google_auth_oauthlib.flow import InstalledAppFlow

        if not Path(self.client_secrets_file).exists():
            raise FileNotFoundError(
                f"OAuth client secrets not found: {self.client_secrets_file}. "
                "Create an OAuth client ID (Desktop app) in Google Cloud Console "
                "and download it to this path."
            )
        flow = InstalledAppFlow.from_client_secrets_file(self.client_secrets_file, SCOPES)
        # run_local_server handles the redirect automatically when a browser is
        # available; falls back to console if not.
        try:
            creds = flow.run_local_server(port=0)
        except Exception:
            creds = flow.run_console()
        self._save_credentials(creds)
        logger.info(f"YouTube authorization complete, token saved to {self.token_file}")
        return creds

    def _get_service(self):
        if self._service is not None:
            return self._service
        from googleapiclient.discovery import build

        creds = self._load_credentials()
        if not creds:
            raise RuntimeError(
                "YouTube is not authorized. Run `python -m utils.youtube_uploader` "
                "once to complete OAuth consent."
            )
        self._service = build("youtube", "v3", credentials=creds)
        return self._service

    # ---------------- upload ----------------

    def upload(self, video_path, title, description="", tags=None,
               privacy_status="private", category_id="24"):
        """
        Upload a video with a resumable request.

        Args:
            video_path: path to the mp4 to upload
            title: video title (trimmed to 100 chars — YouTube limit)
            description: video description (trimmed to 5000 chars)
            tags: list of tag strings
            privacy_status: "private" | "unlisted" | "public"
            category_id: YouTube category (24 = Entertainment)

        Returns:
            dict with video_id and url
        """
        from googleapiclient.http import MediaFileUpload
        from googleapiclient.errors import HttpError

        video_path = str(video_path)
        if not Path(video_path).exists():
            raise FileNotFoundError(f"Video not found: {video_path}")

        service = self._get_service()

        body = {
            "snippet": {
                "title": (title or "Untitled")[:100],
                "description": (description or "")[:5000],
                "tags": (tags or [])[:15],
                "categoryId": category_id,
            },
            "status": {
                "privacyStatus": privacy_status,
                "selfDeclaredMadeForKids": False,
            },
        }

        media = MediaFileUpload(video_path, chunksize=-1, resumable=True)
        request = service.videos().insert(
            part="snippet,status", body=body, media_body=media
        )

        logger.info(f"Uploading to YouTube: {title!r} ({privacy_status})")
        response = None
        try:
            while response is None:
                status, response = request.next_chunk()
                if status:
                    logger.info(f"  upload progress: {int(status.progress() * 100)}%")
        except HttpError as e:
            logger.error(f"YouTube upload failed: {e}")
            raise

        video_id = response.get("id")
        url = f"https://youtu.be/{video_id}" if video_id else None
        logger.info(f"✓ Uploaded to YouTube: {url}")
        return {"video_id": video_id, "url": url, "privacy_status": privacy_status}


if __name__ == "__main__":
    # One-time consent flow.
    import config
    uploader = YouTubeUploader(
        client_secrets_file=getattr(config, "YOUTUBE_CLIENT_SECRETS", "client_secrets.json"),
        token_file=getattr(config, "YOUTUBE_TOKEN_FILE", "youtube_token.json"),
    )
    uploader.authorize_interactive()
    print("Done. You can now enable YouTube upload in the app.")

import base64
import json
import os
from pathlib import Path
from typing import Optional
import firebase_admin
from firebase_admin import credentials, firestore, storage
from app.config.settings import settings

class FirebaseService:
    def __init__(self):
        self._app = None
        self._db = None
        self._bucket = None
        self._init_attempted = False
        self._initialize()

    def _initialize(self):
        if self._init_attempted:
            return
        self._init_attempted = True

        try:
            if not firebase_admin._apps:
                cred = None
                cred_dict = None

                # 1. Check if raw JSON string is provided (ideal for Render environment variables)
                if settings.FIREBASE_KEY_JSON and settings.FIREBASE_KEY_JSON.strip():
                    raw = settings.FIREBASE_KEY_JSON.strip()
                    # Strip wrapping single/double quotes if added by UI
                    if (raw.startswith('"') and raw.endswith('"')) or (raw.startswith("'") and raw.endswith("'")):
                        raw = raw[1:-1]

                    # Try base64 decoding if user encoded it
                    try:
                        decoded = base64.b64decode(raw).decode("utf-8")
                        if "{" in decoded and "private_key" in decoded:
                            raw = decoded
                    except Exception:
                        pass

                    try:
                        cred_dict = json.loads(raw)
                    except Exception:
                        # Try handling escaped newlines
                        try:
                            cred_dict = json.loads(raw.replace("\\n", "\n"))
                        except Exception as je:
                            print(f"Error parsing FIREBASE_KEY_JSON: {je}")

                    if cred_dict:
                        try:
                            # Fix literal \n in private_key if needed
                            if "private_key" in cred_dict and "\\n" in cred_dict["private_key"]:
                                cred_dict["private_key"] = cred_dict["private_key"].replace("\\n", "\n")
                            cred = credentials.Certificate(cred_dict)
                            print("Loaded Firebase credentials from FIREBASE_KEY_JSON")
                        except Exception as ce:
                            print(f"Error creating credentials from FIREBASE_KEY_JSON: {ce}")

                # 2. Check if key file exists at configured path, local root, or Render secret file path
                if cred is None:
                    possible_paths = [
                        settings.FIREBASE_KEY_PATH,
                        "firebase-key.json",
                        "/etc/secrets/firebase-key.json",
                    ]
                    for kp in possible_paths:
                        if kp and os.path.exists(kp):
                            try:
                                with open(kp, "r", encoding="utf-8") as f:
                                    cred_dict = json.load(f)
                                cred = credentials.Certificate(kp)
                                print(f"Loaded Firebase credentials from file: {kp}")
                                break
                            except Exception as fe:
                                print(f"Warning reading key file {kp}: {fe}")

                # If no credentials found, DO NOT initialize Firestore to prevent 25s metadata hang
                if cred is None:
                    print("Firebase warning: No valid credentials found. Skipping Firestore to avoid Google Cloud metadata server timeout.")
                    return

                # Auto-determine project_id and storage_bucket
                project_id = settings.FIREBASE_PROJECT_ID or (cred_dict.get("project_id") if cred_dict else None)
                storage_bucket = settings.FIREBASE_STORAGE_BUCKET or (f"{project_id}.firebasestorage.app" if project_id else None)

                options = {}
                if project_id:
                    options["projectId"] = project_id
                if storage_bucket:
                    options["storageBucket"] = storage_bucket

                self._app = firebase_admin.initialize_app(cred, options)
            else:
                self._app = firebase_admin.get_app()

            try:
                self._db = firestore.client()
                print("Successfully initialized Firebase Firestore")
            except Exception as dbe:
                print(f"Firestore initialization warning: {dbe}")

            try:
                self._bucket = storage.bucket()
            except Exception:
                self._bucket = None
        except Exception as e:
            print(f"Firebase initialization warning: {e}")

    @property
    def db(self):
        if self._db is None and not self._init_attempted:
            self._initialize()
        return self._db

    @property
    def bucket(self):
        if self._bucket is None and not self._init_attempted:
            self._initialize()
        return self._bucket


    def upload_bytes(self, destination_blob_name: str, data: bytes, content_type: Optional[str] = None) -> str:
        """Uploads bytes directly to Firebase Storage bucket."""
        blob = self.bucket.blob(destination_blob_name)
        if content_type:
            blob.content_type = content_type
        blob.upload_from_string(data, content_type=content_type)
        return destination_blob_name

    def download_bytes(self, source_blob_name: str) -> bytes:
        """Downloads bytes from Firebase Storage."""
        blob = self.bucket.blob(source_blob_name)
        return blob.download_as_bytes()

    def upload_file(self, local_file_path: Path, destination_blob_name: str, content_type: Optional[str] = None) -> str:
        """Uploads a local file to Firebase Storage."""
        blob = self.bucket.blob(destination_blob_name)
        if content_type:
            blob.content_type = content_type
        blob.upload_from_filename(str(local_file_path), content_type=content_type)
        return destination_blob_name

    def download_to_file(self, source_blob_name: str, local_destination_path: Path):
        """Downloads a blob to a local file."""
        local_destination_path.parent.mkdir(parents=True, exist_ok=True)
        blob = self.bucket.blob(source_blob_name)
        blob.download_to_filename(str(local_destination_path))

    def delete_file(self, blob_name: str):
        """Deletes a file from Firebase Storage."""
        try:
            blob = self.bucket.blob(blob_name)
            if blob.exists():
                blob.delete()
        except Exception as e:
            print(f"Error deleting blob {blob_name}: {e}")

    def file_exists(self, blob_name: str) -> bool:
        """Checks if a file exists in Firebase Storage."""
        blob = self.bucket.blob(blob_name)
        return blob.exists()

firebase_service = FirebaseService()

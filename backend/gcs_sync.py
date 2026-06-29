
import os
import threading
from google.cloud import storage

GCS_BUCKET = os.getenv("CHROMA_GCS_BUCKET")
LOCAL_PATH = "./chroma_db"
PREFIX = "chroma_db/"  

_bucket = None
_last_synced_mtime = {}  # local file path -> mtime at last successful upload


def _get_bucket():
    global _bucket
    if _bucket is not None:
        return _bucket
    if not GCS_BUCKET:
        return None
    client = storage.Client()
    _bucket = client.bucket(GCS_BUCKET)
    return _bucket


def restore_from_gcs():
   
    bucket = _get_bucket()
    if not bucket:
        print("CHROMA_GCS_BUCKET not set - skipping GCS restore, using local disk only")
        return

    os.makedirs(LOCAL_PATH, exist_ok=True)
    blobs = list(bucket.list_blobs(prefix=PREFIX))
    if not blobs:
        print("No existing ChromaDB files in GCS - starting fresh")
        return

    for blob in blobs:
        rel_path = blob.name[len(PREFIX):]
        if not rel_path:
            continue
        local_file = os.path.join(LOCAL_PATH, rel_path)
        os.makedirs(os.path.dirname(local_file), exist_ok=True)
        blob.download_to_filename(local_file)
        _last_synced_mtime[local_file] = os.path.getmtime(local_file)

    print(f"Restored {len(blobs)} ChromaDB file(s) from gs://{GCS_BUCKET}/{PREFIX}")


def _changed_files():
    changed = []
    for root, _dirs, files in os.walk(LOCAL_PATH):
        for fname in files:
            full_path = os.path.join(root, fname)
            mtime = os.path.getmtime(full_path)
            if _last_synced_mtime.get(full_path) != mtime:
                changed.append((full_path, mtime))
    return changed


def _sync_worker():
    bucket = _get_bucket()
    if not bucket:
        return

    for full_path, mtime in _changed_files():
        rel_path = os.path.relpath(full_path, LOCAL_PATH)
        blob = bucket.blob(PREFIX + rel_path)
        blob.upload_from_filename(full_path)
        _last_synced_mtime[full_path] = mtime

    print("ChromaDB incremental sync to GCS complete")


def backup_to_gcs():
    """Call after writes (e.g. after build_faq_embeddings).
    Runs in a background thread so it never blocks the response - and only
    uploads files that actually changed, so it stays fast even as the
    ChromaDB folder grows."""
    if not GCS_BUCKET:
        return
    threading.Thread(target=_sync_worker, daemon=True).start()
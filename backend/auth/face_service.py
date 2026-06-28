import numpy as np
import cv2
from insightface.app import FaceAnalysis

_app = None  # loaded lazily on first use, not at import time, so the
              # app can start even if the model download is slow/unreachable


def _get_app():
    global _app
    if _app is None:
        _app = FaceAnalysis(name="buffalo_l")
        _app.prepare(ctx_id=-1, det_size=(640, 640))
    return _app


def get_embedding(image_path: str):
    img = cv2.imread(image_path)
    if img is None:
        return None
    return get_embedding_from_array(img)


def get_embedding_from_array(img):
    """Same as get_embedding, but takes an already-decoded image array
    (e.g. from cv2.imdecode) instead of a file path on disk."""
    if img is None:
        return None

    faces = _get_app().get(img)
    if len(faces) == 0:
        return None

    return faces[0].embedding


# compare two faces
def compare_faces(emb1, emb2, threshold=0.5):
    dist = np.linalg.norm(emb1 - emb2)
    return dist < threshold
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
import shutil
import os
import cv2
import numpy as np
from services import users, create_auth_token, resolve_auth_token, revoke_auth_token
from auth.face_service import get_embedding, get_embedding_from_array, compare_faces
from auth.password_service import hash_password, verify_password

router = APIRouter()

#register
@router.post("/register")
async def register(
    email: str = Form(...),
    password: str = Form(...),
    file: UploadFile = File(...)
):
    if users.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="Email already registered")

    temp_path = f"temp_{file.filename}"
    try:
        with open(temp_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        try:
            embedding = get_embedding(temp_path)
        except Exception as e:
            raise HTTPException(status_code=503, detail=f"Face recognition unavailable: {e}")
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

    if embedding is None:
        raise HTTPException(status_code=400, detail="No face detected in image")

    users.insert_one({
        "email": email,
        "password": hash_password(password),
        "face_embedding": embedding.tolist()
    })

    return {"message": "User registered successfully"}


#login
@router.post("/login")
async def login(
    file: UploadFile = File(None),
    email: str = Form(None),
    password: str = Form(None)
):
    #face login
    if file:
        image_bytes = await file.read()
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        try:
            face_embedding = get_embedding_from_array(img)
        except Exception as e:
            raise HTTPException(status_code=503, detail=f"Face recognition unavailable: {e}")

        if face_embedding is not None:
            for user in users.find():
                stored = np.array(user["face_embedding"])

                if compare_faces(face_embedding, stored):
                    token = create_auth_token(user["email"])
                    return {"message": "Login Success", "user": user["email"], "token": token}

        raise HTTPException(status_code=401, detail="Face not recognized")

    #email login
    user = users.find_one({"email": email})

    if user and verify_password(password, user["password"]):
        token = create_auth_token(email)
        return {
            "message": "Login Success",
            "user": email,
            "token": token,
        }

    raise HTTPException(status_code=401, detail="Authentication Failed")


@router.get("/verify")
async def verify(token: str):
    """Used on page load to restore a session from a token stored in the
    URL, without ever putting the user's email itself in the URL."""
    user_email = resolve_auth_token(token)
    if not user_email:
        raise HTTPException(status_code=401, detail="Session expired or invalid - please log in again")
    return {"user": user_email}


@router.post("/logout")
async def logout(token: str = Form(...)):
    revoke_auth_token(token)
    return {"message": "Logged out"}
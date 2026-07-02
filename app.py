import os
import shutil
import uuid
import threading
import time
from zipfile import ZipFile
import numpy as np
import librosa
import soundfile as sf
from pedalboard import Pedalboard, Reverb
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi import Depends
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from database import get_db

from schemas import UserCreate, UserLogin

from crud import create_user, get_user_by_email
from auth import verify_password

# Import your functions safely here
from effects import moving_pan, interaural_delay
from separator import separate_song 

from database import engine
from models import Base

Base.metadata.create_all(bind=engine)

app = FastAPI()



@app.post("/register")
def register(user: UserCreate, db: Session = Depends(get_db)):
    existing = get_user_by_email(db, user.email)
    if existing:
        return {"success": False, "message": "Email already registered."}

    new_user = create_user(db, user.username, user.email, user.password)
    return {
        "success": True,
        "message": "Registration successful!",
        "user_id": new_user.id
    }


@app.post("/login")
def login(user: UserLogin, db: Session = Depends(get_db)):
    existing = get_user_by_email(db, user.email)

    if not existing or not verify_password(user.password, existing.password):
        return {"success": False, "message": "Invalid email or password."}

    return {
        "success": True,
        "message": "Login successful!",
        "user_id": existing.id,
        "username": existing.username
    }


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_methods=["*"],
    allow_headers=["*"],
)

def stereo(audio):
    if audio.ndim == 1:
        return np.stack([audio, audio], axis=1)
    return audio

def cleanup(folder, delay=20):
    """Delete a processing session folder after `delay` seconds,
    giving the response time to finish streaming the file first."""
    time.sleep(delay)
    shutil.rmtree(folder, ignore_errors=True)

@app.post("/process-8d/")
async def process_audio(file: UploadFile = File(...)):
    # Create unique session directories to avoid file collisions between users
    session_id = str(uuid.uuid4())
    upload_dir = f"processing/{session_id}"
    os.makedirs(upload_dir, exist_ok=True)
    
    input_path = f"{upload_dir}/{file.filename}"
    output_path = f"{upload_dir}/final_8d.wav"
    
    # Save uploaded file
    with open(input_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    try:
        # 1. Run Stem Separation (Demucs)
        # Note: In production, offload this to a task queue like Celery!
        separate_song(input_path, output_dir=upload_dir)
        
        # Demucs saves files to output_dir/htdemucs/filename/stems...
        song_name = os.path.splitext(file.filename)[0]
        stem_base = f"{upload_dir}/htdemucs/{song_name}"
        
        stems = {}
        sr = 44100
        
        for stem in ['vocals', 'drums', 'bass', 'other']:
            stem_path = f"{stem_base}/{stem}.wav"
            if os.path.exists(stem_path):
                audio, sr = librosa.load(stem_path, sr=None, mono=False)
                stems[stem] = stereo(audio.T)
            else:
                # Fallback empty track if a stem fails
                stems[stem] = np.zeros((sr * 10, 2)) 

        # 2. Apply your 8D spatial logic
        vocals = moving_pan(stems['vocals'], sr, speed=0.03, phase=0)
        drums = moving_pan(stems['drums'], sr, speed=0.11, phase=np.pi/2)
        bass = moving_pan(stems['bass'], sr, speed=0.05, phase=np.pi)
        other = moving_pan(stems['other'], sr, speed=0.08, phase=3*np.pi/2)
        
        mix = vocals + drums + bass + other
        
        # 3. Master and Export
        board = Pedalboard([Reverb(room_size=0.35)])
        mix = board(mix, sr)
        mix /= np.max(np.abs(mix)) + 1e-6 # prevent divide-by-zero
        
        sf.write(output_path, mix, sr)
        
        threading.Thread(target=cleanup, args=(upload_dir,), daemon=True).start()
        
        return FileResponse(output_path, media_type="audio/wav", filename="8D_Master.wav")
        
    except Exception as e:
        return {"error": str(e)}


@app.post("/separate/")
async def separate_audio(file: UploadFile = File(...)):
    session_id = str(uuid.uuid4())
    upload_dir = f"processing/{session_id}"
    os.makedirs(upload_dir, exist_ok=True)

    input_path = f"{upload_dir}/{file.filename}"

    with open(input_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        separate_song(input_path, output_dir=upload_dir)

        song_name = os.path.splitext(file.filename)[0]
        stem_folder = f"{upload_dir}/htdemucs/{song_name}"

        zip_path = f"{upload_dir}/stems.zip"

        with ZipFile(zip_path, "w") as zipf:
            for stem in ["vocals", "drums", "bass", "other"]:
                stem_file = f"{stem_folder}/{stem}.wav"

                if os.path.exists(stem_file):
                    zipf.write(stem_file, arcname=f"{stem}.wav")

        threading.Thread(target=cleanup, args=(upload_dir,), daemon=True).start()

        return FileResponse(
            zip_path,
            media_type="application/zip",
            filename="stems.zip"
        )

    except Exception as e:
        return {"error": str(e)}

app.mount("/", StaticFiles(directory=".", html=True), name="static")

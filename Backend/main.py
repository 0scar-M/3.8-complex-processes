from fastapi import FastAPI, File, UploadFile, Query, HTTPException, Depends
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
import PIL as pil
from PIL import Image
import io
import os
import sqlite3 as sql
import time
import uuid

# Configure FastAPI app
app = FastAPI()

# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# Define global variables
media_formats = {"image": ("JPEG", "PNG")} # tells the API what conversion method to use for which formats
valid_formats = [x for y in media_formats.values() for x in y] # set valid_formats to list of all valid formats
invalid_conversions = []


class DB:
    "Manages the backend's interaction with the database."

    def __init__(self):
        "Opens database connection."
        self.timeout_secs = 600 # 10 mins
        self.path = os.path.join(os.path.dirname(os.path.dirname(__file__)), r"database/files.db")
        self.conn = sql.connect(self.path, check_same_thread=False)
        self.cursor = self.conn.cursor()
    
    def check_expired_sessions(self):
        """
        Removes any expired sessions if session.last_changed_at < current time - self.timeout_secs
        """
        expired_time = time.time() - self.timeout_secs
        try:
            session_ids = self.cursor.execute("SELECT session_id FROM sessions WHERE last_changed_at < ?", (expired_time,)).fetchall()
            for x in session_ids:
                self.cursor.execute("DELETE FROM sessions WHERE session_id=?", (x[0],))
                self.cursor.execute("DELETE FROM files WHERE session_id=?", (x[0],))
                self.conn.commit()
        except Exception as e:
            self.conn.rollback()
            raise_error(e, "removing expired session from database")

    def query(self, query_body: str, error_action: str, *query_params: tuple):
        """
        Executes a query on the database, returns the response and commits the changes.
        query_body = query to be executed.
        error_action = what this query does, used for descriptive error msgs.
        *query_params = parameterized parameters for query.
        """
        try:
            self.check_expired_sessions()
            self.cursor.execute(query_body, query_params)
            result = self.cursor.fetchall()
            self.conn.commit()
            return result
        except Exception as e:
            self.conn.rollback()
            raise_error(e, error_action)
    
    def close(self):
        "Terminates the database connection."
        self.conn.close()

def raise_error(error, error_action, code=500):
    """
    Raises an HTTPException if result is Exception.
    async so that if there is an error, it waits before continuing.
    """
    if issubclass(type(error), Exception):
        if error_action:
            raise HTTPException(status_code=code, detail=f"{error} while {error_action}")
        else:
            raise HTTPException(status_code=code, detail=error)

# Dependency function
def get_db():
    db = DB()
    try:
        yield db
    finally:
        db.close()

@app.post("/upload/")
async def upload_file(session_id: str = Query(...), file: UploadFile = File(...), db: DB = Depends(get_db)):
    """
    Adds entry to files table.
    If session_id = new, then a new uuid will be returned and a new entry will be created in the sessions table for the file.
    If session_id != new and is already in the db, then it will still be returned and the entry for that id will be updated with the new file.
    """
    if session_id == "new":
        session_id = str(uuid.uuid4())
        new_session_id = True
    else: new_session_id = False

    file_name = file.filename
    file_format = file.filename.split(".")[-1].upper()
    if file_format == "JPG": file_format = "JPEG" # PIL uses JPEG not JPG
    file_contents = await file.read()
    file_id = file.filename+"|"+session_id
    session_ids = [x[0] for x in db.query("SELECT session_id FROM files;", "getting list of session_ids from database")] # list of tuples of strings -> list of strings
    
    if file_format in [x[0] for x in invalid_conversions] or file_format not in valid_formats:
        raise HTTPException(status_code=400, detail=f"Invalid file format '{file_format}'")
    
    if new_session_id:
        db.query("INSERT INTO sessions VALUES (?, ?);", "inserting session data into database", session_id, time.time())
        db.query("INSERT INTO files VALUES (?, ?, ?, ?, ?, 0);", "inserting file data into database", file_id, session_id, file_name, file_format, file_contents)
    elif session_id in session_ids:
        db.query("UPDATE files SET file_id=?, session_id=?, name=?, format=?, contents=? WHERE session_id=?;", "updating file data in database", file_id, session_id, file_name, file_format, file_contents, session_id)
        db.query("UPDATE sessions SET last_changed_at=? WHERE session_id=?;", "updating session data in database", time.time(), session_id)
    else:
        raise HTTPException(status_code=404, detail=f"Invalid session_id value '{session_id}'")
    
    return {
        "file_name": file_name, 
        "session_id": session_id
    }

@app.patch("/convert/")
async def convert_file(session_id: str = Query(...), to_format: str = Query(...), optimise: bool = Query(...), db: DB = Depends(get_db)):
    """
    Converts file in database to desired format.
    optimise sets the optimize property in Image.save() to True. It is lossless compression only.
    Will return 404 if the session_id is invalid.
    """
    if to_format == "JPG": to_format = "JPEG" # PIL uses 'JPEG' instead of 'JPG'

    file_response = db.query("SELECT contents, format, file_id, name, converted FROM files WHERE session_id=?", "getting file from database", session_id)
    if file_response:
        file_response = file_response[0]
        if file_response[4] == 1:
            raise HTTPException(status_code=404, detail=f"File already converted for session_id: '{session_id}'")
    else:
        raise HTTPException(status_code=404, detail=f"File not found for session_id: '{session_id}'")

    conversion = (file_response[1], to_format)
    file_id = file_response[2]
    file_name = file_response[3]
    new_file_name = file_name.split(".")[0]+"."+conversion[1].lower()
    match conversion:
        case (f, t) if f in media_formats["image"] and t in media_formats["image"] and (f, t) not in invalid_conversions:
            # Image conversion
            try:
                image = Image.open(io.BytesIO(file_response[0]))
                converted_io = io.BytesIO()
                if image.mode != "RGB": # switch to RGB mode if not in it.
                    image = image.convert("RGB")
                image.save(converted_io, format=conversion[1], optimize=optimise) # optimize=True enables compression (lossless)
                db.query("UPDATE files SET name=?, contents=?, format=?, converted=1 WHERE file_id=?", "converting file in database", new_file_name, converted_io.getvalue(), conversion[1], file_id)
                db.query("UPDATE sessions SET last_changed_at=? WHERE session_id=?", "updating session data in database", time.time(), session_id)
            except pil.UnidentifiedImageError as e:
                # corrupted file
                raise_error(e, "converting file", code=400)
            except Exception as e:
                raise_error(e, "converting file")
        case _:
            raise HTTPException(status_code=400, detail=f"Invalid file conversion '{' to '.join(conversion)}'")
    
    return {
        "new_file_name": new_file_name
    }

@app.get("/download/")
async def download_file(session_id: str = Query(...), db: DB = Depends(get_db)):
    """
    Returns all files for a certain session_id.
    Will return 404 if the session_id is invalid.
    """

    response = db.query("SELECT name, contents, format FROM files WHERE session_id=?", "getting file from database", session_id)
    if response:
        response = response[0]
    else:
        raise HTTPException(status_code=404, detail=f"File not found for session_id: '{session_id}'")
    
    file_name = response[0]
    file_contents = response[1]
    file_media_type = f"{list(media_formats.keys())[list(media_formats.values()).index([x for x in media_formats.values() if response[2] in x][0])]}/{response[2]}".lower()

    return Response(
        content=file_contents, 
        media_type=file_media_type, 
        headers={"file_name": file_name}
    )

@app.get("/supported-formats")
async def supported_formats():
    "Returns all valid formats."
    return valid_formats

@app.get("/supported-conversions/{format}")
async def supported_formats(format: str):
    "Returns all valid formats for a specific media type if media_type is in media_formats.keys()"
    if format in valid_formats:
        return [x for x in media_formats.values() if format in x][0]
    else:
        raise HTTPException(status_code=404, detail=f"Invalid format: {format}")

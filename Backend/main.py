from fastapi import FastAPI, File, UploadFile, Query, HTTPException
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
import PIL as pil
from PIL import Image
import uuid
import sqlite3 as sql
import os
import io

app = FastAPI()

# Configure CORS
origins = [
    "http://127.0.0.1:5500",
    "http://localhost:5500",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

DATABASE = os.path.join(os.path.dirname(os.path.dirname(__file__)), r"Database/files.db")
media_formats = {"image": ("JPEG", "PNG")} # tells the API what conversion method to use for which formats
valid_formats = []
[[valid_formats.append(y) for y in x] for x in media_formats.values()] # set valid_formats to list of all valid formats
invalid_conversions = []

@app.post("/upload/")
async def upload_file(session_id: str = Query(...), file: UploadFile = File(...)):
    """
    Adds entry to files table. 
    If session_id = new, then a new uuid will be returned and a new entry will be created in the db for the file.
    If session_id != new and is already in the db, then it will still be returned and the entry for that id will be updated with the new file.
    """
    if session_id == "new":
        session_id = str(uuid.uuid4())
        new_session_id = True
    else: new_session_id = False

    file_name = file.filename
    file_format = file.filename.split(".")[-1].upper()
    if file_format == "JPG": file_format = "JPEG" # PIL uses JPEG not JPG
    file_bytes = await file.read()
    file_id = file.filename+"|"+session_id
    session_ids = [x[0] for x in db_query("SELECT session_id FROM files", "getting list of session_ids from database")] # list of tuples of strings -> list of strings
    
    if file_format in [x[0] for x in invalid_conversions] or file_format not in valid_formats:
        raise HTTPException(status_code=400, detail=f"Invalid file format '{file_format}'")
    
    if new_session_id:
        db_query("INSERT INTO files VALUES (?, ?, ?, ?, ?);", "uploading file to database", file_name, file_format, file_bytes, session_id, file_id)
    elif session_id in session_ids:
        db_query("UPDATE files SET name=?, format=?, bytes=?, file_id=? WHERE session_id=?;", "updating file in database", file_name, file_format, file_bytes, file_id, session_id)
    else:
        raise HTTPException(status_code=404, detail=f"Invalid session_id value '{session_id}'")
    
    return {
        "file_name": file_name,
        "file_id": file_id,
        "session_id": session_id
            }

@app.get("/convert/")
async def convert_file(session_id: str = Query(...), to_format: str = Query(...), optimise: bool = Query(...)):
    """
    Returns file in desired format.
    optimise sets the optimize property in Image.save() to True. It is lossless compression only.
    Will return 404 if the session_id is invalid.
    """
    if to_format == "JPG": to_format = "JPEG" # PIL uses 'JPEG' instead of 'JPG'

    file_response = db_query("SELECT bytes, format, file_id, name FROM files WHERE session_id=?", "getting file from database", session_id)
    if file_response:
        file_response = file_response[0]
    else:
        raise HTTPException(status_code=404, detail=f"File not found for session_id '{session_id}'")

    file_id = file_response[2]
    conversion = (file_response[1], to_format)
    match conversion:
        case (f, t) if f in media_formats["image"] and t in media_formats["image"] and (f, t) not in invalid_conversions:
            # Image conversion
            try:
                image = Image.open(io.BytesIO(file_response[0]))
                converted_io = io.BytesIO()
                image.save(converted_io, format=conversion[1], optimize=optimise) # optimize=True enables compression (lossless)
            except pil.UnidentifiedImageError as e:
                # corrupted file
                db_query("DELETE FROM files WHERE file_id=?", "removing file from database", file_id)
                raise_error(e, "converting image", code=400)
            except Exception as e:
                # remove the file from the db because if there was a conversion error, they will have to re-upload a file anyway.
                db_query("DELETE FROM files WHERE file_id=?", "removing file from database", file_id)
                raise_error(e, "converting image")
        case _:
            raise HTTPException(status_code=400, detail=f"Invalid file conversion '{' to '.join(conversion)}'")
    
    file_name = file_response[3]
    new_file_type = conversion[1]
    new_file_name = file_name.split(".")[0]+"."+new_file_type.lower()
    media_type = f"{list(media_formats.keys())[list(media_formats.values()).index([x for x in media_formats.values() if new_file_type in x][0])]}/{new_file_type}".lower()
    headers = {"file-name": new_file_name, "media-type": media_type}
    db_query("DELETE FROM files WHERE session_id=?", "removing file from database", session_id)
    return Response(content=converted_io.getvalue(), media_type=media_type, headers=headers)

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

def db_query(query_body: str, error_action: str, *query_params: tuple):
    """
    Executes a query on the database, returns the response and commits the changes.
    query_body = query to be executed.
    *query_params = parameterized parameters for query.
    action = what this query does, used for descriptive error msgs.
    """
    try:
        with sql.connect(DATABASE) as conn:
            cursor = conn.cursor()
            cursor.execute(query_body, query_params)
            return cursor.fetchall()
    except Exception as e:
        raise_error(e, error_action)

def raise_error(error, error_action, code=500):
    """
    Raises an HTTPException if result is Exception.
    async so that if there is an error, it waits before continuing.
    """
    if issubclass(type(error), Exception):
        if error_action:
            raise HTTPException(status_code=code, detail=f"Error while {error_action}: {error}")
        else:
            raise HTTPException(status_code=code, detail=f"Error: {error}")

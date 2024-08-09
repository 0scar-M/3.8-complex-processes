from dotenv import load_dotenv
from fastapi import FastAPI, File, UploadFile, Query, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
import io
import os
import sqlite3 as sql
import subprocess
import time
import tempfile
import uuid

# Load environment variables
load_dotenv()

# Define global variables
frontend_url = f"http://{os.getenv("HOST_NAME")}"
media_formats = { # All suported formats for each media type.
    "image": ("BMP", "GIF", "JFIF", "JPG", "PNG", "RAW", "SVG", "TIF", "WEBP"), 
    "video": ("AVI", "FLV", "GIF", "MKV", "MOV", "MP4", "WMV"), 
    "audio": ("AAC", "FLAC", "MP3", "OGG", "WAV", "WMA")
}
format_aliases = { # Some formats have multiple names, this provides a way to correct them.
    "JPG": ("JPEG", "JPE"), 
    "RAW": ("CR2", "NEF", "ARW"),
    "SVG": ("SVGZ"), 
    "TIF": ("TIFF"),
    "MP4": ("M4V"), 
    "AAC": ("M4A"), 
    "OGG": ("OGA")
}
valid_formats = [x for y in media_formats.values() for x in y] # Set valid_formats to list of all valid formats
invalid_conversions = [(x, "SVG") for x in media_formats["image"] if x != "SVG"] # Cannot convert raster to SVG

# Configure FastAPI app
app = FastAPI()

# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)


class DB:
    "Manages the backend's interaction with the database."

    def __init__(self):
        "Opens database connection."
        self.timeout_secs = 600 # 10 mins
        self.path = os.getenv("DATABASE_PATH") # get database path from environment variable. See docker-compose.yml
        # when running on local machine: self.path = r"../database/database.db"
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
    "Raises an HTTPException if result is an Exception."
    if issubclass(type(error), Exception):
        if error_action:
            raise HTTPException(status_code=code, detail=f"{error} while {error_action}")
        else:
            raise HTTPException(status_code=code, detail=error)

def correct_format(format: str):
    """
    Returns the file format corrected to its standard form based on format_aliases.
    If format is not valid, or no aliases exist, it is returned unchanged.
    """
    
    format = format.upper()

    if format in format_aliases: # Check if format is already correct
        return format
    
    for correct_format, aliases in format_aliases.items():
        if format in aliases:
            return correct_format
    
    return format # If no match is found, return the original format

def is_valid_conversion(conversion: tuple[str, str]):
    "Returns True if conversion is valid, False if conversion is invalid."
    
    conversion = tuple([correct_format(x) for x in conversion]) # correct conversion formats
    
    if [x in valid_formats for x in conversion] == [True, True] and conversion not in invalid_conversions and get_media_type(conversion[0]) == get_media_type(conversion[1]):
        return True
    else:
        return False

def get_media_type(format):
    "Returns the media type (image, video or audio) of a given format."

    return list(media_formats.keys())[list(media_formats.values()).index([x for x in media_formats.values() if format in x][0])]

def get_db():
    "Dependency function"

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
    file_format = correct_format(file.filename.split(".")[-1].upper())
    file_contents = await file.read()
    file_id = file.filename+"|"+session_id
    session_ids = [x[0] for x in db.query("SELECT session_id FROM files;", "getting list of session_ids from database")] # list of tuples of strings -> list of strings
    
    if file_format not in valid_formats:
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
async def convert_file(session_id: str = Query(...), to_format: str = Query(...), db: DB = Depends(get_db)):
    "Converts file in database to desired format."

    # Get file to convert contents and other data from db, and validate session_id
    file_response = db.query("SELECT contents, format, file_id, name, converted FROM files WHERE session_id=?", "getting file from database", session_id)
    if file_response:
        file_response = file_response[0]
        if file_response[4] == 1:
            raise HTTPException(status_code=404, detail=f"File already converted for session_id: '{session_id}'")
    else:
        raise HTTPException(status_code=404, detail=f"File not found for session_id: '{session_id}'")
    
    # Validate to_format
    to_format = correct_format(to_format)
    if to_format not in valid_formats:
        raise HTTPException(status_code=404, detail=f"Invalid to_format: {to_format}")

    conversion = (file_response[1], to_format)
    file_id = file_response[2]
    file_name = file_response[3]
    new_file_name = file_name.split(".")[0]+"."+(conversion[1].lower())

    if is_valid_conversion(conversion):
        input_io = io.BytesIO(file_response[0])
        output_io = io.BytesIO()

        # Create temporary files for the conversion input and output
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{conversion[0].lower()}") as input_temp:
            input_temp.write(input_io.getvalue())
            input_temp.flush()
            input_temp_name = input_temp.name
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{conversion[1].lower()}") as output_temp:
            output_temp_name = output_temp.name

        try:
            # Construct the command
            command = [
                "ffmpeg", "-nostdin", "-y",
                "-i", input_temp_name,
                output_temp_name
            ]

            # Run the ffmpeg process
            process = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=30  # Timeout after 30 seconds
            )
        except subprocess.TimeoutExpired:
            raise_error("FFMPEG process timed out", "converting file")
        except Exception as e:
            raise_error(e, "converting file")

        # Check for errors
        if process.returncode != 0:
            raise_error(f"FFMPEG error: {process.stderr.decode()}", "converting file")
        else:
            # Read the output file from the temporary file into a BytesIO object
            with open(output_temp_name, 'rb') as output_temp:
                output_io = io.BytesIO(output_temp.read())
                output_io.name = new_file_name
                # Update db
                db.query("UPDATE files SET name=?, contents=?, format=?, converted=1 WHERE file_id=?", "converting file in database", new_file_name, output_io.getvalue(), conversion[1], file_id)
                db.query("UPDATE sessions SET last_changed_at=? WHERE session_id=?", "updating session data in database", time.time(), session_id)
        
        # Clean up temporary files
        os.remove(input_temp_name)
        os.remove(output_temp_name)
    else:
        raise HTTPException(status_code=400, detail=f"Invalid file conversion '{' to '.join(conversion)}'")
    
    return {
        "new_file_name": new_file_name
    }

@app.get("/download/")
async def download_file(session_id: str = Query(...), db: DB = Depends(get_db)):
    "Returns all files for a given session_id."

    # Get file contents and other data from db
    response = db.query("SELECT name, contents, format FROM files WHERE session_id=?", "getting file from database", session_id)
    if response:
        response = response[0]
    else:
        raise HTTPException(status_code=404, detail=f"File not found for session_id: '{session_id}'")
    
    file_name = response[0]
    file_contents = response[1]
    file_media_type = f"{get_media_type(response[2])}/{response[2]}".lower()

    return Response(
        content=file_contents, 
        media_type=file_media_type, 
        headers={"file_name": file_name}
    )

@app.get("/supported-formats/")
async def supported_formats():
    "Returns all valid formats."

    return valid_formats

@app.get("/supported-conversions/")
async def supported_conversions(format: str):
    "Returns all valid formats to convert to for a specific format if it is in valid_formats."

    format = correct_format(format)
    if format in valid_formats:
        same_media_type_formats = [x for x in media_formats.values() if format in x][0]
        return [x for x in same_media_type_formats if is_valid_conversion((format, x))]
    else:
        raise HTTPException(status_code=404, detail=f"Invalid format: {format}")

@app.get("/correct-format/")
async def correct_format_endpoint(format: str):
    "Returns the file format corrected to its standard form based on format_aliases."

    format = correct_format(format)
    if format in valid_formats:
        return format
    else:
        raise HTTPException(status_code=404, detail=f"Invalid format: {format}")

@app.get("/is-valid-conversion/")
async def is_valid_conversion_endpoint(from_format: str, to_format: str):
    "Returns True if file conversion from from_format to to_format is valid, False if not."

    from_format = correct_format(from_format)
    to_format = correct_format(to_format)
    return is_valid_conversion((from_format, to_format))

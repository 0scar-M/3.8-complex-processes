from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import Response
from PIL import Image
import uuid
import sqlite3 as sql
import os

app = FastAPI()

DATABASE = os.path.join(os.path.dirname(os.path.dirname(__file__)), r"Database/files.db")
valid_conversions = {"JPG": "PNG", 
                     "PNG": "JPG"}

@app.post("/upload/{session_id}")
async def upload_file(session_id: str, file: UploadFile = File(...)):
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
    file_bytes = await file.read()
    file_id = file.filename+"|"+session_id
    session_ids = [x[0] for x in db_query("SELECT session_id FROM files")] # list of tuples of strings -> list of strings
    
    if file_format not in valid_conversions.keys():
        raise HTTPException(status_code=400, detail=f"Invalid file format '{file_format}'")
    
    if new_session_id:
        db_query("INSERT INTO files VALUES (?, ?, ?, ?, ?);", file_name, file_format, file_bytes, session_id, file_id)
    elif session_id in session_ids:
        db_query("UPDATE files SET name=?, format=?, bytes=?, file_id=? WHERE session_id=?;", file_name, file_format, file_bytes, file_id, session_id)
    else:
        raise HTTPException(status_code=404, detail="Item not found")
    
    return {
        "file_name": file_name,
        "file_id": file_id,
        "session_id": session_id
            }

def db_query(query_body: str, *query_params: tuple):
    """
    Executes a query on the database, returns the response and commits the changes.
    query_body = query to be executed.
    *query_params = parameterized parameters for query.
    """
    with sql.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute(query_body, query_params)
        return cursor.fetchall()

from fastapi import FastAPI, Depends, HTTPException, Header
from typing import Optional
from supabase import create_client, Client
import secrets
from dotenv import load_dotenv
import os

load_dotenv()

# ---- Supabase Setup ----
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI()


# ---- Helper: Get API key from request ----
def get_api_key(x_api_key: Optional[str] = Header(None)):
    if not x_api_key:
        raise HTTPException(status_code=401, detail="API Key required")
    
    # Check in Supabase
    response = supabase.table("api_keys").select("*").eq("api_key", x_api_key).execute()
    if not response.data:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    return x_api_key


# ---- Endpoint: User signs in & gets an API key ----
@app.post("/signin")
def signin_user(email: str):
    # check if user already has an API key
    existing = supabase.table("api_keys").select("api_key").eq("user_email", email).execute()
    if existing.data:
        return {"message": "Welcome back!", "api_key": existing.data[0]["api_key"]}
    
    # generate new API key
    new_key = secrets.token_hex(16)  # 32-char hex key
    supabase.table("api_keys").insert({"user_email": email, "api_key": new_key}).execute()
    return {"message": "Signed in successfully", "api_key": new_key}


# ---- Function to expose ----
def add(a: int, b: int):
    return a + b


# ---- Protected API ----
@app.get("/add")
def add_numbers(a: int, b: int, api_key: str = Depends(get_api_key)):
    return {"result": add(a, b)}

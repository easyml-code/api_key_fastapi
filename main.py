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

    user = response.data[0]
    
    if user["credits"] <= 0:
        raise HTTPException(status_code=402, detail="Out of credits. Please recharge.")
    
    return user


# ---- Endpoint: User signs in & gets an API key ----
@app.post("/signin")
def signin_user(email: str):
    # check if user already has an API key
    existing = supabase.table("api_keys").select("api_key").eq("user_email", email).execute()
    if existing.data:
        return {"message": "Welcome back!", "api_key": existing.data[0]["api_key"]}
    
    # generate new API key
    new_key = secrets.token_hex(16)  # 32-char hex key
    supabase.table("api_keys").insert({"user_email": email, "api_key": new_key, "credits":100}).execute()
    return {"message": "Signed in successfully", "api_key": new_key, "credits": 100}


# ---- Function to expose ----
def add(a: int, b: int):
    return a + b


@app.get("/add")
def add_numbers(a: int, b: int, user = Depends(get_api_key)):
    supabase.table("api_keys").update({"credits": user["credits"] - 1}).eq("api_key", user["api_key"]).execute()
    
    # Log usage
    supabase.table("usage_logs").insert({
        "api_key": user["api_key"],
        "endpoint": "/add",
        "tokens_used": 1
    }).execute()
    
    return {"result": add(a, b), "remaining_credits": user["credits"] - 1}

# ---- Recharge Endpoint ----
@app.post("/recharge")
def recharge(api_key: str, amount: int):
    """Admin/User can recharge credits"""
    response = supabase.table("api_keys").select("*").eq("api_key", api_key).execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Invalid API Key")
    
    if not isinstance(amount/10, int):
        raise HTTPException(status_code=400, detail="Invalid Amount, Please recharge with the mutliple of 10")
    
    user = response.data[0]
    new_credits = user["credits"] + amount//10
    supabase.table("api_keys").update({"credits": new_credits}).eq("api_key", api_key).execute()
    return {"message": "Recharged successfully", "credits": new_credits}
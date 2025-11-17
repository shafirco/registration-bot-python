# main.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr
from pymongo import MongoClient
from datetime import datetime
from fastapi.middleware.cors import CORSMiddleware
import bcrypt
import requests
import os
import ssl
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = FastAPI()

# ✅ Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React Web (local)
        "http://127.0.0.1:3000",
        "http://localhost:19006", # Expo (web preview)
        "exp://127.0.0.1:19000",  # Expo (mobile)
        "http://10.0.2.2:19000",  # Android emulator
        "https://*.azurewebsites.net",  # Azure App Services
        "*"  # Allow all origins in production (you can restrict this later)
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Database connection ---
MONGODB_URL = os.getenv("MONGODB_URL")
DATABASE_NAME = os.getenv("DATABASE_NAME", "registration_db")

# Initialize MongoDB connection (optional)
users_collection = None
if MONGODB_URL:
    try:
        # Multiple connection attempts with different SSL configurations
        connection_configs = [
            # Config 1: Standard SSL with certificate validation disabled
            {
                "ssl": True,
                "ssl_cert_reqs": ssl.CERT_NONE,
                "serverSelectionTimeoutMS": 3000,
                "connectTimeoutMS": 3000,
                "socketTimeoutMS": 3000
            },
            # Config 2: TLS with insecure settings
            {
                "tls": True,
                "tlsInsecure": True,
                "serverSelectionTimeoutMS": 3000,
                "connectTimeoutMS": 3000,
                "socketTimeoutMS": 3000
            },
            # Config 3: No SSL (fallback)
            {
                "ssl": False,
                "serverSelectionTimeoutMS": 3000,
                "connectTimeoutMS": 3000,
                "socketTimeoutMS": 3000
            }
        ]
        
        client = None
        for i, config in enumerate(connection_configs):
            try:
                print(f"🔄 Trying MongoDB connection method {i+1}...")
                client = MongoClient(MONGODB_URL, **config)
                # Test the connection
                client.admin.command('ping')
                print(f"✅ MongoDB connected successfully with method {i+1}")
                break
            except Exception as e:
                print(f"❌ Method {i+1} failed: {str(e)[:100]}...")
                if client:
                    client.close()
                client = None
                continue
        
        if client:
            db = client[DATABASE_NAME]
            users_collection = db["users"]
        else:
            print("⚠️ All MongoDB connection methods failed")
            print("📝 Registration will work without database storage")
            users_collection = None
            
    except Exception as e:
        print(f"⚠️ MongoDB connection setup failed: {e}")
        print("📝 Registration will work without database storage")
        users_collection = None
else:
    print("📝 No MongoDB URL provided - registration will work without database storage")

# --- Request model ---
class UserRegister(BaseModel):
    name: str
    email: EmailStr
    password: str

# --- Routes ---
@app.get("/")
def root():
    return {"message": "Registration API is running", "status": "healthy"}

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "registration-api"}

@app.post("/register")
def register_user(user: UserRegister):
    # בדוק אם יש חיבור למסד נתונים
    if users_collection is not None:
        try:
            # בדוק אם המשתמש כבר קיים
            if users_collection.find_one({"email": user.email}):
                raise HTTPException(status_code=400, detail="User already exists")

            # הצפן סיסמה
            hashed_pw = bcrypt.hashpw(user.password.encode('utf-8'), bcrypt.gensalt())

            # צור מסמך חדש
            user_doc = {
                "name": user.name,
                "email": user.email,
                "password_hash": hashed_pw.decode('utf-8'),
                "created_at": datetime.utcnow()
            }

            # שמור בבסיס הנתונים
            result = users_collection.insert_one(user_doc)
            print(f"✅ User {user.email} saved to database with ID: {result.inserted_id}")
        except Exception as e:
            print(f"⚠️ Database error: {e}")
            # Continue without database
    else:
        print(f"📝 User registration (no database): {user.name} - {user.email}")

    # --- קרא לשרת Node.js כדי להביא הודעת AI ---
    NODE_SERVER_URL = os.getenv("NODE_SERVER_URL", "https://registration-bot-node-bfb7g2gscyghg4gc.israelcentral-01.azurewebsites.net")
    try:
        response = requests.get(f"{NODE_SERVER_URL}/random-message")
        ai_data = response.json()
        ai_message = ai_data.get("quote", "")
    except Exception as e:
        print("⚠️ Error fetching AI message:", e)
        ai_message = "ברוך הבא! (לא ניתן היה להביא הודעת השראה)"

    return {
        "success": True,
        "message": "User registered successfully",
        "ai_message": ai_message
    }

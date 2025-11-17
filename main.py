# main.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr
from pymongo import MongoClient
from datetime import datetime
from fastapi.middleware.cors import CORSMiddleware
import bcrypt
import requests
import os
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
        print("🔄 Attempting MongoDB connection...")
        
        # Parse and modify the connection string for Azure compatibility
        if "mongodb+srv://" in MONGODB_URL:
            # For Azure, we need to modify the connection string
            modified_url = MONGODB_URL
            if "tls=true" not in modified_url:
                if "?" in modified_url:
                    modified_url += "&tls=true&tlsAllowInvalidCertificates=true"
                else:
                    modified_url += "?tls=true&tlsAllowInvalidCertificates=true"
            
            print(f"🔗 Using modified connection string for Azure")
            
            client = MongoClient(
                modified_url,
                serverSelectionTimeoutMS=10000,
                connectTimeoutMS=10000,
                socketTimeoutMS=10000,
                maxPoolSize=1,
                retryWrites=True
            )
        else:
            client = MongoClient(MONGODB_URL)
        
        # Test connection
        client.admin.command('ping')
        db = client[DATABASE_NAME]
        users_collection = db["users"]
        print("✅ MongoDB connected successfully")
        
    except Exception as e:
        print(f"⚠️ MongoDB connection failed: {e}")
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
            users_collection.insert_one(user_doc)
            print(f"✅ User {user.email} saved to database")
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

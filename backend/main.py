from pathlib import Path
from datetime import datetime, timedelta
import uuid
import hashlib
import asyncio

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles

from pydantic import BaseModel, EmailStr

from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
)
from sqlalchemy.orm import declarative_base, sessionmaker, Session

from jose import jwt

from playwright.sync_api import sync_playwright


# =========================================================
# APP SETUP
# =========================================================

app = FastAPI(title="Simple URL Preview App")


# =========================================================
# CORS
# =========================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# DIRECTORIES
# =========================================================

BASE_DIR = Path(__file__).resolve().parent

PREVIEW_DIR = BASE_DIR / "previews"
PREVIEW_DIR.mkdir(exist_ok=True)


# =========================================================
# DATABASE
# =========================================================

DATABASE_URL = f"sqlite:///{BASE_DIR / 'app.db'}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)

Base = declarative_base()


# =========================================================
# DATABASE MODELS
# =========================================================

class User(Base):
    __tablename__ = "users"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    email = Column(
        String,
        unique=True,
        nullable=False,
        index=True,
    )

    password = Column(
        String,
        nullable=False,
    )


class SavedURL(Base):
    __tablename__ = "saved_urls"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    url = Column(
        String,
        nullable=False,
    )

    preview = Column(
        String,
        nullable=False,
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
    )


Base.metadata.create_all(bind=engine)


# =========================================================
# DATABASE DEPENDENCY
# =========================================================

def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


# =========================================================
# PASSWORD HASHING
# =========================================================

def hash_password(password: str) -> str:
    return hashlib.sha256(
        password.encode("utf-8")
    ).hexdigest()


# =========================================================
# JWT AUTHENTICATION
# =========================================================

SECRET_KEY = "simple-demo-secret-key"
ALGORITHM = "HS256"

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/login"
)


def create_token(user_id: int) -> str:

    payload = {
        "user_id": user_id,
        "exp": datetime.utcnow() + timedelta(hours=24),
    }

    return jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM,
    )


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):

    try:

        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
        )

        user_id = payload.get("user_id")

        if user_id is None:
            raise HTTPException(
                status_code=401,
                detail="Invalid token",
            )

    except Exception:

        raise HTTPException(
            status_code=401,
            detail="Invalid token",
        )

    user = (
        db.query(User)
        .filter(User.id == user_id)
        .first()
    )

    if not user:

        raise HTTPException(
            status_code=401,
            detail="User not found",
        )

    return user


# =========================================================
# REQUEST MODELS
# =========================================================

class SignupData(BaseModel):
    email: EmailStr
    password: str


class URLData(BaseModel):
    url: str


# =========================================================
# SIGNUP
# =========================================================

@app.post("/signup")
def signup(
    data: SignupData,
    db: Session = Depends(get_db),
):

    email = str(data.email).lower().strip()

    existing = (
        db.query(User)
        .filter(User.email == email)
        .first()
    )

    if existing:

        raise HTTPException(
            status_code=400,
            detail="Email already registered",
        )

    user = User(
        email=email,
        password=hash_password(data.password),
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return {
        "message": "Account created successfully"
    }


# =========================================================
# LOGIN
# =========================================================

@app.post("/login")
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):

    email = form_data.username.lower().strip()

    user = (
        db.query(User)
        .filter(User.email == email)
        .first()
    )

    if not user:

        raise HTTPException(
            status_code=401,
            detail="Invalid email or password",
        )

    if hash_password(form_data.password) != user.password:

        raise HTTPException(
            status_code=401,
            detail="Invalid email or password",
        )

    access_token = create_token(user.id)

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }


# =========================================================
# STATIC PREVIEW FILES
# =========================================================

app.mount(
    "/previews",
    StaticFiles(
        directory=str(PREVIEW_DIR)
    ),
    name="previews",
)


# =========================================================
# SCREENSHOT FUNCTION
# =========================================================

def take_screenshot(url: str):

    filename = f"{uuid.uuid4()}.png"

    file_path = PREVIEW_DIR / filename

    print("Opening URL:", url)

    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=True
        )

        try:

            page = browser.new_page(
                viewport={
                    "width": 1440,
                    "height": 900,
                }
            )

            print("Loading page...")

            page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=30000,
            )

            print("Page loaded.")

            page.wait_for_timeout(2000)

            page.screenshot(
                path=str(file_path),
                full_page=True,
            )

            print(
                "Screenshot saved:",
                file_path
            )

        finally:

            browser.close()

    return filename


# =========================================================
# CREATE URL PREVIEW
# =========================================================

@app.post("/urls")
async def create_url(
    data: URLData,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):

    url = data.url.strip()

    if not url:

        raise HTTPException(
            status_code=400,
            detail="URL is required",
        )

    # Add HTTPS automatically
    if not url.startswith(
        ("http://", "https://")
    ):

        url = "https://" + url

    # Run Playwright outside FastAPI's
    # asyncio event loop.
    try:

        filename = await asyncio.to_thread(
            take_screenshot,
            url,
        )

    except Exception as e:

        print(
            "SCREENSHOT ERROR:",
            repr(e)
        )

        raise HTTPException(
            status_code=400,
            detail=f"Could not create preview: {str(e)}",
        )

    # Save URL in database
    item = SavedURL(
        url=url,
        preview=filename,
        user_id=current_user.id,
    )

    db.add(item)

    db.commit()

    db.refresh(item)

    return {
        "id": item.id,
        "url": item.url,
        "preview_url": f"/previews/{item.preview}",
        "created_at": item.created_at,
    }


# =========================================================
# GET SAVED URLs
# =========================================================

@app.get("/urls")
def get_urls(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):

    items = (
        db.query(SavedURL)
        .filter(
            SavedURL.user_id == current_user.id
        )
        .order_by(
            SavedURL.created_at.desc()
        )
        .all()
    )

    return [
        {
            "id": item.id,
            "url": item.url,
            "preview_url": f"/previews/{item.preview}",
            "created_at": item.created_at,
        }
        for item in items
    ]


# =========================================================
# DELETE SAVED URL
# =========================================================

@app.delete("/urls/{url_id}")
def delete_url(
    url_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):

    item = (
        db.query(SavedURL)
        .filter(
            SavedURL.id == url_id,
            SavedURL.user_id == current_user.id,
        )
        .first()
    )

    if not item:

        raise HTTPException(
            status_code=404,
            detail="URL not found",
        )

    # Delete screenshot
    file_path = PREVIEW_DIR / item.preview

    if file_path.exists():
        file_path.unlink()

    # Delete database record
    db.delete(item)

    db.commit()

    return {
        "message": "Deleted successfully"
    }


# =========================================================
# HOME
# =========================================================

@app.get("/")
def home():

    return {
        "message": "URL Preview API is running"
    }
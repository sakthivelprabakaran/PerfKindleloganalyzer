from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime
import uvicorn
from typing import List, Optional
import pandas as pd
import os
import shutil
import bcrypt
import jwt
from datetime import datetime, timedelta

# Import centralized configuration
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (
    SERVER_IP, SERVER_PORT, DB_NAME, DB_BACKUP_DIR, 
    DB_BACKUP_RETENTION, DEFAULT_PASSWORD,
    SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES
)

import time
import asyncio
import sqlite3
from functools import wraps
from sqlalchemy.exc import OperationalError

# --- Retry Logic Decorator (Sync) ---
def retry_on_db_lock(max_retries=5, base_delay=0.1):
    """
    Decorator to retry database operations when SQLite is locked (Sync).
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            while True:
                try:
                    return func(*args, **kwargs)
                except OperationalError as e:
                    if "database is locked" in str(e) and retries < max_retries:
                        retries += 1
                        delay = base_delay * (2 ** (retries - 1))
                        print(f"⚠️ Database locked (Sync). Retrying {retries}/{max_retries} in {delay:.2f}s...")
                        time.sleep(delay)
                    else:
                        raise e
        return wrapper
    return decorator

# --- Retry Logic Decorator (Async) ---
def retry_on_db_lock_async(max_retries=5, base_delay=0.1):
    """
    Decorator to retry database operations when SQLite is locked (Async).
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            retries = 0
            while True:
                try:
                    return await func(*args, **kwargs)
                except OperationalError as e:
                    if "database is locked" in str(e) and retries < max_retries:
                        retries += 1
                        delay = base_delay * (2 ** (retries - 1))
                        print(f"⚠️ Database locked (Async). Retrying {retries}/{max_retries} in {delay:.2f}s...")
                        await asyncio.sleep(delay)
                    else:
                        raise e
        return wrapper
    return decorator

# --- Auto-Backup Function ---
def backup_database():
    """Create a timestamped backup of the database on startup."""
    if not os.path.exists(DB_NAME):
        print("ℹ️  No existing database to backup.")
        return

    os.makedirs(DB_BACKUP_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"live_audit_backup_{timestamp}.db"
    backup_path = os.path.join(DB_BACKUP_DIR, backup_filename)
    
    try:
        shutil.copy2(DB_NAME, backup_path)
        print(f"✅ Database backed up: {backup_path}")
        
        # Cleanup old backups (keep last N)
        backups = sorted([os.path.join(DB_BACKUP_DIR, f) for f in os.listdir(DB_BACKUP_DIR) if f.endswith('.db')])
        while len(backups) > DB_BACKUP_RETENTION:
            old_backup_to_remove = backups.pop(0)
            os.remove(old_backup_to_remove)
            print(f"🗑️  Removed old backup: {os.path.basename(old_backup_to_remove)}")
    except Exception as e:
        print(f"⚠️  Backup failed: {e}")

# --- Database Setup ---
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_NAME}"

# Enable WAL mode and connection pooling for better concurrency
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={
        "check_same_thread": False,
        "timeout": 30  # Wait 30s instead of immediate failure
    },
    pool_pre_ping=True  # Validate connections before using
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class TestResult(Base):
    __tablename__ = "test_results"
    id = Column(Integer, primary_key=True, index=True)
    test_case_id = Column(String, index=True)
    test_case_name = Column(String)
    executor_name = Column(String)
    project_name = Column(String, default="KindleLogAnalyzer")  # Project name
    suite_name = Column(String, index=True)  # Suite name (P0, P1, P2, etc.) - indexed for filtering
    value = Column(Float)
    brd_reference = Column(Float, nullable=True)  # Reference value from BRD
    deviation_percent = Column(Float, nullable=True)  # Auto-calculated deviation from BRD
    previous_value = Column(Float, nullable=True)  # Previous build value from BRD
    deviation_from_previous = Column(Float, nullable=True)  # Auto-calculated deviation from previous build
    notes = Column(String, nullable=True, default="")  # Executor's notes for this test case
    baseline = Column(String, nullable=True, default="")  # Baseline data if applicable
    timestamp = Column(DateTime, default=datetime.now)
    status = Column(String, default="Pending") # Pending, Approved, Retest
    auditor_comment = Column(String, default="")
    is_read_by_executor = Column(Integer, default=0) # 0=No, 1=Yes

class TaskAssignment(Base):
    __tablename__ = "task_assignments"
    id = Column(Integer, primary_key=True, index=True)
    project = Column(String)  # Kindle, Mainline, etc.
    suite = Column(String)    # P0, P1, P2, Adhoc
    device_name = Column(String, default="")  # Device name (e.g., Kindle Paperwhite)
    executor_username = Column(String)
    auditor_username = Column(String)
    status = Column(String, default="Assigned")  # Assigned, In Progress, Completed
    created_at = Column(DateTime, default=datetime.now)

class AuditorBRD(Base):
    """Stores BRD file paths for each auditor/project/suite with versioning."""
    __tablename__ = "auditor_brds"
    
    id = Column(Integer, primary_key=True, index=True)
    auditor_username = Column(String, index=True)
    project = Column(String, index=True)
    suite = Column(String, index=True)
    brd_file_path = Column(String)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    version = Column(Integer, default=1)  # Version number
    is_active = Column(Integer, default=1)  # 1 = active, 0 = superseded
    replaced_by_id = Column(Integer, nullable=True)  # FK to newer version

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String, nullable=True)  # NEW: Hashed password
    full_name = Column(String)
    role = Column(String)  # admin, executor, auditor, admin

class Project(Base):
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True)
    description = Column(String, default="")

class Suite(Base):
    __tablename__ = "suites"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    description = Column(String, default="")

class ProductivityLog(Base):
    __tablename__ = "productivity_logs"
    id = Column(Integer, primary_key=True, index=True)
    executor_username = Column(String, index=True)
    session_file_name = Column(String)
    test_case_id = Column(String)
    test_case_name = Column(String)
    project_name = Column(String)
    suite_name = Column(String)
    n_points = Column(Integer, default=0)
    timestamp = Column(DateTime, default=datetime.now)
    session_date = Column(String, index=True)  # YYYY-MM-DD for daily aggregation
    week_number = Column(Integer, index=True)  # ISO week number
    year = Column(Integer)  # Year for week_number
    created_at = Column(DateTime, default=datetime.now)

Base.metadata.create_all(bind=engine)

# --- Pydantic Models ---
class ResultCreate(BaseModel):
    test_case_id: str
    test_case_name: str
    executor_name: str
    project_name: str = "KindleLogAnalyzer"  # Default value
    suite_name: str  # Required (P0, P1, P2, etc.)
    value: float
    notes: str = ""
    baseline: str = ""
    status: Optional[str] = None # Optional status override (e.g., "Blocked")

class ResultUpdate(BaseModel):
    status: str
    auditor_comment: str
    notes: Optional[str] = None
    baseline: Optional[str] = None

class ResultResponse(BaseModel):
    id: int
    test_case_id: str
    test_case_name: str
    executor_name: str
    project_name: str
    suite_name: str
    value: float
    brd_reference: Optional[float] = None
    deviation_percent: Optional[float] = None
    previous_value: Optional[float] = None
    deviation_from_previous: Optional[float] = None
    notes: str = ""
    baseline: str = ""
    timestamp: datetime
    status: str
    auditor_comment: str
    is_read_by_executor: int

    class Config:
        from_attributes = True

class TaskAssignmentCreate(BaseModel):
    project: str
    suite: str
    device_name: str = ""
    executor_username: str
    auditor_username: str

class TaskAssignmentResponse(BaseModel):
    id: int
    project: str
    suite: str
    device_name: Optional[str] = None
    executor_username: str
    auditor_username: str
    status: str
    created_at: datetime

class ProductivityLogCreate(BaseModel):
    executor_username: str
    session_file_name: str
    test_case_id: str
    test_case_name: str
    project_name: str
    suite_name: str
    n_points: int
    timestamp: Optional[datetime] = None

class ProductivityResponse(BaseModel):
    id: int
    executor_username: str
    session_file_name: str
    test_case_id: str
    test_case_name: str
    project_name: str
    suite_name: str
    n_points: int
    timestamp: datetime
    session_date: str
    week_number: int
    year: int

    class Config:
        from_attributes = True

class SuiteCreate(BaseModel):
    name: str
    description: str = ""

class SuiteResponse(BaseModel):
    id: int
    name: str
    description: str
    
    class Config:
        from_attributes = True

class UserCreate(BaseModel):
    username: str
    full_name: str
    role: str
    password: str = DEFAULT_PASSWORD  # Default password from config

class UserLogin(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    username: str
    role: str
    full_name: str

class LoginResponse(BaseModel):
    success: bool
    username: str
    full_name: str
    role: str
    message: str = ""

class UserResponse(BaseModel):
    id: int
    username: str
    full_name: str
    role: str

    class Config:
        from_attributes = True

class ProjectCreate(BaseModel):
    name: str
    description: str = ""

class ProjectResponse(BaseModel):
    id: int
    name: str
    description: str

    class Config:
        from_attributes = True

# --- Authentication Utilities ---
def verify_password(plain_password, hashed_password):
    """Verify a password against a hash."""
    if not hashed_password:
        return False
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def get_password_hash(password):
    """Hash a password."""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

# Alias for compatibility if used elsewhere
hash_password = get_password_hash

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def normalize_username(username: str) -> str:
    """Normalize username to lowercase for consistent handling."""
    return username.lower().strip()

# --- FastAPI App ---
app = FastAPI(title="Live Audit Server")

async def startup_event():
    """Run startup tasks."""
    print("🚀 Starting Live Audit Server...")
    # 1. Backup Database
    backup_database()
    
    # 2. Enable WAL Mode
    try:
        with engine.connect() as connection:
            connection.execute(text("PRAGMA journal_mode=WAL;"))
            # Verify WAL mode is active
            result = connection.execute(text("PRAGMA journal_mode;")).fetchone()
            print(f"✅ SQLite journal mode: {result[0]}")
    except Exception as e:
        print(f"⚠️ Failed to enable WAL mode: {e}")

    # 3. Create Default Admin if not exists
    try:
        db = SessionLocal()
        admin = db.query(User).filter(User.username == "admin").first()
        if not admin:
            print("⚠️ No admin user found. Creating default admin...")
            hashed_password = get_password_hash(DEFAULT_PASSWORD)
            new_admin = User(
                username="admin",
                full_name="System Administrator",
                role="admin",
                password_hash=hashed_password # Corrected from hashed_password to password_hash
            )
            db.add(new_admin)
            db.commit()
            print(f"✅ Default admin created. Username: 'admin', Password: '{DEFAULT_PASSWORD}'")
        db.close()
    except Exception as e:
        print(f"❌ Failed to create default admin: {e}")
    
    print("✅ Server startup complete!\n")

app.add_event_handler("startup", startup_event)

# --- Socket.IO Setup ---
import socketio

# Create Socket.IO server (Async)
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')
# Wrap FastAPI app with Socket.IO app
socket_app = socketio.ASGIApp(sio, app)

# --- Socket.IO Event Handlers ---
@sio.event
async def connect(sid, environ, auth):
    """Handle new WebSocket connection."""
    print(f"🔌 Client connected: {sid}")
    # Auth check (optional but recommended)
    if auth:
        token = auth.get('token')
        if token:
            try:
                # Validate token is not empty
                if not token or token.strip() == '':
                    print(f"⚠️ Empty token provided for {sid}")
                    return
                
                payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
                username = payload.get("sub")
                role = payload.get("role")
                print(f"✅ Authenticated WebSocket user: {username} ({role})")
                
                # Store user info in session
                await sio.save_session(sid, {'username': username, 'role': role})
                
                # Join personal room (for direct notifications)
                await sio.enter_room(sid, f"user_{username}")
                
                # Join role-based room
                await sio.enter_room(sid, f"role_{role}")
                
            except jwt.ExpiredSignatureError:
                print(f"⚠️ WebSocket Auth Failed: Token expired for {sid}")
            except jwt.InvalidTokenError as e:
                print(f"⚠️ WebSocket Auth Failed for {sid}: Invalid token - {e}")
            except Exception as e:
                print(f"⚠️ WebSocket Auth Failed for {sid}: {e}")
        else:
            print(f"⚠️ No token in auth dictionary for {sid}")
    else:
        print(f"⚠️ No auth dictionary provided for WebSocket connection {sid}")
    
    # Debug: Print all rooms for this SID
    print(f"🔍 Rooms for {sid}: {sio.rooms(sid)}")

@sio.event
async def disconnect(sid):
    """Handle WebSocket disconnection."""
    print(f"🔌 Client disconnected: {sid}")

@sio.event
async def join_assignment_room(sid, data):
    """Allow auditors/executors to join specific assignment rooms."""
    # data = {'project': 'Kindle', 'suite': 'P0'}
    project = data.get('project')
    suite = data.get('suite')
    if project and suite:
        room_name = f"assignment_{project}_{suite}"
        await sio.enter_room(sid, room_name)
        print(f"👤 {sid} joined room: {room_name}")

@sio.event
async def leave_assignment_room(sid, data):
    """Leave assignment room."""
    project = data.get('project')
    suite = data.get('suite')
    if project and suite:
        room_name = f"assignment_{project}_{suite}"
        await sio.leave_room(sid, room_name)
        print(f"👤 {sid} left room: {room_name}")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

from fastapi.security import OAuth2PasswordBearer
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception
    
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
    return user

# --- Authentication Endpoints ---
@app.post("/login", response_model=Token)
def login(user_credentials: UserLogin, db: Session = Depends(get_db)):
    """Authenticates a user and returns a JWT token."""
    # Normalize username
    normalized_username = normalize_username(user_credentials.username)
    
    user = db.query(User).filter(User.username == normalized_username).first()
    
    if not user or not verify_password(user_credentials.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    
    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role},
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "username": user.username,
        "role": user.role,
        "full_name": user.full_name
    }

@app.post("/submit_result", response_model=ResultResponse)
@retry_on_db_lock()
def submit_result(result: ResultCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Executor submits a test result."""
    # Verify user is the executor
    # (Optional: strictly enforce that current_user.username == result.executor_name)
    
    # Check if test case ID already exists for this run (optional, but good for integrity)son: Try to find BRD reference
    brd_reference = None
    deviation_percent = None
    auto_status = "Pending"
    previous_value = None  # Initialize at function scope
    deviation_from_previous = None  # Initialize at function scope
    
    # Use suite_name from the request (not extracted from test_case_id)
    suite = result.suite_name
    
    if suite:
        # Find BRD for this suite and project (latest uploaded)
        brd_record = db.query(AuditorBRD).filter(
            AuditorBRD.suite == suite,
            AuditorBRD.project == result.project_name
        ).order_by(AuditorBRD.uploaded_at.desc()).first()
        
        if brd_record and os.path.exists(brd_record.brd_file_path):
            try:
                # Read BRD Excel file
                df = pd.read_excel(brd_record.brd_file_path, sheet_name=suite)
                
                # Find matching test case
                matching_row = df[df['Test Case ID'] == result.test_case_id]
                
                if not matching_row.empty:
                    # Read Reference Value (BRD)
                    brd_reference = float(matching_row.iloc[0]['Reference Value'])
                    
                    # Read Previous Value if column exists
                    previous_value = None
                    deviation_from_previous = None
                    if 'Previous Value' in df.columns:
                        prev_val_raw = matching_row.iloc[0]['Previous Value']
                        if pd.notna(prev_val_raw):  # Check if not NaN/NULL
                            try:
                                previous_value = float(prev_val_raw)
                                # Calculate deviation from previous build
                                if previous_value > 0:
                                    deviation_from_previous = ((result.value - previous_value) / previous_value) * 100
                            except (ValueError, TypeError):
                                pass  # Keep as None if can't convert
                    
                    # Calculate deviation percentage from BRD Reference
                    if brd_reference > 0:
                        deviation_percent = ((result.value - brd_reference) / brd_reference) * 100
                        
                        # Auto-categorize based on deviation
                        if abs(deviation_percent) == 0:
                            auto_status = "Approved"  # Exact match → Auto-approve
                        elif abs(deviation_percent) < 10:
                            auto_status = "Pending"   # < 10% → Needs auditor review
                        else:
                            auto_status = "Pending"   # ≥ 10% → Flagged for attention
            except Exception as e:
                print(f"❌ Error reading BRD: {e}")
    
    # **Update-or-Create Logic**: Check if result already exists for this test case + executor + project + suite
    existing_result = db.query(TestResult).filter(
        TestResult.test_case_id == result.test_case_id,
        TestResult.executor_name == result.executor_name,
        TestResult.project_name == result.project_name,
        TestResult.suite_name == result.suite_name
    ).first()
    
    if existing_result:
        # **UPDATE** existing record
        print(f"♻️  Updating existing result ID {existing_result.id} for '{result.test_case_id}' by {result.executor_name}")
        existing_result.test_case_name = result.test_case_name
        existing_result.value = result.value
        existing_result.brd_reference = brd_reference
        existing_result.deviation_percent = deviation_percent
        existing_result.previous_value = previous_value
        existing_result.deviation_from_previous = deviation_from_previous
        existing_result.notes = result.notes
        existing_result.baseline = result.baseline
        existing_result.timestamp = datetime.now()  # Update timestamp to latest submission
        existing_result.status = result.status if result.status else auto_status  # Use provided status or reset to Pending
        existing_result.auditor_comment = ""  # Clear previous auditor comment
        existing_result.is_read_by_executor = 0  # Reset read flag
        db_result = existing_result
    else:
        # **CREATE** new record
        print(f"✨ Creating new result for '{result.test_case_id}' by {result.executor_name}")
        db_result = TestResult(
            test_case_id=result.test_case_id,
            test_case_name=result.test_case_name,
            executor_name=result.executor_name,
            project_name=result.project_name,
            suite_name=result.suite_name,
            value=result.value,
            brd_reference=brd_reference,
            deviation_percent=deviation_percent,
            previous_value=previous_value,
            deviation_from_previous=deviation_from_previous,
            notes=result.notes,
            baseline=result.baseline,
            status=result.status if result.status else auto_status # Use provided status or auto-calculated
        )
        db.add(db_result)
    
    db.commit()
    db.refresh(db_result)
    print(f"✅ Saved result ID {db_result.id} for executor '{result.executor_name}' - {result.test_case_id}")
    
    # --- WebSocket Broadcast ---
    # Convert result to dict for JSON serialization
    result_dict = ResultResponse.from_orm(db_result).dict()
    # Convert datetime to ISO string
    result_dict['timestamp'] = result_dict['timestamp'].isoformat()
    
    # 1. Broadcast to all auditors (general dashboard)
    print(f"📢 Broadcasting new_result to role_auditor. Data: {result_dict['test_case_name']}")
    asyncio.run(sio.emit('new_result', result_dict, room='role_auditor'))
    
    # 2. Broadcast to specific assignment room (if applicable)
    if suite:
        # Assuming project is known or passed. For now, we might need to look it up or rely on general broadcast.
        # Ideally, we'd broadcast to f"assignment_{project}_{suite}"
        pass 
        
    return db_result

@app.get("/live_dashboard", response_model=List[ResultResponse])
def get_dashboard(db: Session = Depends(get_db)):
    """Auditor fetches all results for the dashboard."""
    # Return latest 100 results for now
    results = db.query(TestResult).order_by(TestResult.timestamp.desc()).limit(100).all()
    print(f"🔍 DEBUG: /live_dashboard returning {len(results)} results")
    if len(results) > 0:
        print(f"🔍 DEBUG: Sample executors: {set([r.executor_name for r in results[:10]])}")
    return results

@app.post("/update_status/{result_id}", response_model=ResultResponse)
def update_status(result_id: int, update: ResultUpdate, db: Session = Depends(get_db)):
    """Auditor updates status (Approve/Reject)."""
    db_result = db.query(TestResult).filter(TestResult.id == result_id).first()
    if not db_result:
        raise HTTPException(status_code=404, detail="Result not found")
    
    db_result.status = update.status
    db_result.auditor_comment = update.auditor_comment
    db_result.is_read_by_executor = 0 # Reset read status so executor gets notified
    db.commit()
    db.refresh(db_result)
    
    # --- WebSocket Broadcast ---
    # Notify the specific executor immediately
    notification_data = {
        "id": db_result.id,
        "test_case_name": db_result.test_case_name,
        "status": db_result.status,
        "auditor_comment": db_result.auditor_comment,
        "timestamp": datetime.now().isoformat()
    }
    
    # Emit to the executor's personal room
    # We need to find the executor's username. It's in db_result.executor_name
    # Note: executor_name might not match username exactly if normalization differs, 
    # but we should use normalized version for room names.
    executor_room = f"user_{normalize_username(db_result.executor_name)}"
    
    print(f"📢 Emitting status update to {executor_room}")
    asyncio.run(sio.emit('status_update', notification_data, room=executor_room))
    
    return db_result

@app.get("/notifications/{executor_name}", response_model=List[ResultResponse])
def get_notifications(executor_name: str, db: Session = Depends(get_db)):
    """Executor polls for rejected/updated results."""
    # Find results for this executor that are Rejected and NOT read yet
    results = db.query(TestResult).filter(
        TestResult.executor_name == executor_name,
        TestResult.status == "Rejected",
        TestResult.is_read_by_executor == 0
    ).all()
    return results

@app.post("/mark_read/{result_id}")
def mark_read(result_id: int, db: Session = Depends(get_db)):
    """Executor marks a notification as read."""
    db_result = db.query(TestResult).filter(TestResult.id == result_id).first()
    if db_result:
        db_result.is_read_by_executor = 1
        db.commit()
    return {"status": "ok"}

@app.post("/task_assignments", response_model=TaskAssignmentResponse)
@retry_on_db_lock()
def create_task_assignment(assignment: TaskAssignmentCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Admin assigns a task to an executor and auditor."""
    # Verify admin role
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
        
    # Normalize usernames
    db_task = TaskAssignment(
        project=assignment.project,
        suite=assignment.suite,
        executor_username=assignment.executor_username,
        auditor_username=assignment.auditor_username,
        status="Assigned"
    )
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task

@app.get("/my_tasks/{executor_username}", response_model=List[TaskAssignmentResponse])
def get_my_tasks(executor_username: str, db: Session = Depends(get_db)):
    """Get tasks assigned to an executor (case-insensitive)."""
    normalized_username = normalize_username(executor_username)
    tasks = db.query(TaskAssignment).filter(
        TaskAssignment.executor_username == normalized_username,
        TaskAssignment.status != "Completed"
    ).all()
    return tasks

@app.get("/my_audits/{auditor_username}", response_model=List[TaskAssignmentResponse])
def get_my_audits(auditor_username: str, db: Session = Depends(get_db)):
    """Get audits assigned to an auditor (case-insensitive)."""
    normalized_username = normalize_username(auditor_username)
    tasks = db.query(TaskAssignment).filter(
        TaskAssignment.auditor_username == normalized_username
    ).all()
    return tasks

@app.get("/all_task_assignments", response_model=List[TaskAssignmentResponse])
def get_all_assignments(db: Session = Depends(get_db)):
    """Admin fetches all task assignments."""
    return db.query(TaskAssignment).order_by(TaskAssignment.created_at.desc()).all()

# Suite Management Endpoints
@app.get("/suites", response_model=List[SuiteResponse])
def get_suites(db: Session = Depends(get_db)):
    """Get all suites."""
    return db.query(Suite).order_by(Suite.name).all()

@app.post("/suites", response_model=SuiteResponse)
@retry_on_db_lock()
def create_suite(suite: SuiteCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Admin creates a new suite."""
    # Verify admin role
    if "admin" not in current_user.role.lower():
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Check for duplicate
    existing = db.query(Suite).filter(Suite.name == suite.name).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Suite '{suite.name}' already exists")
    
    db_suite = Suite(name=suite.name, description=suite.description)
    db.add(db_suite)
    db.commit()
    db.refresh(db_suite)
    return db_suite

@app.delete("/suites/{suite_id}")
@retry_on_db_lock()
def delete_suite(suite_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Admin deletes a suite (only if not referenced in task assignments)."""
    # Verify admin role
    if "admin" not in current_user.role.lower():
        raise HTTPException(status_code=403, detail="Admin access required")
    
    suite = db.query(Suite).filter(Suite.id == suite_id).first()
    if not suite:
        raise HTTPException(status_code=404, detail="Suite not found")
    
    # Check if suite is referenced in any task assignments
    referenced = db.query(TaskAssignment).filter(TaskAssignment.suite == suite.name).first()
    if referenced:
        raise HTTPException(status_code=400, detail=f"Cannot delete suite '{suite.name}' - it is referenced in existing task assignments")
    
    db.delete(suite)
    db.commit()
    return {"message": f"Suite '{suite.name}' deleted successfully"}

# User Management Endpoints
@app.post("/users", response_model=UserResponse)
@retry_on_db_lock()
def create_user(user: UserCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Admin creates a new user with hashed password."""
    # Verify admin role
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
        
    # Normalize username before saving
    normalized_username = normalize_username(user.username)
    
    # Check if user already exists
    existing_user = db.query(User).filter(User.username == normalized_username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    # Hash the password
    hashed_pwd = hash_password(user.password)
    
    db_user = User(
        username=normalized_username, 
        full_name=user.full_name, 
        role=user.role,
        password_hash=hashed_pwd
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@app.get("/users", response_model=List[UserResponse])
def get_all_users(db: Session = Depends(get_db)):
    """Fetch all users."""
    return db.query(User).all()

@app.put("/users/{username}", response_model=UserResponse)
def update_user(username: str, user: UserCreate, db: Session = Depends(get_db)):
    """Admin updates a user's info."""
    db_user = db.query(User).filter(User.username == username).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    db_user.full_name = user.full_name
    db_user.role = user.role
    db.commit()
    db.refresh(db_user)
    return db_user

@app.get("/users/executors", response_model=List[UserResponse])
def get_executors(db: Session = Depends(get_db)):
    """Fetch all users who can execute (have 'executor' role)."""
    all_users = db.query(User).all()
    return [u for u in all_users if 'executor' in u.role.lower()]

@app.get("/users/auditors", response_model=List[UserResponse])
def get_auditors(db: Session = Depends(get_db)):
    """Fetch all users who can audit (have 'auditor' role)."""
    all_users = db.query(User).all()
    return [u for u in all_users if 'auditor' in u.role.lower()]

# Project Management Endpoints
@app.post("/projects", response_model=ProjectResponse)
@retry_on_db_lock()
def create_project(project: ProjectCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Admin creates a new project."""
    # Verify admin role
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
        
    # Check if project already exists
    existing_project = db.query(Project).filter(Project.name == project.name).first()
    if existing_project:
        raise HTTPException(status_code=400, detail="Project already exists")
        
    db_project = Project(name=project.name, description=project.description)
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    return db_project

@app.get("/projects", response_model=List[ProjectResponse])
def get_all_projects(db: Session = Depends(get_db)):
    """Fetch all projects."""
    return db.query(Project).all()

# BRD Management Endpoints
def validate_brd_format(file_path: str, suite: str) -> tuple[bool, str]:
    """
    Validate BRD Excel file format.
    Returns (is_valid, error_message)
    """
    required_columns = ['Test Case ID', 'Test Case Name', 'Reference Value']
    
    try:
        # Check if suite is provided
        if not suite:
            return False, "Suite parameter is required"
        
        # Try to read the Excel file
        df = pd.read_excel(file_path, sheet_name=suite)
        
        # Check for required columns
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            return False, f"Missing columns: {', '.join(missing_columns)}. Required: {', '.join(required_columns)}"
        
        # Check if Reference Value column contains numeric data
        if not pd.api.types.is_numeric_dtype(df['Reference Value']):
            return False, "'Reference Value' column must contain numeric data"
        
        # Check for empty Test Case ID
        if df['Test Case ID'].isnull().any():
            return False, "'Test Case ID' column contains empty values"
        
        return True, "Valid"
        
    except ValueError as e:
        return False, f"Sheet '{suite}' not found in Excel file. Please ensure the sheet name matches the suite."
    except Exception as e:
        return False, f"Error reading Excel file: {str(e)}"

# Template Management
TEMPLATE_DIR = "templates"
TEMPLATE_FILENAME = "master_template.xlsx"

@app.get("/template")
async def get_template():
    """Downloads the current master template."""
    file_path = os.path.join(TEMPLATE_DIR, TEMPLATE_FILENAME)
    if os.path.exists(file_path):
        return FileResponse(file_path, filename=TEMPLATE_FILENAME, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    else:
        raise HTTPException(status_code=404, detail="Master template not found on server.")

@app.post("/template")
async def upload_template(file: UploadFile = File(...)):
    """Uploads a new master template, backing up the old one."""
    if not file.filename.endswith('.xlsx'):
        raise HTTPException(status_code=400, detail="Invalid file type. Only .xlsx files are allowed.")

    # Ensure directory exists
    if not os.path.exists(TEMPLATE_DIR):
        os.makedirs(TEMPLATE_DIR)

    file_path = os.path.join(TEMPLATE_DIR, TEMPLATE_FILENAME)

    # Backup existing template
    if os.path.exists(file_path):
        backup_name = f"master_template_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        backup_path = os.path.join(TEMPLATE_DIR, backup_name)
        shutil.move(file_path, backup_path)

    # Save new template
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        return {"message": "Template uploaded successfully", "filename": file.filename}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save template: {str(e)}")

@app.post("/upload_brd")
@retry_on_db_lock_async()
async def upload_brd(
    file: UploadFile = File(...),
    auditor_username: str = Form(...),
    project: str = Form(...),
    suite: str = Form(...),
    token: str = Form(...),
    db: Session = Depends(get_db)
):
    """Auditor uploads a BRD Excel file."""
    print(f"DEBUG: upload_brd called. Token: {token[:10]}...")
    # Verify token manually (since OAuth2PasswordBearer doesn't support Form data easily)
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        role: str = payload.get("role")
        print(f"DEBUG: Token decoded. Username: {username}, Role: {role}")
        
        # Check if user has auditor or admin role (handles comma-separated roles)
        if "auditor" not in role and "admin" not in role:
             raise HTTPException(status_code=403, detail="Not authorized")
    except Exception as e:
        print(f"DEBUG: Token validation failed: {e}")
        raise HTTPException(status_code=401, detail="Not authenticated")

    # Validate file extension
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Invalid file type. Only .xlsx and .xls files are allowed.")
        
    # Create uploads directory if it doesn't exist
    upload_dir = "brd_uploads"
    os.makedirs(upload_dir, exist_ok=True)
    
    # Add timestamp to prevent overwriting
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    file_path = os.path.join(upload_dir, f"{auditor_username}_{project}_{suite}_{timestamp}_{file.filename}")
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Validate BRD format
    is_valid, error_msg = validate_brd_format(file_path, suite)
    if not is_valid:
        # Delete invalid file
        os.remove(file_path)
        raise HTTPException(status_code=400, detail=f"Invalid BRD format: {error_msg}")
    
    # Check for existing active BRD and mark it as superseded
    existing_brd = db.query(AuditorBRD).filter(
        AuditorBRD.project == project,
        AuditorBRD.suite == suite,
        AuditorBRD.is_active == 1
    ).first()
    
    new_version = 1
    if existing_brd:
        # Mark old BRD as inactive
        existing_brd.is_active = 0
        new_version = existing_brd.version + 1
        print(f"📦 Superseding BRD v{existing_brd.version} with v{new_version}")
    
    # Save new BRD record with version
    db_brd = AuditorBRD(
        auditor_username=auditor_username,
        project=project,
        suite=suite,
        brd_file_path=file_path,
        version=new_version,
        is_active=1
    )
    db.add(db_brd)
    
    # Update old BRD's replaced_by_id
    if existing_brd:
        db.commit()  # Commit to get new BRD id
        db.refresh(db_brd)
        existing_brd.replaced_by_id = db_brd.id
    
    db.commit()
    db.refresh(db_brd)
    
    return {
        "status": "success", 
        "file_path": file_path, 
        "id": db_brd.id, 
        "version": new_version,
        "message": f"BRD v{new_version} validated and uploaded successfully"
    }

@app.get("/check_brd/{project}/{suite}")
def check_brd_status(project: str, suite: str, db: Session = Depends(get_db)):
    """Check if BRD exists for a project/suite (active version only)."""
    brd = db.query(AuditorBRD).filter(
        AuditorBRD.project == project,
        AuditorBRD.suite == suite,
        AuditorBRD.is_active == 1  # Only active BRDs
    ).order_by(AuditorBRD.uploaded_at.desc()).first()
    
    if brd:
        return {
            "exists": True, 
            "uploaded_at": brd.uploaded_at.isoformat(),
            "version": brd.version
        }
    return {"exists": False}

# =============================================================================
# PRODUCTIVITY TRACKING ENDPOINTS
# =============================================================================

@app.post("/productivity/log")
def log_productivity(log: ProductivityLogCreate, db: Session = Depends(get_db)):
    """Log N-points when a test case is completed"""
    from datetime import datetime
    
    # Use provided timestamp or current time
    timestamp = log.timestamp if log.timestamp else datetime.now()
    
    # Calculate session_date, week_number, and year
    session_date = timestamp.strftime("%Y-%m-%d")
    week_number = timestamp.isocalendar()[1]  # ISO week number
    year = timestamp.year
    
    # Create log entry
    db_log = ProductivityLog(
        executor_username=log.executor_username,
        session_file_name=log.session_file_name,
        test_case_id=log.test_case_id,
        test_case_name=log.test_case_name,
        project_name=log.project_name,
        suite_name=log.suite_name,
        n_points=log.n_points,
        timestamp=timestamp,
        session_date=session_date,
        week_number=week_number,
        year=year
    )
    
    db.add(db_log)
    db.commit()
    db.refresh(db_log)
    
    return {"status": "success", "id": db_log.id}

@app.get("/productivity/daily/{username}")
def get_daily_productivity(username: str, date: str = None, db: Session = Depends(get_db)):
    """Get daily productivity for a specific user"""
    from datetime import datetime, date as dt_date
    
    # Use provided date or today
    if date:
        target_date = date
    else:
        target_date = datetime.now().strftime("%Y-%m-%d")
    
    # Query logs for this user on this date
    logs = db.query(ProductivityLog).filter(
        ProductivityLog.executor_username == username,
        ProductivityLog.session_date == target_date
    ).all()
    
    total_n_points = sum(log.n_points for log in logs)
    test_cases_completed = len(logs)
    
    # Group by suite
    breakdown_by_suite = {}
    for log in logs:
        suite = log.suite_name
        breakdown_by_suite[suite] = breakdown_by_suite.get(suite, 0) + log.n_points
    
    return {
        "username": username,
        "date": target_date,
        "total_n_points": total_n_points,
        "test_cases_completed": test_cases_completed,
        "breakdown_by_suite": breakdown_by_suite
    }

@app.get("/productivity/weekly/{username}")
def get_weekly_productivity(username: str, week: int = None, year: int = None, db: Session = Depends(get_db)):
    """Get weekly productivity summary"""
    from datetime import datetime
    
    # Use provided week/year or current
    if not week or not year:
        now = datetime.now()
        iso_cal = now.isocalendar()
        week = iso_cal[1]
        year = iso_cal[0]
    
    # Query logs for this user in this week
    logs = db.query(ProductivityLog).filter(
        ProductivityLog.executor_username == username,
        ProductivityLog.week_number == week,
        ProductivityLog.year == year
    ).all()
    
    total_n_points = sum(log.n_points for log in logs)
    test_cases_completed = len(logs)
    
    # Group by date for daily breakdown
    daily_breakdown = {}
    for log in logs:
        date = log.session_date
        daily_breakdown[date] = daily_breakdown.get(date, 0) + log.n_points
    
    # Convert to list format
    daily_list = [{"date": d, "points": p} for d, p in sorted(daily_breakdown.items())]
    
    avg_points_per_day = total_n_points / max(len(daily_breakdown), 1)
    
    return {
        "username": username,
        "week": week,
        "year": year,
        "total_n_points": total_n_points,
        "daily_breakdown": daily_list,
        "test_cases_completed": test_cases_completed,
        "avg_points_per_day": round(avg_points_per_day, 1)
    }

@app.get("/productivity/leaderboard")
def get_leaderboard(period: str = "week", db: Session = Depends(get_db)):
    """Get team leaderboard"""
    from datetime import datetime
    from sqlalchemy import func
    
    now = datetime.now()
    
    if period == "day":
        target_date = now.strftime("%Y-%m-%d")
        query = db.query(
            ProductivityLog.executor_username,
            func.sum(ProductivityLog.n_points).label('total_points')
        ).filter(
            ProductivityLog.session_date == target_date
        ).group_by(ProductivityLog.executor_username)
    
    elif period == "week":
        iso_cal = now.isocalendar()
        week = iso_cal[1]
        year = iso_cal[0]
        query = db.query(
            ProductivityLog.executor_username,
            func.sum(ProductivityLog.n_points).label('total_points')
        ).filter(
            ProductivityLog.week_number == week,
            ProductivityLog.year == year
        ).group_by(ProductivityLog.executor_username)
    
    elif period == "month":
        month = now.month
        year = now.year
        query = db.query(
            ProductivityLog.executor_username,
            func.sum(ProductivityLog.n_points).label('total_points')
        ).filter(
            func.strftime('%Y-%m', ProductivityLog.session_date) == f"{year}-{month:02d}"
        ).group_by(ProductivityLog.executor_username)
    
    else:
        return {"error": "Invalid period. Use 'day', 'week', or 'month'"}
    
    results = query.order_by(func.sum(ProductivityLog.n_points).desc()).all()
    
    # Fetch full names from users table
    leaderboard = []
    for rank, (username, points) in enumerate(results, 1):
        user = db.query(User).filter(User.username == username).first()
        full_name = user.full_name if user else username
        
        leaderboard.append({
            "rank": rank,
            "username": username,
            "full_name": full_name,
            "points": points
        })
    
    # Calculate team average
    team_total = sum(item["points"] for item in leaderboard)
    team_average = team_total / max(len(leaderboard), 1)
    
    return {
        "period": period,
        "leaderboard": leaderboard,
        "team_average": round(team_average, 1)
    }

@app.get("/productivity/all")
def get_all_productivity(
    period: str = "week",
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get productivity data for all executors (admin only)"""
    # Check admin permission
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    from datetime import datetime
    from sqlalchemy import func
    
    now = datetime.now()
    
    if period == "week":
        iso_cal = now.isocalendar()
        week = iso_cal[1]
        year = iso_cal[0]
        query = db.query(
            ProductivityLog.executor_username,
            func.sum(ProductivityLog.n_points).label('total_points'),
            func.count(ProductivityLog.id).label('test_cases')
        ).filter(
            ProductivityLog.week_number == week,
            ProductivityLog.year == year
        ).group_by(ProductivityLog.executor_username)
    else:
        # Can add other periods later
        query = db.query(
            ProductivityLog.executor_username,
            func.sum(ProductivityLog.n_points).label('total_points'),
            func.count(ProductivityLog.id).label('test_cases')
        ).group_by(ProductivityLog.executor_username)
    
    results = query.all()
    
    executors = []
    for username, points, test_cases in results:
        user = db.query(User).filter(User.username == username).first()
        full_name = user.full_name if user else username
        
        # Calculate daily avg (assuming 5 working days per week)
        daily_avg = points / 5 if period == "week" else points
        
        executors.append({
            "username": username,
            "full_name": full_name,
            "total_points": points,
            "daily_avg": round(daily_avg, 1),
            "test_cases": test_cases
        })
    
    team_total = sum(e["total_points"] for e in executors)
    team_average = team_total / max(len(executors), 1)
    
    return {
        "period": period,
        "executors": executors,
        "team_total": team_total,
        "team_average": round(team_average, 1)
    }

if __name__ == "__main__":
    # Check if port is already in use
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('127.0.0.1', SERVER_PORT))
    sock.close()
    
    if result == 0:
        print(f"\n❌ ERROR: Port {SERVER_PORT} is already in use!")
        print("Please stop the existing server or change the port.")
        print(f"To kill the process using port {SERVER_PORT}, run: lsof -ti:{SERVER_PORT} | xargs kill -9\n")
        exit(1)

    # Initialize default suites if database is empty
    try:
        db = SessionLocal()
        suite_count = db.query(Suite).count()
        if suite_count == 0:
            print("📝 Initializing default suites...")
            default_suites = [
                Suite(name="P0", description="Priority 0 - Critical"),
                Suite(name="P1", description="Priority 1 - High"),
                Suite(name="P2", description="Priority 2 - Medium"),
                Suite(name="Adhoc", description="Ad-hoc testing"),
            ]
            for suite in default_suites:
                db.add(suite)
            db.commit()
            print("✅ Default suites initialized: P0, P1, P2, Adhoc")
        db.close()
    except Exception as e:
        print(f"⚠️ Warning: Could not initialize default suites: {e}")

    print("🚀 Starting Live Audit Server...")
    uvicorn.run(socket_app, host="0.0.0.0", port=SERVER_PORT)

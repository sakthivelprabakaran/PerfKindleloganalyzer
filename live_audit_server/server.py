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

# --- Auto-Backup Function ---
def backup_database():
    """Create automatic backup of database on server startup."""
    db_file = "live_audit.db"
    backup_dir = "backups"
    
    if not os.path.exists(db_file):
        print("ℹ️  No existing database to backup.")
        return
    
    # Create backups directory
    os.makedirs(backup_dir, exist_ok=True)
    
    # Create backup with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = os.path.join(backup_dir, f"live_audit_backup_{timestamp}.db")
    
    try:
        shutil.copy2(db_file, backup_file)
        print(f"✅ Database backed up: {backup_file}")
        
        # Keep only last 30 backups
        backups = sorted([f for f in os.listdir(backup_dir) if f.endswith('.db')])
        if len(backups) > 30:
            for old_backup in backups[:-30]:
                os.remove(os.path.join(backup_dir, old_backup))
                print(f"🗑️  Removed old backup: {old_backup}")
    except Exception as e:
        print(f"⚠️  Backup failed: {e}")

# --- Database Setup ---
SQLALCHEMY_DATABASE_URL = "sqlite:///./live_audit.db"

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
    value = Column(Float)
    brd_reference = Column(Float, nullable=True)  # Reference value from BRD
    deviation_percent = Column(Float, nullable=True)  # Auto-calculated deviation
    timestamp = Column(DateTime, default=datetime.now)
    status = Column(String, default="Pending") # Pending, Approved, Retest
    auditor_comment = Column(String, default="")
    is_read_by_executor = Column(Integer, default=0) # 0=No, 1=Yes

class TaskAssignment(Base):
    __tablename__ = "task_assignments"
    id = Column(Integer, primary_key=True, index=True)
    project = Column(String)  # Kindle, Mainline, etc.
    suite = Column(String)    # P0, P1, P2, Adhoc
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
    username = Column(String, unique=True)
    full_name = Column(String)
    role = Column(String)  # executor, auditor, admin

class Project(Base):
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True)
    description = Column(String, default="")

Base.metadata.create_all(bind=engine)

# --- Pydantic Models ---
class ResultCreate(BaseModel):
    test_case_id: str
    test_case_name: str
    executor_name: str
    value: float

class ResultUpdate(BaseModel):
    status: str
    auditor_comment: str

class ResultResponse(BaseModel):
    id: int
    test_case_id: str
    test_case_name: str
    executor_name: str
    value: float
    brd_reference: Optional[float] = None
    deviation_percent: Optional[float] = None
    timestamp: datetime
    status: str
    auditor_comment: str
    is_read_by_executor: int

    class Config:
        orm_mode = True

class TaskAssignmentCreate(BaseModel):
    project: str
    suite: str
    executor_username: str
    auditor_username: str

class TaskAssignmentResponse(BaseModel):
    id: int
    project: str
    suite: str
    executor_username: str
    auditor_username: str
    status: str
    created_at: datetime

    class Config:
        orm_mode = True

class UserCreate(BaseModel):
    username: str
    full_name: str
    role: str

class UserResponse(BaseModel):
    id: int
    username: str
    full_name: str
    role: str

    class Config:
        orm_mode = True

class ProjectCreate(BaseModel):
    name: str
    description: str = ""

class ProjectResponse(BaseModel):
    id: int
    name: str
    description: str

    class Config:
        orm_mode = True

# --- FastAPI App ---
app = FastAPI(title="Live Audit Server")

@app.on_event("startup")
async def startup_event():
    """Run on server startup: backup database and enable WAL mode."""
    print("🚀 Starting Live Audit Server...")
    
    # 1. Backup existing database
    backup_database()
    
    # 2. Enable WAL mode for better concurrency
    try:
        with engine.connect() as conn:
            conn.execute(text("PRAGMA journal_mode=WAL;"))
            result = conn.execute(text("PRAGMA journal_mode;")).fetchone()
            print(f"✅ SQLite journal mode: {result[0]}")
    except Exception as e:
        print(f"⚠️  WAL mode setup failed: {e}")
    
    print("✅ Server startup complete!\n")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Helper Functions ---
def normalize_username(username: str) -> str:
    """Normalize username to lowercase for case-insensitive matching."""
    return username.lower().strip() if username else ""

@app.post("/submit_result", response_model=ResultResponse)
def submit_result(result: ResultCreate, db: Session = Depends(get_db)):
    """Executor submits a new test result with auto-comparison against BRD."""
    
    # Auto-comparison: Try to find BRD reference
    brd_reference = None
    deviation_percent = None
    auto_status = "Pending"
    
    # Extract suite from test_case_id (e.g., "P03" → "P0")
    suite = result.test_case_id[:2] if len(result.test_case_id) >= 2 else None
    
    if suite:
        # Find BRD for this suite (latest uploaded)
        brd_record = db.query(AuditorBRD).filter(
            AuditorBRD.suite == suite
        ).order_by(AuditorBRD.uploaded_at.desc()).first()
        
        if brd_record and os.path.exists(brd_record.brd_file_path):
            try:
                # Read BRD Excel file
                df = pd.read_excel(brd_record.brd_file_path, sheet_name=suite)
                
                # Find matching test case
                matching_row = df[df['Test Case ID'] == result.test_case_id]
                
                if not matching_row.empty:
                    brd_reference = float(matching_row.iloc[0]['Reference Value'])
                    
                    # Calculate deviation percentage
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
                print(f"Error reading BRD: {e}")
    
    db_result = TestResult(
        test_case_id=result.test_case_id,
        test_case_name=result.test_case_name,
        executor_name=result.executor_name,
        value=result.value,
        brd_reference=brd_reference,
        deviation_percent=deviation_percent,
        status=auto_status
    )
    db.add(db_result)
    db.commit()
    db.refresh(db_result)
    return db_result

@app.get("/live_dashboard", response_model=List[ResultResponse])
def get_dashboard(db: Session = Depends(get_db)):
    """Auditor fetches all results for the dashboard."""
    # Return latest 100 results for now
    return db.query(TestResult).order_by(TestResult.timestamp.desc()).limit(100).all()

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
def create_task_assignment(task: TaskAssignmentCreate, db: Session = Depends(get_db)):
    """Admin creates a new task assignment."""
    db_task = TaskAssignment(
        project=task.project,
        suite=task.suite,
        executor_username=task.executor_username,
        auditor_username=task.auditor_username,
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

# User Management Endpoints
@app.post("/users", response_model=UserResponse)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    """Admin creates a new user."""
    # Normalize username before saving
    normalized_username = normalize_username(user.username)
    db_user = User(username=normalized_username, full_name=user.full_name, role=user.role)
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
def create_project(project: ProjectCreate, db: Session = Depends(get_db)):
    """Admin creates a new project."""
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

@app.post("/upload_brd")
async def upload_brd(
    file: UploadFile = File(...),
    auditor_username: str = Form(""),
    project: str = Form(""),
    suite: str = Form(""),
    db: Session = Depends(get_db)
):
    """Auditor uploads BRD Excel file for a specific suite with validation."""
    
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

if __name__ == "__main__":
    # Run on 0.0.0.0 to be accessible on LAN
    uvicorn.run(app, host="0.0.0.0", port=8000)

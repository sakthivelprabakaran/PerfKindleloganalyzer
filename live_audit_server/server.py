from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime
import uvicorn
from typing import List, Optional

# --- Database Setup ---
SQLALCHEMY_DATABASE_URL = "sqlite:///./live_audit.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class TestResult(Base):
    __tablename__ = "test_results"
    id = Column(Integer, primary_key=True, index=True)
    test_case_id = Column(String, index=True)
    test_case_name = Column(String)
    executor_name = Column(String)
    value = Column(Float)
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
    __tablename__ = "auditor_brds"
    id = Column(Integer, primary_key=True, index=True)
    auditor_username = Column(String)
    project = Column(String)
    suite = Column(String)
    brd_file_path = Column(String)
    uploaded_at = Column(DateTime, default=datetime.now)

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

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/submit_result", response_model=ResultResponse)
def submit_result(result: ResultCreate, db: Session = Depends(get_db)):
    """Executor submits a new test result."""
    db_result = TestResult(
        test_case_id=result.test_case_id,
        test_case_name=result.test_case_name,
        executor_name=result.executor_name,
        value=result.value,
        status="Pending"
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
    """Executor fetches their assigned tasks."""
    return db.query(TaskAssignment).filter(
        TaskAssignment.executor_username == executor_username,
        TaskAssignment.status != "Completed"
    ).all()

@app.get("/my_audits/{auditor_username}", response_model=List[TaskAssignmentResponse])
def get_my_audits(auditor_username: str, db: Session = Depends(get_db)):
    """Auditor fetches their assigned audits."""
    return db.query(TaskAssignment).filter(
        TaskAssignment.auditor_username == auditor_username
    ).all()

@app.get("/all_task_assignments", response_model=List[TaskAssignmentResponse])
def get_all_assignments(db: Session = Depends(get_db)):
    """Admin fetches all task assignments."""
    return db.query(TaskAssignment).order_by(TaskAssignment.created_at.desc()).all()

# User Management Endpoints
@app.post("/users", response_model=UserResponse)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    """Admin creates a new user."""
    db_user = User(username=user.username, full_name=user.full_name, role=user.role)
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

if __name__ == "__main__":
    # Run on 0.0.0.0 to be accessible on LAN
    uvicorn.run(app, host="0.0.0.0", port=8000)

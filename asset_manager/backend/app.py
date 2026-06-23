import base64
import hashlib
import hmac
import json
import os
import time
from typing import Optional

import bcrypt
from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field
from psycopg2 import IntegrityError
from psycopg2.extras import RealDictCursor

from .database.db import get_connection


TOKEN_SECRET = os.getenv("TOKEN_SECRET", "change-this-secret-for-production")
TOKEN_EXPIRY_SECONDS = 8 * 60 * 60
ASSET_STATUSES = {"Available", "Assigned", "Maintenance", "Retired"}

app = FastAPI(title="Asset Management API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class LoginRequest(BaseModel):
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)


class EmployeeRequest(BaseModel):
    name: str = Field(min_length=1)
    email: EmailStr
    department: str = Field(min_length=1)


class AssetRequest(BaseModel):
    asset_name: str = Field(min_length=1)
    asset_type: str = Field(min_length=1)
    serial_number: str = Field(min_length=1)
    status: str = Field(default="Available")


class AssignmentRequest(BaseModel):
    employee_id: int
    asset_id: int


def db_query(query, params=None, fetch_one=False, fetch_all=False):
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(query, params or ())
            result = None
            if fetch_one:
                result = cursor.fetchone()
            if fetch_all:
                result = cursor.fetchall()
        conn.commit()
        return result
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def make_token(user: dict) -> str:
    payload = {
        "id": user["id"],
        "username": user["username"],
        "role": user["role"],
        "exp": int(time.time()) + TOKEN_EXPIRY_SECONDS,
    }
    payload_text = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    payload_part = base64.urlsafe_b64encode(payload_text).decode("utf-8").rstrip("=")
    signature = hmac.new(TOKEN_SECRET.encode("utf-8"), payload_part.encode("utf-8"), hashlib.sha256).digest()
    signature_part = base64.urlsafe_b64encode(signature).decode("utf-8").rstrip("=")
    return f"{payload_part}.{signature_part}"


def read_token(token: str) -> dict:
    try:
        payload_part, signature_part = token.split(".")
        expected_signature = hmac.new(
            TOKEN_SECRET.encode("utf-8"), payload_part.encode("utf-8"), hashlib.sha256
        ).digest()
        actual_signature = base64.urlsafe_b64decode(signature_part + "=" * (-len(signature_part) % 4))
        if not hmac.compare_digest(expected_signature, actual_signature):
            raise ValueError
        payload_json = base64.urlsafe_b64decode(payload_part + "=" * (-len(payload_part) % 4))
        payload = json.loads(payload_json)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc

    if payload.get("exp", 0) < int(time.time()):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired")

    return payload


def current_user(authorization: Optional[str] = Header(default=None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Login required")
    return read_token(authorization.replace("Bearer ", "", 1))


def admin_user(user=Depends(current_user)):
    if user["role"] != "Admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user


def clean_asset(data: AssetRequest):
    asset = data.dict()
    asset["status"] = asset["status"].strip()
    if asset["status"] not in ASSET_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid asset status")
    return asset


def initialize_database():
    db_query(
        """
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role VARCHAR(20) NOT NULL CHECK (role IN ('Admin', 'User'))
        );

        CREATE TABLE IF NOT EXISTS employees (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            email VARCHAR(150) UNIQUE NOT NULL,
            department VARCHAR(100) NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS assets (
            id SERIAL PRIMARY KEY,
            asset_name VARCHAR(120) NOT NULL,
            asset_type VARCHAR(80) NOT NULL,
            serial_number VARCHAR(120) UNIQUE NOT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'Available'
                CHECK (status IN ('Available', 'Assigned', 'Maintenance', 'Retired')),
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS assignments (
            id SERIAL PRIMARY KEY,
            employee_id INTEGER NOT NULL REFERENCES employees(id) ON DELETE RESTRICT,
            asset_id INTEGER NOT NULL REFERENCES assets(id) ON DELETE RESTRICT,
            assigned_date DATE NOT NULL DEFAULT CURRENT_DATE,
            returned_date DATE,
            CHECK (returned_date IS NULL OR returned_date >= assigned_date)
        );

        CREATE INDEX IF NOT EXISTS idx_assignments_employee_id ON assignments(employee_id);
        CREATE INDEX IF NOT EXISTS idx_assignments_asset_id ON assignments(asset_id);
        CREATE INDEX IF NOT EXISTS idx_assets_status ON assets(status);
        """
    )
    db_query(
        """
        ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash TEXT;
        ALTER TABLE users ADD COLUMN IF NOT EXISTS role VARCHAR(20) DEFAULT 'User';
        ALTER TABLE assets ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'Available';
        ALTER TABLE assignments ADD COLUMN IF NOT EXISTS returned_date DATE;
        """
    )
    db_query(
        """
        UPDATE assets
        SET status = 'Available'
        WHERE status IS NULL;

        UPDATE assets
        SET status = 'Assigned'
        WHERE id IN (
            SELECT asset_id
            FROM assignments
            WHERE returned_date IS NULL
        );
        """
    )

    seed_user("admin", "admin123", "Admin")
    seed_user("user", "user123", "User")


def table_has_column(table_name: str, column_name: str) -> bool:
    column = db_query(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = %s AND column_name = %s
        """,
        (table_name, column_name),
        fetch_one=True,
    )
    return bool(column)


def seed_user(username: str, password: str, role: str):
    existing = db_query("SELECT id, password_hash FROM users WHERE username = %s", (username,), fetch_one=True)
    if existing:
        if not existing.get("password_hash"):
            db_query(
                "UPDATE users SET password_hash = %s, role = %s WHERE id = %s",
                (hash_password(password), role, existing["id"]),
            )
        return

    password_hash = hash_password(password)
    if table_has_column("users", "password"):
        db_query(
            "INSERT INTO users (username, password, password_hash, role) VALUES (%s, %s, %s, %s)",
            (username, "", password_hash, role),
        )
    else:
        db_query(
            "INSERT INTO users (username, password_hash, role) VALUES (%s, %s, %s)",
            (username, password_hash, role),
        )


@app.on_event("startup")
def startup():
    initialize_database()


@app.get("/")
def home():
    return {"message": "Asset Management API Running"}


@app.post("/login")
def login(data: LoginRequest):
    user = db_query(
        "SELECT id, username, password_hash, role FROM users WHERE username = %s",
        (data.username.strip(),),
        fetch_one=True,
    )
    if not user or not verify_password(data.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    return {
        "message": "Login successful",
        "token": make_token(user),
        "username": user["username"],
        "role": user["role"],
    }


@app.get("/me")
def me(user=Depends(current_user)):
    return {"username": user["username"], "role": user["role"]}


@app.get("/dashboard")
def dashboard(user=Depends(current_user)):
    stats = db_query(
        """
        SELECT
            (SELECT COUNT(*) FROM employees) AS total_employees,
            (SELECT COUNT(*) FROM assets) AS total_assets,
            (SELECT COUNT(*) FROM assets WHERE status = 'Assigned') AS assigned_assets,
            (SELECT COUNT(*) FROM assets WHERE status = 'Available') AS available_assets
        """,
        fetch_one=True,
    )
    recent = db_query(
        """
        SELECT ass.id, e.name AS employee_name, a.asset_name, ass.assigned_date, ass.returned_date
        FROM assignments ass
        JOIN employees e ON ass.employee_id = e.id
        JOIN assets a ON ass.asset_id = a.id
        ORDER BY ass.id DESC
        LIMIT 5
        """,
        fetch_all=True,
    )
    return {"stats": stats, "recent_assignments": recent}


@app.get("/employees")
def get_employees(search: str = "", user=Depends(current_user)):
    term = f"%{search.strip()}%"
    return db_query(
        """
        SELECT id, name, email, department
        FROM employees
        WHERE %s = '' OR name ILIKE %s OR email ILIKE %s OR department ILIKE %s
        ORDER BY id
        """,
        (search.strip(), term, term, term),
        fetch_all=True,
    )


@app.post("/employees", status_code=201)
def create_employee(data: EmployeeRequest, user=Depends(admin_user)):
    try:
        return db_query(
            """
            INSERT INTO employees (name, email, department)
            VALUES (%s, %s, %s)
            RETURNING id, name, email, department
            """,
            (data.name.strip(), data.email.lower(), data.department.strip()),
            fetch_one=True,
        )
    except IntegrityError as exc:
        raise HTTPException(status_code=400, detail="Employee email already exists") from exc


@app.put("/employees/{employee_id}")
def update_employee(employee_id: int, data: EmployeeRequest, user=Depends(admin_user)):
    try:
        employee = db_query(
            """
            UPDATE employees
            SET name = %s, email = %s, department = %s
            WHERE id = %s
            RETURNING id, name, email, department
            """,
            (data.name.strip(), data.email.lower(), data.department.strip(), employee_id),
            fetch_one=True,
        )
    except IntegrityError as exc:
        raise HTTPException(status_code=400, detail="Employee email already exists") from exc
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    return employee


@app.delete("/employees/{employee_id}")
def delete_employee(employee_id: int, user=Depends(admin_user)):
    active_assignment = db_query(
        "SELECT id FROM assignments WHERE employee_id = %s AND returned_date IS NULL",
        (employee_id,),
        fetch_one=True,
    )
    if active_assignment:
        raise HTTPException(status_code=400, detail="Employee has an active asset assignment")

    employee = db_query("DELETE FROM employees WHERE id = %s RETURNING id", (employee_id,), fetch_one=True)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    return {"message": "Employee deleted"}


@app.get("/assets")
def get_assets(search: str = "", user=Depends(current_user)):
    term = f"%{search.strip()}%"
    return db_query(
        """
        SELECT id, asset_name, asset_type, serial_number, status
        FROM assets
        WHERE %s = ''
           OR asset_name ILIKE %s
           OR asset_type ILIKE %s
           OR serial_number ILIKE %s
           OR status ILIKE %s
        ORDER BY id
        """,
        (search.strip(), term, term, term, term),
        fetch_all=True,
    )


@app.post("/assets", status_code=201)
def create_asset(data: AssetRequest, user=Depends(admin_user)):
    asset = clean_asset(data)
    try:
        return db_query(
            """
            INSERT INTO assets (asset_name, asset_type, serial_number, status)
            VALUES (%s, %s, %s, %s)
            RETURNING id, asset_name, asset_type, serial_number, status
            """,
            (
                asset["asset_name"].strip(),
                asset["asset_type"].strip(),
                asset["serial_number"].strip(),
                asset["status"],
            ),
            fetch_one=True,
        )
    except IntegrityError as exc:
        raise HTTPException(status_code=400, detail="Asset serial number already exists") from exc


@app.put("/assets/{asset_id}")
def update_asset(asset_id: int, data: AssetRequest, user=Depends(admin_user)):
    asset = clean_asset(data)
    active_assignment = db_query(
        "SELECT id FROM assignments WHERE asset_id = %s AND returned_date IS NULL",
        (asset_id,),
        fetch_one=True,
    )
    if active_assignment and asset["status"] != "Assigned":
        raise HTTPException(status_code=400, detail="Assigned assets must be returned before changing status")

    try:
        updated = db_query(
            """
            UPDATE assets
            SET asset_name = %s, asset_type = %s, serial_number = %s, status = %s
            WHERE id = %s
            RETURNING id, asset_name, asset_type, serial_number, status
            """,
            (
                asset["asset_name"].strip(),
                asset["asset_type"].strip(),
                asset["serial_number"].strip(),
                asset["status"],
                asset_id,
            ),
            fetch_one=True,
        )
    except IntegrityError as exc:
        raise HTTPException(status_code=400, detail="Asset serial number already exists") from exc
    if not updated:
        raise HTTPException(status_code=404, detail="Asset not found")
    return updated


@app.delete("/assets/{asset_id}")
def delete_asset(asset_id: int, user=Depends(admin_user)):
    active_assignment = db_query(
        "SELECT id FROM assignments WHERE asset_id = %s AND returned_date IS NULL",
        (asset_id,),
        fetch_one=True,
    )
    if active_assignment:
        raise HTTPException(status_code=400, detail="Asset has an active assignment")

    asset = db_query("DELETE FROM assets WHERE id = %s RETURNING id", (asset_id,), fetch_one=True)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return {"message": "Asset deleted"}


@app.get("/assignments")
def get_assignments(user=Depends(current_user)):
    return db_query(
        """
        SELECT
            ass.id,
            ass.employee_id,
            ass.asset_id,
            e.name AS employee_name,
            a.asset_name,
            a.serial_number,
            ass.assigned_date,
            ass.returned_date
        FROM assignments ass
        JOIN employees e ON ass.employee_id = e.id
        JOIN assets a ON ass.asset_id = a.id
        ORDER BY ass.id DESC
        """,
        fetch_all=True,
    )


@app.post("/assignments", status_code=201)
def create_assignment(data: AssignmentRequest, user=Depends(admin_user)):
    employee = db_query("SELECT id FROM employees WHERE id = %s", (data.employee_id,), fetch_one=True)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    asset = db_query("SELECT id, status FROM assets WHERE id = %s", (data.asset_id,), fetch_one=True)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    if asset["status"] != "Available":
        raise HTTPException(status_code=400, detail=f"Asset is {asset['status']} and cannot be assigned")

    assignment = db_query(
        """
        INSERT INTO assignments (employee_id, asset_id, assigned_date)
        VALUES (%s, %s, CURRENT_DATE)
        RETURNING id, employee_id, asset_id, assigned_date, returned_date
        """,
        (data.employee_id, data.asset_id),
        fetch_one=True,
    )
    db_query("UPDATE assets SET status = 'Assigned' WHERE id = %s", (data.asset_id,))
    return assignment


@app.put("/assignments/{assignment_id}/return")
def return_assignment(assignment_id: int, user=Depends(admin_user)):
    assignment = db_query(
        """
        UPDATE assignments
        SET returned_date = CURRENT_DATE
        WHERE id = %s AND returned_date IS NULL
        RETURNING id, asset_id, returned_date
        """,
        (assignment_id,),
        fetch_one=True,
    )
    if not assignment:
        raise HTTPException(status_code=404, detail="Active assignment not found")

    db_query("UPDATE assets SET status = 'Available' WHERE id = %s", (assignment["asset_id"],))
    return {"message": "Asset returned", "returned_date": assignment["returned_date"]}

# Asset Management System

## 1. Project Overview

Asset Management System is a simple full-stack internal portal for tracking company employees, assets, and asset assignments.

The project uses:

- Backend: Python, FastAPI, PostgreSQL, psycopg2, bcrypt
- Frontend: HTML, Tailwind CSS CDN, Vanilla JavaScript
- Authentication: bcrypt password hashes and a signed bearer token stored in browser localStorage

The code is intentionally kept small and beginner-friendly so an internship or entry-level candidate can understand the full request flow.

## 2. Features

- Admin and User login
- Password hashing with bcrypt
- Role-based API protection
- Dashboard cards for employee and asset totals
- Recent assignments table
- Employee CRUD with search and unique email validation
- Asset CRUD with search, unique serial validation, and status badges
- Asset assignment and return flow
- Assignment history using SQL joins
- Protected frontend pages
- Success messages, error messages, empty states, and confirmation dialogs

## 3. Folder Structure

```text
asset_manager/
├── backend/
│   ├── app.py
│   ├── requirements.txt
│   └── database/
│       └── db.py
├── database/
│   └── schema.sql
├── frontend/
│   ├── login.html
│   ├── dashboard.html
│   ├── employees.html
│   ├── assets.html
│   ├── assignments.html
│   ├── profile.html
│   └── js/
│       ├── common.js
│       ├── login.js
│       ├── dashboard.js
│       ├── employees.js
│       ├── assets.js
│       ├── assignments.js
│       └── profile.js
├── README.md
└── STUDY_GUIDE.md
```

## 4. Database Schema

Main tables:

- `users`: login accounts with `username`, `password_hash`, and `role`
- `employees`: employee name, email, and department
- `assets`: asset name, type, serial number, and status
- `assignments`: links an employee to an asset with assigned and returned dates

Important rules:

- Employee email is unique.
- Asset serial number is unique.
- Asset status must be `Available`, `Assigned`, `Maintenance`, or `Retired`.
- Assignments use foreign keys to employees and assets.

The SQL file is available at `database/schema.sql`. The FastAPI app also creates or repairs the required tables during startup.

## 5. API Endpoints

Authentication:

- `POST /login`
- `GET /me`

Dashboard:

- `GET /dashboard`

Employees:

- `GET /employees?search=`
- `POST /employees`
- `PUT /employees/{employee_id}`
- `DELETE /employees/{employee_id}`

Assets:

- `GET /assets?search=`
- `POST /assets`
- `PUT /assets/{asset_id}`
- `DELETE /assets/{asset_id}`

Assignments:

- `GET /assignments`
- `POST /assignments`
- `PUT /assignments/{assignment_id}/return`

## 6. Authentication Flow

1. User submits username and password from `login.html`.
2. Backend finds the user by username.
3. Backend verifies the submitted password against `password_hash` using bcrypt.
4. Backend returns a signed bearer token, username, and role.
5. Frontend stores those values in localStorage.
6. Later API calls send the token in the `Authorization` header.

Default users:

- Admin: `admin` / `admin123`
- User: `user` / `user123`

## 7. Authorization Flow

- Any logged-in user can view dashboard, employees, assets, assignments, and profile.
- Only Admin can create, update, delete, assign, and return assets.
- The backend enforces role checks with `current_user` and `admin_user` dependencies.
- The frontend also hides Admin-only forms and buttons for User accounts.

## 8. CRUD Operations

Employees:

- Create employees with name, email, and department.
- Edit employee details.
- Delete employees if they do not have an active assignment.
- Search by name, email, or department.

Assets:

- Create assets with name, type, serial number, and status.
- Edit asset details.
- Delete assets if they do not have an active assignment.
- Search by name, type, serial number, or status.

Assignments:

- Assign only `Available` assets.
- Assigned assets become `Assigned`.
- Returned assets become `Available`.
- Assignment history stays in the database.


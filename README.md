# Client Management System

## Introduction

### Executive Summary

The Client Management System (CMS) is a web-based business automation solution designed to manage client profiles, transactions, payments, and invoices. It offers a secure authentication mechanism and a real-time dashboard to streamline operational workflows.

### Purpose

The system centralizes client and financial data while reducing manual workload, increasing transparency, and improving business efficiency.

### Target Audience
- Small to medium businesses
- Agencies
- Freelancers
- Service-based companies

### Scope
- Core workflow includes:
- Client CRUD
- Transaction entry
- Payment logs
- Invoice generation
- Search & filtering
- Analytics dashboard

---

## TECHNOLOGY STACK

- Backend
    - FastAPI (Python)
    - Motor (async MongoDB driver)
    - Jinja2 (templating)

- Frontend
    - HTML
    - TailwindCSS
    - Vanilla JavaScript

- Database
    - MongoDB Atlas (Cloud managed NoSQL)

## File Structure

```bash
ClientManagement/
├── .gitignore
├── requirements.txt
├── main.py                    # FastAPI app & auth setup
├── database.py                # MongoDB (pymongo) connection
├── models.py                  # Pydantic models (Client, User, Transaction)
├── security.py                # Password hashing, JWT, login logic
├── routers/
│   ├── auth.py                # login/logout
│   ├── clients.py             # CRUD: /add, /view, /pending, /completed
│   └── transactions.py        # /transaction (update payment)
├── templates/
│   ├── base.html              # Layout with sidebar & your color palette
│   ├── login.html
│   ├── admin.html             # Dashboard (matches your image)
│   ├── add_client.html
│   ├── view_clients.html
│   ├── pending.html
│   ├── completed.html
│   └── transaction.html
└── static/
    └── style.css              # Tailwind via CDN + custom overrides (fonts, colors)
```

Author:: Tushar Shihab <br>
Machine Learning Engineer
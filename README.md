# Client Management System

---

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
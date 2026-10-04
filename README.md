# Development of a Shared-Infrastructure SaaS Framework with Row-Level Security and Rate Limiting for Retail SMEs

**Final Year Project (FYP)**  
**Candidate:** Hassan Saidu  
**Matriculation Number:** CSC/22U/4159  
**Repository:** [https://github.com/hassan3xl/fyb](https://github.com/hassan3xl/fyb)

---

## 📌 Project Overview

This project presents the development of an **Application-Layer Multi-Tenant Resource Isolation Framework** built on a shared cloud infrastructure, specifically engineered to support **Retail Small and Medium Enterprises (SMEs)**. 

Retail SMEs often face prohibitive costs when deploying enterprise resource planning (ERP) or multi-branch retail management software. Single-tenant architectures require dedicated database instances and computing servers for each business, leading to inflated operational expenditure. Conversely, traditional shared-infrastructure setups introduce significant data security risks (cross-tenant leakage) and performance vulnerabilities (noisy neighbors monopolizing system resources).

This framework resolves both challenges by implementing:
1. **Shared-Infrastructure SaaS Multi-Tenancy**: Pooled database and application compute resources with dynamic tenant routing (`/<tenant_slug>/`) and cryptographic tenant session binding.
2. **Row-Level Security (RLS)**: Enforced database data scoping and query-layer isolation to prevent unauthorized cross-tenant data access.
3. **Sliding-Window Rate Limiting**: Distributed cache-based sliding-window rate throttling (Standard: 100 req/min, Premium: 300 req/min) to mitigate noisy-neighbor degradation and DoS vulnerabilities.
4. **Adaptive Retail SME Suite**: Tailored business schemas and POS workflows for:
   - 💊 **Pharmacies & Drug Stores**: Batch number tracking, expiration date monitoring, and prescription dispensing.
   - 🛒 **Provision & Grocery Stores**: Fast barcode/retail checkout and automated reorder-threshold alerts.
   - 🏬 **Supermarkets**: Multi-cashier POS, category hierarchies, and high-volume transaction processing.
   - 💻 **Electronics & Tech Shops**: Serial number tracking, hardware model indexing, and exchange/return warranties.

---

## 🏗️ Architecture & Technical Pillars

```
+-----------------------------------------------------------------------------------+
|                           Client Request / Retail POS                             |
+-----------------------------------------------------------------------------------+
                                         │
                                         ▼
+───────────────────────────────────────────────────────────────────────────────────+
|                               ThrottleMiddleware                                  |
|            Sliding-Window Rate Limiter (Standard: 100/min, Premium: 300/min)      |
+───────────────────────────────────────────────────────────────────────────────────+
                                         │
                                         ▼
+───────────────────────────────────────────────────────────────────────────────────+
|                                TenantMiddleware                                   |
|            Tenant Slug Resolution & Session-Context Cryptographic Binding         |
+───────────────────────────────────────────────────────────────────────────────────+
                                         │
                                         ▼
+───────────────────────────────────────────────────────────────────────────────────+
|                         Row-Level Security (RLS) Layer                            |
|             Automated Tenant-Scoped Querysets (tenant_id = request.tenant_id)     |
+───────────────────────────────────────────────────────────────────────────────────+
                                         │
                                         ▼
+───────────────────────────────────────────────────────────────────────────────────+
|                       Shared PostgreSQL Database (Neon DB)                        |
|       Categories  •  Products  •  Sales  •  SaleItems  •  ReturnTransactions      |
+───────────────────────────────────────────────────────────────────────────────────+
```

### 1. Row-Level Security (RLS)
Every database entity (`Category`, `Product`, `Sale`, `SaleItem`, `ReturnTransaction`) is partitioned logically by `tenant_id`. Custom querysets and view decorators automatically inject tenant boundaries, guaranteeing that even on shared tables, one store cannot query or mutate records belonging to another tenant.

### 2. Sliding-Window Rate Limiting
Implemented in `middleware/throttle_middleware.py`. Rather than basic fixed-window counters that suffer from burst boundary vulnerabilities, the sliding-window algorithm calculates exact request density over moving 60-second intervals. When a tenant exceeds their plan threshold:
- HTTP 429 status code is returned.
- A user-friendly modal displays the exact retry countdown timer (`Retry in X seconds`).

### 3. Retail Returns & Exchanges Workflow
Allows retail cashiers to process partial or full item returns, refund transactions, and issue direct product exchanges while maintaining accurate inventory quantities and audit trails.

---

## 🚀 Getting Started

### Prerequisites
- Python 3.12+
- PostgreSQL or SQLite
- `uv` (recommended) or `pip`

### Installation
```bash
# Clone the repository
git clone https://github.com/hassan3xl/fyb.git
cd multi-tenant

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Environment Configuration
Configure your `.env` or development settings (`src/settings/dev.py`):
```env
SECRET_KEY=your-django-secret-key
DEBUG=True
DATABASE_URL=postgres://user:password@host/neondb
```

### Database Migration
```bash
python manage.py migrate
```

### Run Development Server
```bash
python manage.py runserver
```
Visit `http://localhost:8000/` to explore the framework home page, register a retail SME store, or sign in to an existing workspace.

---

## 🧪 Testing

Run the automated test suite verifying isolation policies, rate throttling, and return workflows:
```bash
python manage.py test --keepdb
```

---

## 👨‍💻 Project Details
- **Student Name:** Hassan Saidu
- **Matriculation No:** CSC/22U/4159
- **Project Topic:** Development of a Shared-Infrastructure SaaS Framework with Row-Level Security and Rate Limiting for Retail SMEs

📄 PharmaDocs AI

Your AI-powered Pharma Document Platform — Built with Flask, HTML, and Bootstrap.
PharmaDocs AI is designed to streamline pharmaceutical document generation and management, making it easy for healthcare professionals and researchers to access, upload, and process documents securely.

🚀 Features

* Secure Authentication – Firebase-based login and registration.

* Document Upload & Management – Upload documents to Cloudinary storage.

* AI-Powered Processing – Backend ready for integration with NLP/ML models.

* Responsive UI – Bootstrap 4 ensures mobile-friendly design.

* Cloud Native – Deployed using Google Cloud Run with environment-based configuration.


## Tech Stack

| Layer       | Technology         | Reason                                                                                   |
|-------------|--------------------|------------------------------------------------------------------------------------------|
| Backend     | Flask              | Lightweight Python microframework — perfect for quick API + template rendering, easy integration with Firebase and Cloudinary |
| Frontend    | HTML5 + Bootstrap 5| Provides responsive, clean UI with minimal CSS overhead                                  |
| Auth        | Firebase Auth      | Secure, battle-tested authentication with easy client/backend integration               |
| Storage     | Cloudinary         | Fast, CDN-backed image hosting for user uploads                                          |
| Deployment  | Google Cloud Run   | Fully managed, serverless container platform with HTTPS and scalability                  |
| Environment | `.env` variables   | Keep sensitive keys/config out of code                                                   |
| Management | [Astral UV](https://github.com/astral-sh/uv) | Keeps it easy to manage python dependencies |

## Project Structure

```
PharmaDocs AI/
├── app_routes # contains the flask routes/endpoints
├── services # contains various services like document uploading, authentication
├── static # required css and js files or images
├── templates # the main website templates written in HTML
├── utils # helper functions and validators for activity login, creds etc
├── app.py # main entry point
├── Dockerfile
├── main.py
├── models.py
├── Procfile
├── pyproject.toml
├── README.md
├── requirements.txt
└── uv.lock
```

## Local Development

```bash
# Clone repository
git clone https://github.com/<your-username>/pharmadocsai.git
cd pharmadocsai
```

Manage deps manually

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run locally
flask run --reload
```

or using uv

```bash

# Create virtual environment
uv -p python3.11

# Install dependencies
uv pip install -r requirements.txt

# Run locally
uv run flask run --reload
```

## Deployment

The complete deployment is done using Google Cloud. Check out docs to deploy it in GCloud for your own use.

## License

Copyright (c) 2025 Soumyadeep Ghosh <soumyadeepghosh2004@zohomail.in>
All Rights Reserved.

This project is proprietary software.
No part of this codebase may be copied, modified, distributed, deployed, or used in any form
without prior written permission from the copyright holder.

## Working

PharmaDocs AI is designed to streamline company and sub-brand profile management, along with generating associated documentation. The application currently focuses on:

- **Company Profile Management** — Create, view, and update company details.
- **Sub-Brand Management (Planned)** — Sub-brand creation is part of the roadmap but **not implemented yet**.
- **Document Generation (Planned)** — Exact profile-to-document generation pipeline is **not implemented yet**.

## Models

The system uses well-structured models to organize data:

1. **Company**
   - Stores the main company profile details such as name, registration info, address, and contact details.
   - Linked to multiple sub-brands (planned).

2. **SubBrand** *(Planned)*
   - Represents a specific brand/product line under the main company.
   - Will be linked to the parent `Company` model via a foreign key.

3. **Document** *(Planned)* *(Partially Implemented)*
   - Holds metadata for generated profile documents (PDF/HTML).
   - Will be linked to either a `Company` or a `SubBrand`.


## Database Schema

PharmaDocs AI uses an **SQL database** (SQLite for development) to persist data.
The key relationships are:

- **One-to-Many**:
  - A single `Company` can have many `SubBrands` (planned).
- **One-to-Many**:
  - A `Company` or `SubBrand` can have many `Documents` (planned).

Example Schema (Current + Planned):

| Table       | Fields                                                   | Relationships |
|-------------|----------------------------------------------------------|---------------|
| Company     | id, name, reg_number, address, contact_email, created_at  | —             |
| SubBrand    | id, company_id, name, description, created_at             | FK → Company  |
| Document    | id, owner_type, owner_id, file_path, created_at           | FK → Company/SubBrand |

## Data Storage

- **Current State**:
  - All data is stored in a relational **SQL database**.
  - SQLite is used during development for simplicity and zero setup.
- **Future Plans**:
  - Move to PostgreSQL/MySQL in production for scalability.
  - Add indexing and constraints for improved query performance.

## Roadmap

- ✅ Company profile creation and management.
- ⏳ Sub-brand creation and linking to companies.
- ⏳ Automated document generation (PDF, DOCX).
- ⏳ API endpoints for mobile and third-party integrations.


# PharmaDocs AI Platform

A Flask-based platform to generate Analytical Method Validation (AMV) reports using deterministic calculations and ICH Q2(R1) guidelines. Includes auto-extraction from PDFs, SMILES generation from active ingredient names, and chemical structure visualization.

## Features
- AMV report generation (no AI; pure calculations)
- Method parameter extraction from PDF
- SMILES generation via PubChem API from ingredient names
- Chemical structure rendering (RDKit)
- Company equipment/materials/reagents management
- Authentication and dashboard

## Tech Stack
- Python 3.11+
- Flask, SQLAlchemy, Flask-Migrate
- RDKit (structure), python-docx (report), PyPDF2/pdfplumber (PDF)
- Firebase Admin (auth optional), Cloudinary (optional uploads)

## Prerequisites
- Python 3.11+
- (Optional) RDKit may require system packages; on Windows, install via dkit-pypi already listed in requirements

## Setup
`ash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
`

Create required folders if missing:
`ash
mkdir uploads reports instance
`

## Run
`ash
# Development
set FLASK_APP=app.py
flask run

# Or via main
python app.py
`

## Environment
Create a .env if needed (Cloudinary, Firebase, etc.). The app runs without them for local testing.

## SMILES & Structure
- Enter active ingredient in AMV form and click "Generate SMILES"
- SMILES auto-fills plus molecular formula/weight
- Click "Generate Structure" to render and view properties

## Cleaning and Git
- .gitignore excludes venv, caches, local DBs, uploads/reports outputs
- Local SQLite DBs and generated files are not committed

## Deploy
- Uses Procfile and Dockerfile as references. Ensure env vars supplied in your environment.

## License
Proprietary. All rights reserved.

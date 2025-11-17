# Copyright (C) 2025 Soumyadeep Ghosh <soumyadeepghosh2004@zohomail.in>
# All Rights Reserved.

from app import app  # noqa: F401
from dotenv import load_dotenv
import os

load_dotenv()

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
    print("FIREBASE_API_KEY",os.environ.get('FIREBASE_API_KEY'))
    print("FIREBASE_PROJECT_ID",os.environ.get('FIREBASE_PROJECT_ID'))



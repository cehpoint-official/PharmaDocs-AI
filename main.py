# Copyright (C) 2025 Soumyadeep Ghosh <soumyadeepghosh2004@zohomail.in>
# All Rights Reserved.

from app import app  # noqa: F401
from dotenv import load_dotenv

load_dotenv()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

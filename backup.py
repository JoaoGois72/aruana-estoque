import os
from datetime import datetime
from app import create_app
from app.extensions import db

app = create_app()

with app.app_context():
    filename = f"backup_{datetime.now().strftime('%Y%m%d_%H%M')}.sql"
    os.system(f"pg_dump $DATABASE_URL > {filename}")
    print("Backup gerado:", filename)

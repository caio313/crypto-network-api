import psycopg2
import os

conn = psycopg2.connect(os.environ["DATABASE_URL"])
conn.autocommit = True
cur = conn.cursor()

cur.execute("DROP TYPE IF EXISTS tierenum;")

cur.execute("""
    CREATE TABLE IF NOT EXISTS alembic_version (
        version_num VARCHAR(32) NOT NULL,
        CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
    );
""")

print("DB limpia. Lista para migración.")
cur.close()
conn.close()

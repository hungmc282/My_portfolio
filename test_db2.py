import mysql.connector
import os
import uuid
from dotenv import load_dotenv

load_dotenv()
db_config = {
    'host': os.getenv('DB_HOST'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'database': os.getenv('DB_NAME'),
    'port': int(os.getenv('DB_PORT', 4000)),
    'ssl_verify_cert': False,
    'ssl_verify_identity': False
}
conn = mysql.connector.connect(**db_config)
cursor = conn.cursor(dictionary=True)
try:
    cursor.execute("UPDATE Users SET session_token = '123', failed_attempts = 0, locked_until= NULL WHERE username = 'admin'")
    conn.commit()
    print("Success")
except Exception as e:
    print("Error:", e)

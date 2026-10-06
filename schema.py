import mysql.connector
import os
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
cursor.execute("DESCRIBE Users")
for row in cursor.fetchall():
    print(row)

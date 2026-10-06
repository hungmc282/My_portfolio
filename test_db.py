import mysql.connector
import os
from dotenv import load_dotenv
from datetime import datetime

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
cursor.execute("SELECT NOW() as db_time")
db_time = cursor.fetchone()['db_time']
py_time = datetime.now()
print("DB time:", db_time)
print("PY time:", py_time)

import mysql.connector
import os
from werkzeug.security import generate_password_hash
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
cursor = conn.cursor()

try:
    # 1. Add role column if not exists
    cursor.execute("SHOW COLUMNS FROM Users LIKE 'role'")
    if not cursor.fetchone():
        cursor.execute("ALTER TABLE Users ADD COLUMN role VARCHAR(20) DEFAULT 'user'")
        print("Added 'role' column to Users.")

    # 2. Check if hungmc exists
    cursor.execute("SELECT id FROM Users WHERE username = 'hungmc'")
    user = cursor.fetchone()
    hashed_pw = generate_password_hash('123')
    
    if user:
        cursor.execute("UPDATE Users SET role = 'admin', password = %s WHERE username = 'hungmc'", (hashed_pw,))
        print("Updated hungmc to admin.")
    else:
        cursor.execute("INSERT INTO Users (username, password, role) VALUES ('hungmc', %s, 'admin')", (hashed_pw,))
        print("Created hungmc as admin.")
        
    # 3. Create Feedbacks table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Feedbacks (
        id INT AUTO_INCREMENT PRIMARY KEY,
        report_id INT NOT NULL,
        username VARCHAR(50) NOT NULL,
        content TEXT NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (report_id) REFERENCES Reports(id) ON DELETE CASCADE,
        FOREIGN KEY (username) REFERENCES Users(username) ON DELETE CASCADE
    )
    """)
    print("Created Feedbacks table.")
    
    conn.commit()
    print("Migration successful.")
except Exception as e:
    print("Error:", e)
finally:
    cursor.close()
    conn.close()

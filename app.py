import os
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, session
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
# Chìa khóa bí mật để mã hóa Session (Cookie ghi nhớ đăng nhập)
app.secret_key = os.getenv('SECRET_KEY', 'fallback-dev-secret-key') # Use a fallback secret key for development

db_config = {
    'host': os.getenv('DB_HOST'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'database': os.getenv('DB_NAME'),
    'port': int(os.getenv('DB_PORT', 8889))
}



# Hàm hỗ trợ kết nối nhanh Database
def get_db_connection():
    return mysql.connector.connect(**db_config)

# ------------------ TRANG CHỦ PUBLIC (CHO NHÀ TUYỂN DỤNG) ------------------
@app.route('/')
def home():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Lấy tất cả bài report để hiển thị ra trang chủ
    cursor.execute("SELECT * FROM Reports ORDER BY created_at DESC")
    public_reports = cursor.fetchall() 
    
    cursor.close()
    conn.close()
    
    # Truyền dữ liệu ra file index.html
    return render_template('index.html', reports=public_reports)

# ------------------ CHỨC NĂNG ĐĂNG KÝ ------------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Băm mật khẩu (Hash) trước khi lưu
        hashed_password = generate_password_hash(password)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            # Lưu vào bảng Users
            cursor.execute("INSERT INTO Users (username, password) VALUES (%s, %s)", (username, hashed_password))
            conn.commit()
            return redirect(url_for('login')) # Đăng ký xong tự động chuyển sang trang Login
        except:
            return "Lỗi: Tên đăng nhập này đã tồn tại!"
        finally:
            cursor.close()
            conn.close()
            
    # Nếu là GET (chỉ truy cập đường dẫn), hiển thị giao diện HTML
    return render_template('register.html')

# ------------------ CHỨC NĂNG ĐĂNG NHẬP ------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password_input = request.form['password']
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True) # Lấy dữ liệu dưới dạng Dictionary cho dễ đọc
        cursor.execute("SELECT * FROM Users WHERE username = %s", (username,))
        user = cursor.fetchone() # Lấy ra 1 người dùng khớp với username
        
        cursor.close()
        conn.close()
        
        # Kiểm tra xem user có tồn tại và mật khẩu nhập vào (đã check hash) có đúng không
        if user and check_password_hash(user['password'], password_input):
            # Lưu thông tin vào Session để ghi nhớ là đã đăng nhập
            session['loggedin'] = True
            session['username'] = user['username']
            return redirect(url_for('dashboard'))
        else:
            return "Sai tên đăng nhập hoặc mật khẩu!"
            
    return render_template('login.html')


# ------------------ TRANG QUẢN TRỊ (DASHBOARD) ------------------
@app.route('/dashboard')
def dashboard():
    if 'loggedin' in session:
        conn = get_db_connection()
        # Dùng dictionary=True để lấy dữ liệu dạng cột (như report['title'])
        cursor = conn.cursor(dictionary=True)
        
        # Lệnh SQL: Lấy tất cả bài viết, sắp xếp theo ngày tạo mới nhất (DESC)
        cursor.execute("SELECT * FROM Reports ORDER BY created_at DESC")
        reports_list = cursor.fetchall() 
        
        cursor.close()
        conn.close()
        
        # Truyền danh sách bài viết ra ngoài file HTML
        return render_template('dashboard.html', reports=reports_list)
        
    return redirect(url_for('login'))


# ------------------ THÊM REPORT MỚI ------------------
@app.route('/add_report', methods=['GET', 'POST'])
def add_report():
    # Chặn những người chưa đăng nhập
    if 'loggedin' not in session:
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        title = request.form['title']
        category = request.form['category']
        content = request.form['content']
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Chèn dữ liệu vào bảng Reports trong MySQL
        cursor.execute(
            "INSERT INTO Reports (title, category, content) VALUES (%s, %s, %s)", 
            (title, category, content)
        )
        conn.commit() # Xác nhận lưu
        
        cursor.close()
        conn.close()
        
        # Lưu xong thì tự động quay về trang Dashboard
        return redirect(url_for('dashboard'))
        
    return render_template('report.html')

# ------------------ ĐĂNG XUẤT ------------------
@app.route('/logout')
def logout():
    # Xóa dữ liệu Session
    session.pop('loggedin', None)
    session.pop('username', None)
    return redirect(url_for('login'))

# ------------------ XEM CHI TIẾT MỘT REPORT ------------------
# Đường dẫn có chứa <int:id> để nhận biết số ID của bài viết
@app.route('/report/<int:id>')
def view_report(id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Tìm duy nhất 1 bài viết có id khớp với đường dẫn
    cursor.execute("SELECT * FROM Reports WHERE id = %s", (id,))
    report = cursor.fetchone() 
    
    cursor.close()
    conn.close()
    
    # Nếu tìm thấy bài viết, chuyển dữ liệu ra trang chi tiết
    if report:
        return render_template('report_detail.html', report=report)
    else:
        return "Không tìm thấy bài viết này!", 404

if __name__ == '__main__':
    app.run(debug=os.getenv('FLASK_DEBUG', 'False').lower() == 'true')
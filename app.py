import os
import uuid
from datetime import datetime, timedelta # thêm dòng này để tính thời gian khoá
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, session
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
# Chìa khóa bí mật để mã hóa Session (Cookie ghi nhớ đăng nhập)
app.secret_key = os.getenv('SECRET_KEY', 'fallback-dev-secret-key') # Use a fallback secret key for development
# Cấu hình bảo mật cho Session Cookie
app.config['SESSION_COOKIE_HTTPONLY'] = True 
app.config['SESSION_COOKIE_SECURE'] = True    
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

db_config = {
    'host': os.getenv('DB_HOST'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'database': os.getenv('DB_NAME'),
    'port': int(os.getenv('DB_PORT', 4000)),
    'ssl_verify_cert': False,
    'ssl_verify_identity': False
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
    if session.get('loggedin'):
        return redirect(url_for('dashboard')) if session.get('role') == 'admin' else redirect(url_for('home'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if len(password) < 8:
            return "Mật khẩu phải có ít nhất 8 ký tự!"
        
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
    if session.get('loggedin'):
        return redirect(url_for('dashboard')) if session.get('role') == 'admin' else redirect(url_for('home'))

    if request.method == 'POST':
        username = request.form['username']
        password_input = request.form['password']
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True) # Lấy dữ liệu dưới dạng Dictionary cho dễ đọc
        cursor.execute("SELECT * FROM Users WHERE username = %s", (username,))
        user = cursor.fetchone() # Lấy ra 1 người dùng khớp với username
        if user:
            # Kiểm tra xem user có bị khoá hay không, nếu có thì thông báo thời gian còn lại
            if user.get('locked_until'):
                if user['locked_until'] > datetime.now():  
                    # Tính thời gian còn lại để thông báo cho người dùng 
                    remaining_time = user['locked_until'] - datetime.now()
                    minutes, seconds = divmod(remaining_time.total_seconds(), 60)

                    cursor.close()
                    conn.close()
                    return f"Tài khoản của bạn đang bị khoá. Vui lòng thử lại sau {int(minutes)} phút {int(seconds)} giây." 
                else:
                    # Nếu thời gian khoá đã qua, reset số lần nhập sai để tránh việc vừa nhập sai 1 lần đã bị khoá lại
                    user['failed_attempts'] = 0

            # Kiểm tra xem user có tồn tại và mật khẩu nhập vào (đã check hash) có đúng không
            if check_password_hash(user['password'], password_input):
                # Sinh ra mã token ngẫu nhiên
                new_token = str(uuid.uuid4())
                # Cập nhật token mới vào Database để lưu lại
                cursor.execute("UPDATE Users SET session_token = %s, failed_attempts = 0, locked_until= NULL WHERE username = %s", (new_token, username))
                conn.commit()

                # Lưu thông tin vào Session để ghi nhớ là đã đăng nhập
                session['loggedin'] = True
                session['username'] = username
                session['session_token'] = new_token
                session['role'] = user.get('role', 'user')

                #Đóng kết nối Database
                cursor.close()
                conn.close()

                if session['role'] == 'admin':
                    return redirect(url_for('dashboard')) #Chuyển sang giao diện Dashboard khi đăng nhập thành công
                else:
                    return redirect(url_for('home')) # User thường thì về trang chủ để xem bài và comment
            # Nếu mật khẩu sai, tăng số lần nhập sai và kiểm tra xem có cần khoá tài khoản không
            else:
                # Tăng số lần nhập sai lên 1
                fail_attempts = (user.get('failed_attempts') or 0) + 1
                # Nếu số lần nhập sai >= 5, khoá tài khoản trong 1 tiếng
                if fail_attempts >= 5:
                    lock_time = datetime.now() + timedelta(hours=1)
                    cursor.execute("UPDATE Users SET failed_attempts = %s, locked_until = %s WHERE username = %s", (fail_attempts, lock_time, username))
                    conn.commit()
                    cursor.close()
                    conn.close()
                    return "Bạn đã nhập sai 5 lần! Tài khoản của bạn đã bị khoá trong 1 tiếng."
                else:
                    cursor.execute("UPDATE Users SET failed_attempts = %s WHERE username = %s", (fail_attempts, username))
                    conn.commit()
                    cursor.close()
                    conn.close()
                    return f"Sai mật khẩu! Bạn đã nhập sai {fail_attempts} lần."
        else:
            cursor.close()
            conn.close()
            return "Tên đăng nhập không tồn tại!"
    
    return render_template('login.html')


# ------------------ TRANG QUẢN TRỊ (DASHBOARD) ------------------
@app.route('/dashboard')
def dashboard():
    if 'loggedin' in session and 'session_token' in session and session.get('role') == 'admin':
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
       # Soi cuốn sổ Database xem có token nào làm trùng với token trong Session không, nếu có thì mới cho vào Dashboard
        cursor.execute("SELECT session_token FROM Users WHERE username = %s", (session['username'],))
        user_db = cursor.fetchone()

        if user_db and user_db['session_token'] == session['session_token']:
            # Mọi thông tin hợp lệ, lấy danh sách report để hiển thị ra Dashboard
            cursor.execute("SELECT * FROM Reports ORDER BY created_at DESC")
            report_list = cursor.fetchall()

            #Đóng kết nối database
            cursor.close()
            conn.close()

            return render_template('dashboard.html', reports=report_list)
        else:
            # Nếu token trong Session không khớp với token trong Database, xóa Session và chuyển về trang Login
            session.clear()
            cursor.close()
            conn.close()
            return redirect(url_for('login'))
          
    return redirect(url_for('login'))


# ------------------ THÊM REPORT MỚI ------------------
@app.route('/add_report', methods=['GET', 'POST'])
def add_report():
    # Chặn những người chưa đăng nhập hoặc không phải admin
    if 'loggedin' not in session or 'session_token' not in session or session.get('role') != 'admin':
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
    if 'username' in session:
        conn = get_db_connection()
        cursor = conn.cursor()
        # Xóa token trong DB thành chuỗi rỗng
        cursor.execute("UPDATE Users SET session_token = NULL WHERE username = %s", (session['username'],))
        conn.commit()
        cursor.close()
        conn.close()

    # Xóa Cookie ở trình duyệt
    session.clear()
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
    
    # Lấy danh sách feedback
    cursor.execute("SELECT * FROM Feedbacks WHERE report_id = %s ORDER BY created_at DESC", (id,))
    feedbacks = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    # Nếu tìm thấy bài viết, chuyển dữ liệu ra trang chi tiết
    if report:
        return render_template('report_detail.html', report=report, feedbacks=feedbacks)
    else:
        return "Không tìm thấy bài viết này!", 404

# ------------------ THÊM BÌNH LUẬN ------------------
@app.route('/report/<int:id>/comment', methods=['POST'])
def add_comment(id):
    if 'loggedin' not in session:
        return redirect(url_for('login'))
        
    content = request.form['content']
    username = session['username']
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO Feedbacks (report_id, username, content) VALUES (%s, %s, %s)",
        (id, username, content)
    )
    conn.commit()
    cursor.close()
    conn.close()
    
    return redirect(url_for('view_report', id=id))

if __name__ == '__main__':
    app.run(debug=os.getenv('FLASK_DEBUG', 'False').lower() == 'true')
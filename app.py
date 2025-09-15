from flask import Flask, redirect, url_for, session, request, render_template, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
from authlib.integrations.flask_client import OAuth
import random
import json
from datetime import datetime
from flask import escape

app = Flask(__name__)
app.secret_key = os.urandom(24).hex()
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///schedule.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
oauth = OAuth(app)

# Google OAuth 配置
google = oauth.register(
    name='google',
    client_id='YOUR_GOOGLE_CLIENT_ID',  # 從 Google Cloud Console 獲取
    client_secret='YOUR_GOOGLE_CLIENT_SECRET',  # 從 Google Cloud Console 獲取
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

# 資料庫模型
class User(db.Model):
    id = db.Column(db.String(120), primary_key=True)
    email = db.Column(db.String(120), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    language = db.Column(db.String(10), default='zh-TW')

class Schedule(db.Model):
    id = db.Column(db.String(10), primary_key=True)  # 改為 10 位數 ID
    name = db.Column(db.String(100), nullable=False)
    owner_id = db.Column(db.String(120), db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    shift_types = db.Column(db.String(500), default='["早班","晚班","夜班"]')

class Shift(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    schedule_id = db.Column(db.String(10), db.ForeignKey('schedule.id'), nullable=False)
    user_id = db.Column(db.String(120), db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.String(10), nullable=False)
    shift = db.Column(db.String(50), nullable=False)
    reminder = db.Column(db.Boolean, default=False)

class Collaborator(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    schedule_id = db.Column(db.String(10), db.ForeignKey('schedule.id'), nullable=False)
    user_id = db.Column(db.String(120), db.ForeignKey('user.id'), nullable=False)

class History(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    schedule_id = db.Column(db.String(10), db.ForeignKey('schedule.id'), nullable=False)
    user_id = db.Column(db.String(120), db.ForeignKey('user.id'), nullable=False)
    action = db.Column(db.String(100), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# 生成 10 位數唯一 ID
def generate_schedule_id():
    while True:
        schedule_id = ''.join([str(random.randint(0, 9)) for _ in range(10)])
        if not Schedule.query.get(schedule_id):
            return schedule_id

# 首頁
@app.route('/')
def index():
    user = session.get('user')
    if not user:
        return render_template('login.html')
    schedules = Schedule.query.filter_by(owner_id=user['sub']).all()
    collaborated = Collaborator.query.filter_by(user_id=user['sub']).all()
    new_schedule_id = generate_schedule_id()  # 預生成 ID 供表單顯示
    return render_template('index.html', user=user, schedules=schedules, collaborated=collaborated, new_schedule_id=new_schedule_id)

# Google 登入
@app.route('/login')
def login():
    redirect_uri = url_for('authorize', _external=True)
    return google.authorize_redirect(redirect_uri)

# 授權回調
@app.route('/authorize')
def authorize():
    token = google.authorize_access_token()
    user = google.parse_id_token(token)
    session['user'] = user
    existing_user = User.query.get(user['sub'])
    if not existing_user:
        new_user = User(id=user['sub'], email=user['email'], name=user['name'])
        db.session.add(new_user)
        db.session.commit()
    return redirect(url_for('index'))

# 登出
@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('index'))

# 創建班表
@app.route('/create_schedule', methods=['POST'])
def create_schedule():
    user = session.get('user')
    if not user:
        return redirect(url_for('login'))
    name = escape(request.form['name'])
    schedule_id = escape(request.form['schedule_id'])  # 使用預生成的 ID
    if not name:
        flash('班表名稱不能為空！', 'danger')
        return redirect(url_for('index'))
    if Schedule.query.get(schedule_id):
        flash('班表 ID 已存在，請重新生成！', 'danger')
        return redirect(url_for('index'))
    new_schedule = Schedule(id=schedule_id, name=name, owner_id=user['sub'])
    db.session.add(new_schedule)
    db.session.commit()
    History(schedule_id=schedule_id, user_id=user['sub'], action=f"創建班表: {name}").add_to_db()
    flash('班表創建成功！', 'success')
    return redirect(url_for('index'))

# 加入班表
@app.route('/join_schedule', methods=['POST'])
def join_schedule():
    user = session.get('user')
    if not user:
        return redirect(url_for('login'))
    schedule_id = escape(request.form['schedule_id'])
    schedule = Schedule.query.get(schedule_id)
    if not schedule:
        flash('無效的班表 ID！', 'danger')
        return redirect(url_for('index'))
    if schedule.owner_id == user['sub']:
        flash('您已是此班表的擁有者！', 'warning')
        return redirect(url_for('index'))
    if Collaborator.query.filter_by(schedule_id=schedule_id).count() >= 5:
        flash('免費版限制：最多 5 名協作者！請升級高級版。', 'warning')
        return redirect(url_for('index'))
    existing = Collaborator.query.filter_by(schedule_id=schedule_id, user_id=user['sub']).first()
    if not existing:
        new_collaborator = Collaborator(schedule_id=schedule_id, user_id=user['sub'])
        db.session.add(new_collaborator)
        db.session.commit()
        History(schedule_id=schedule_id, user_id=user['sub'], action="加入班表").add_to_db()
        flash('成功加入班表！', 'success')
    return redirect(url_for('index'))

# 查看班表
@app.route('/schedule/<schedule_id>')
def view_schedule(schedule_id):
    user = session.get('user')
    if not user:
        return redirect(url_for('login'))
    schedule = Schedule.query.get_or_404(schedule_id)
    is_owner = schedule.owner_id == user['sub']
    is_collaborator = Collaborator.query.filter_by(schedule_id=schedule_id, user_id=user['sub']).first() is not None
    if not (is_owner or is_collaborator):
        flash('您無權訪問此班表！', 'danger')
        return redirect(url_for('index'))
    shifts = Shift.query.filter_by(schedule_id=schedule_id).all()
    collaborators = Collaborator.query.filter_by(schedule_id=schedule_id).all()
    history = History.query.filter_by(schedule_id=schedule_id).order_by(History.timestamp.desc()).all()
    shift_types = json.loads(schedule.shift_types)
    return render_template('schedule.html', schedule=schedule, shifts=shifts, is_owner=is_owner, user=user, 
                         collaborators=collaborators, history=history, shift_types=shift_types)

# 新增班次
@app.route('/add_shift/<schedule_id>', methods=['POST'])
def add_shift(schedule_id):
    user = session.get('user')
    if not user:
        return redirect(url_for('login'))
    schedule = Schedule.query.get_or_404(schedule_id)
    is_owner = schedule.owner_id == user['sub']
    is_collaborator = Collaborator.query.filter_by(schedule_id=schedule_id, user_id=user['sub']).first() is not None
    if not (is_owner or is_collaborator):
        return redirect(url_for('index'))
    date = escape(request.form['date'])
    shift = escape(request.form['shift'])
    reminder = 'reminder' in request.form
    shift_types = json.loads(schedule.shift_types)
    if shift not in shift_types and not is_owner:
        flash('無效的班次類型！請選擇預定義的班次。', 'danger')
        return redirect(url_for('view_schedule', schedule_id=schedule_id))
    try:
        shift_date = datetime.strptime(date, '%Y-%m-%d')
        if not (datetime(2025, 1, 1) <= shift_date <= datetime(2099, 12, 31)):
            flash('班次日期必須在 2025-01-01 至 2099-12-31 之間！', 'danger')
            return redirect(url_for('view_schedule', schedule_id=schedule_id))
    except ValueError:
        flash('無效的日期格式！', 'danger')
        return redirect(url_for('view_schedule', schedule_id=schedule_id))
    new_shift = Shift(schedule_id=schedule_id, user_id=user['sub'], date=date, shift=shift, reminder=reminder)
    db.session.add(new_shift)
    db.session.commit()
    History(schedule_id=schedule_id, user_id=user['sub'], action=f"新增班次: {date} {shift}").add_to_db()
    flash('班次新增成功！', 'success')
    return redirect(url_for('view_schedule', schedule_id=schedule_id))

# 刪除班次
@app.route('/delete_shift/<schedule_id>/<int:shift_id>')
def delete_shift(schedule_id, shift_id):
    user = session.get('user')
    if not user:
        return redirect(url_for('login'))
    schedule = Schedule.query.get_or_404(schedule_id)
    shift = Shift.query.get_or_404(shift_id)
    is_owner = schedule.owner_id == user['sub']
    is_collaborator = Collaborator.query.filter_by(schedule_id=schedule_id, user_id=user['sub']).first() is not None
    if not (is_owner or (is_collaborator and shift.user_id == user['sub'])):
        flash('您無權刪除此班次！', 'danger')
        return redirect(url_for('view_schedule', schedule_id=schedule_id))
    db.session.delete(shift)
    db.session.commit()
    History(schedule_id=schedule_id, user_id=user['sub'], action=f"刪除班次: {shift.date} {shift.shift}").add_to_db()
    flash('班次刪除成功！', 'success')
    return redirect(url_for('view_schedule', schedule_id=schedule_id))

# 移除協作者
@app.route('/remove_collaborator/<schedule_id>/<user_id>')
def remove_collaborator(schedule_id, user_id):
    user = session.get('user')
    if not user:
        return redirect(url_for('login'))
    schedule = Schedule.query.get_or_404(schedule_id)
    if schedule.owner_id != user['sub']:
        flash('僅班表擁有者可移除協作者！', 'danger')
        return redirect(url_for('view_schedule', schedule_id=schedule_id))
    collaborator = Collaborator.query.filter_by(schedule_id=schedule_id, user_id=user_id).first()
    if collaborator:
        db.session.delete(collaborator)
        db.session.commit()
        History(schedule_id=schedule_id, user_id=user['sub'], action=f"移除協作者: {collaborator.user.name}").add_to_db()
        flash('協作者移除成功！', 'success')
    return redirect(url_for('view_schedule', schedule_id=schedule_id))

# 刪除班表
@app.route('/delete_schedule/<schedule_id>')
def delete_schedule(schedule_id):
    user = session.get('user')
    if not user:
        return redirect(url_for('login'))
    schedule = Schedule.query.get_or_404(schedule_id)
    if schedule.owner_id != user['sub']:
        flash('僅班表擁有者可刪除班表！', 'danger')
        return redirect(url_for('index'))
    Shift.query.filter_by(schedule_id=schedule_id).delete()
    Collaborator.query.filter_by(schedule_id=schedule_id).delete()
    History.query.filter_by(schedule_id=schedule_id).delete()
    db.session.delete(schedule)
    db.session.commit()
    flash('班表刪除成功！', 'success')
    return redirect(url_for('index'))

# 匯出班表
@app.route('/export_schedule/<schedule_id>')
def export_schedule(schedule_id):
    user = session.get('user')
    if not user:
        return redirect(url_for('login'))
    schedule = Schedule.query.get_or_404(schedule_id)
    if schedule.owner_id != user['sub']:
        flash('僅班表擁有者可匯出班表！', 'danger')
        return redirect(url_for('view_schedule', schedule_id=schedule_id))
    shifts = Shift.query.filter_by(schedule_id=schedule_id).all()
    data = {
        'schedule_id': schedule.id,
        'name': schedule.name,
        'owner': schedule.owner.name,
        'shifts': [{'user': s.user.name, 'date': s.date, 'shift': s.shift, 'reminder': s.reminder} for s in shifts]
    }
    return jsonify(data)

# 更新班次類型
@app.route('/update_shift_types/<schedule_id>', methods=['POST'])
def update_shift_types(schedule_id):
    user = session.get('user')
    if not user:
        return redirect(url_for('login'))
    schedule = Schedule.query.get_or_404(schedule_id)
    if schedule.owner_id != user['sub']:
        flash('僅班表擁有者可更新班次類型！', 'danger')
        return redirect(url_for('view_schedule', schedule_id=schedule_id))
    shift_types = request.form.getlist('shift_types')
    if not shift_types:
        flash('班次類型不能為空！', 'danger')
        return redirect(url_for('view_schedule', schedule_id=schedule_id))
    schedule.shift_types = json.dumps(shift_types)
    db.session.commit()
    History(schedule_id=schedule_id, user_id=user['sub'], action="更新班次類型").add_to_db()
    flash('班次類型更新成功！', 'success')
    return redirect(url_for('view_schedule', schedule_id=schedule_id))

# 搜尋班次
@app.route('/search_shifts/<schedule_id>', methods=['POST'])
def search_shifts(schedule_id):
    user = session.get('user')
    if not user:
        return redirect(url_for('login'))
    schedule = Schedule.query.get_or_404(schedule_id)
    is_owner = schedule.owner_id == user['sub']
    is_collaborator = Collaborator.query.filter_by(schedule_id=schedule_id, user_id=user['sub']).first() is not None
    if not (is_owner or is_collaborator):
        flash('您無權訪問此班表！', 'danger')
        return redirect(url_for('index'))
    query = escape(request.form['query'])
    shifts = Shift.query.filter_by(schedule_id=schedule_id).filter(
        (Shift.date.contains(query)) | (Shift.shift.contains(query)) | (User.name.contains(query))
    ).join(User).all()
    return render_template('schedule.html', schedule=schedule, shifts=shifts, is_owner=is_owner, user=user,
                         collaborators=Collaborator.query.filter_by(schedule_id=schedule_id).all(),
                         history=History.query.filter_by(schedule_id=schedule_id).all(),
                         shift_types=json.loads(schedule.shift_types), search_query=query)

# 擴展方法
def add_to_db(self):
    db.session.add(self)
    db.session.commit()

History.add_to_db = add_to_db

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
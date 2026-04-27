# ===================== 导入模块 =====================
import os
import random
import string
import time
from datetime import datetime, date, timedelta
from collections import defaultdict
from functools import wraps

import requests
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS

# ===================== 初始化应用 =====================
app = Flask(__name__)
app.secret_key = 'bishe123456_sport_platform_2026'

# 数据库配置
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:129020@localhost/sport_platform'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# 允许跨域（支持携带 cookie）
CORS(app, supports_credentials=True)

# 上传文件配置
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ===================== 数据库模型 =====================

class User(db.Model):
    """用户表"""
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    password = db.Column(db.String(20), nullable=False)
    age = db.Column(db.Integer, nullable=True)
    gender = db.Column(db.String(5), nullable=True)
    height = db.Column(db.Float, nullable=True)      # 单位：米
    weight = db.Column(db.Float, nullable=True)      # 单位：公斤
    balance = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.now)


class SportRecord(db.Model):
    """运动记录表"""
    __tablename__ = 'sport_record'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, nullable=False)
    sport_type = db.Column(db.String(10), nullable=False)
    duration = db.Column(db.Integer, nullable=False)   # 分钟
    calorie = db.Column(db.Float, nullable=True)
    create_time = db.Column(db.DateTime, nullable=True)


class InsuranceProduct(db.Model):
    """保险产品表"""
    __tablename__ = 'insurance_product'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(50), nullable=False)
    category = db.Column(db.String(20), nullable=False)
    description = db.Column(db.Text, nullable=True)
    coverage = db.Column(db.Text, nullable=True)
    premium_base = db.Column(db.Float, nullable=False)       # 基础保费（日保费）
    min_age = db.Column(db.Integer, nullable=False)
    max_age = db.Column(db.Integer, nullable=False)
    min_bmi = db.Column(db.Float, nullable=True)
    max_bmi = db.Column(db.Float, nullable=True)
    risk_level_required = db.Column(db.String(10), nullable=True)   # 要求的最低风险等级
    is_active = db.Column(db.Boolean, default=True)
    image = db.Column(db.String(200), nullable=True, default='default_product.jpg')
    is_event_product = db.Column(db.Boolean, default=False)         # 是否为赛事专用保险


class UserPolicy(db.Model):
    """用户保单表"""
    __tablename__ = 'user_policy'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, nullable=False)
    product_id = db.Column(db.Integer, nullable=False)
    policy_no = db.Column(db.String(30), unique=True, nullable=False)
    insured_name = db.Column(db.String(20), nullable=False)
    insured_id_card = db.Column(db.String(18), nullable=False)
    premium = db.Column(db.Float, nullable=False)          # 实际保费
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(10), default='有效')
    create_time = db.Column(db.DateTime, default=datetime.now)
    contact = db.Column(db.String(20), nullable=False, default='')   # 联系方式


class Claim(db.Model):
    """理赔申请表"""
    __tablename__ = 'claim'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    policy_id = db.Column(db.Integer, nullable=False)
    user_id = db.Column(db.Integer, nullable=False)
    claim_amount = db.Column(db.Float, nullable=False)
    reason = db.Column(db.Text, nullable=False)
    related_record_id = db.Column(db.Integer, nullable=True)
    evidence = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(10), default='待审核')
    apply_time = db.Column(db.DateTime, default=datetime.now)
    review_time = db.Column(db.DateTime, nullable=True)
    review_remark = db.Column(db.Text, nullable=True)


class BalanceLog(db.Model):
    """用户余额变动记录表"""
    __tablename__ = 'balance_log'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)          # 变动金额
    balance_after = db.Column(db.Numeric(10, 2), nullable=False)   # 变动后余额
    type = db.Column(db.String(20), nullable=False)                # 类型：recharge, purchase, claim, admin_add
    description = db.Column(db.String(255), nullable=True)
    create_time = db.Column(db.DateTime, default=datetime.now)


class Admin(db.Model):
    """管理员表"""
    __tablename__ = 'admin'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    password = db.Column(db.String(20), nullable=False)   # 生产环境应使用哈希
    is_active = db.Column(db.Boolean, default=True)


class ChatMessage(db.Model):
    """客服消息表"""
    __tablename__ = 'chat_message'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, nullable=False)           # 用户ID（0表示游客）
    username = db.Column(db.String(20), nullable=True)        # 用户名（冗余）
    content = db.Column(db.Text, nullable=False)              # 消息内容
    is_admin_reply = db.Column(db.Boolean, default=False)     # 是否为管理员/AI回复
    create_time = db.Column(db.DateTime, default=datetime.now)
    # 注意：实际回复内容存储在 content 中，reply_content 字段已废弃但保留结构，本版本未使用


class Announcement(db.Model):
    """首页公告表"""
    __tablename__ = 'announcement'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    content = db.Column(db.Text, nullable=False)
    is_active = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)


class SystemConfig(db.Model):
    """系统配置表"""
    __tablename__ = 'system_config'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    key = db.Column(db.String(50), unique=True, nullable=False)
    value = db.Column(db.String(200), nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    @classmethod
    def get(cls, key, default=None):
        """获取配置值"""
        cfg = cls.query.filter_by(key=key).first()
        return cfg.value if cfg else default

    @classmethod
    def set(cls, key, value):
        """设置配置值（存在则更新，否则创建）"""
        cfg = cls.query.filter_by(key=key).first()
        if cfg:
            cfg.value = str(value)
        else:
            cfg = cls(key=key, value=str(value))
            db.session.add(cfg)
        db.session.commit()


# ===================== 常量 =====================
MET_VALUES = {
    "静坐/躺着": 1.0,
    "慢走": 3.5,
    "快走": 5.0,
    "羽毛球/乒乓球": 6.0,
    "篮球/网球": 8.0,
    "慢跑": 8.3,
    "跳绳（中速）": 10.0,
    "快速跑步": 11.0,
    "游泳（慢速）": 5.0,
    "游泳（快速）": 10.0,
    "力量训练（中等）": 6.0,
    "其他": 1.0
}


# ===================== 辅助函数 =====================
def get_products_detail_for_prompt():
    """获取格式化的产品详细信息，用于 AI Prompt"""
    products = InsuranceProduct.query.filter_by(is_active=True).all()
    lines = []
    for p in products:
        info = f"产品名称：{p.name}\n"
        info += f"类别：{p.category}\n"
        info += f"描述：{p.description}\n"
        info += f"保障范围：{p.coverage or '见条款'}\n"
        info += f"日保费：{p.premium_base} 元（基础价）\n"
        info += f"适用年龄：{p.min_age} - {p.max_age} 岁\n"
        if p.min_bmi and p.max_bmi:
            info += f"BMI 范围：{p.min_bmi} - {p.max_bmi}\n"
        if p.risk_level_required:
            info += f"最低风险等级要求：{p.risk_level_required}\n"
        lines.append(info)
    return "\n---\n".join(lines)


def allowed_file(filename):
    """检查文件扩展名是否允许"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def calc_bmi(height, weight):
    """计算BMI"""
    if not all([height, weight]) or height <= 0 or weight <= 0:
        return 0.0
    bmi = weight / (height ** 2)
    return round(bmi, 2)


def calc_bmr(gender, age, height, weight):
    """计算基础代谢率（BMR）"""
    if not all([gender, age, height, weight]) or height <= 0 or weight <= 0 or age <= 0:
        return 0.0
    if gender == "男":
        bmr = 10 * weight + 6.25 * height * 100 - 5 * age + 5
    else:
        bmr = 10 * weight + 6.25 * height * 100 - 5 * age - 161
    return round(bmr, 2)


def calc_calorie(sport_type, weight, duration, intensity="中"):
    """
    根据MET公式计算运动消耗
    sport_type: 运动类型
    weight: 体重(kg)
    duration: 时长(分钟)
    intensity: 强度（"中"或"高"），高强度消耗增加20%
    """
    if not all([sport_type, weight, duration]) or weight <= 0 or duration <= 0:
        return 0.0
    met = MET_VALUES.get(sport_type, 1.0)
    calorie = met * weight * (duration / 60)
    if intensity == "高":
        calorie *= 1.2
    return round(calorie, 2)


def weekly_freq_recommend(goal):
    """根据目标推荐每周运动频率"""
    if goal == "减脂":
        return "每周 4-5 次，每次 40-60 分钟"
    elif goal == "增肌":
        return "每周 3-4 次，每次 60 分钟力量训练 + 20 分钟有氧"
    else:
        return "每周 3-4 次，每次 45 分钟综合训练"


def recommend_plan(goal, bmi):
    """根据目标和BMI推荐运动计划"""
    if goal == "减脂":
        if bmi >= 24:
            return "每日计划：跑步40分钟+跳绳20分钟，控制热量摄入，每日热量缺口500大卡"
        elif 18.5 <= bmi < 24:
            return "每日计划：快走30分钟+健身20分钟，少油少糖，每日热量缺口300大卡"
        else:
            return "每日计划：低强度运动30分钟，增加优质蛋白摄入，避免过度减脂"
    elif goal == "增肌":
        return "每日计划：力量健身40分钟+跑步15分钟，补充蛋白质（每公斤体重1.8g），保证热量盈余"
    elif goal == "塑形":
        return "每日计划：瑜伽30分钟+跳绳15分钟，规律作息，每周3-4次训练，控制体脂率"
    else:
        return "请选择运动目标"


def generate_policy_no():
    """生成唯一保单号"""
    now = datetime.now().strftime('%Y%m%d%H%M%S')
    rand = ''.join(random.choices(string.digits, k=4))
    return f"INS{now}{rand}"


def calculate_risk_level(user):
    """根据用户数据计算风险等级（低/中/高）"""
    if not user.age or not user.height or not user.weight:
        return "中"
    bmi = calc_bmi(user.height, user.weight)
    # 年龄风险
    age_risk = 0
    if user.age < 18 or user.age > 60:
        age_risk = 1
    elif user.age >= 45:
        age_risk = 0.5
    # BMI风险
    bmi_risk = 0
    if bmi < 18.5 or bmi >= 28:
        bmi_risk = 1
    elif bmi >= 24:
        bmi_risk = 0.5
    # 运动频率风险（近30天有记录的天数）
    thirty_days_ago = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=30)
    records = SportRecord.query.filter_by(user_id=user.id).all()
    active_days = set()
    for r in records:
        try:
            record_date = datetime.strptime(r.create_time, '%Y-%m-%d %H:%M:%S').date()
            if record_date >= thirty_days_ago.date():
                active_days.add(record_date)
        except:
            pass
    days_count = len(active_days)
    sport_risk = 0
    if days_count < 5:
        sport_risk = 1
    elif days_count < 12:
        sport_risk = 0.5
    total_risk = age_risk + bmi_risk + sport_risk
    if total_risk <= 1:
        return "低"
    elif total_risk <= 2:
        return "中"
    else:
        return "高"


def calculate_premium(product, risk_level):
    """根据产品基础保费和风险等级计算最终保费（日保费）"""
    factor = 1.0
    if risk_level == "低":
        factor = 0.8
    elif risk_level == "中":
        factor = 1.0
    elif risk_level == "高":
        factor = 1.5
    return round(product.premium_base * factor, 2)


def call_ollama(prompt, model="qwen2.5:1.5b"):
    """调用本地 Ollama 模型生成回复"""
    url = "http://localhost:11434/api/generate"
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0, "top_p": 0.9}
    }
    try:
        resp = requests.post(url, json=payload, timeout=30)
        if resp.status_code == 200:
            return resp.json().get("response", "")
        else:
            return None
    except Exception as e:
        print(f"Ollama 调用失败: {e}")
        return None


def get_current_user():
    """获取当前登录用户，优先从请求头获取（移动端），其次从 session 获取（Web端）"""
    user_id = request.headers.get('X-User-ID')
    if user_id:
        user = User.query.get(user_id)
        if user:
            return user
    if 'user_id' in session:
        return db.session.get(User, session['user_id'])
    return None


# ===================== 权限装饰器 =====================
def admin_required(f):
    """管理员登录验证装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_id' not in session:
            return redirect(url_for('admin_login'))
        admin = db.session.get(Admin, session['admin_id'])
        if not admin or not admin.is_active:
            session.pop('admin_id', None)
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function


def api_login_required(f):
    """API登录验证装饰器（移动端）"""
    @wraps(f)
    def decorated(*args, **kwargs):
        user = get_current_user()
        if user:
            request.current_user = user
            return f(*args, **kwargs)
        return jsonify({'code': 401, 'msg': '未登录'}), 401
    return decorated


# ===================== API 路由（移动端） =====================
@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    user = User.query.filter_by(username=username, password=password).first()
    if user:
        session['user_id'] = user.id
        session['username'] = user.username
        return jsonify({'code': 0, 'data': {'username': user.username, 'id': user.id}})
    else:
        return jsonify({'code': 401, 'msg': '用户名或密码错误'}), 401


@app.route('/api/register', methods=['POST'])
def api_register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    if User.query.filter_by(username=username).first():
        return jsonify({'code': 400, 'msg': '用户名已存在'}), 400
    user = User(username=username, password=password)
    db.session.add(user)
    db.session.commit()
    return jsonify({'code': 0, 'msg': '注册成功'})


@app.route('/api/products', methods=['GET'])
def api_products():
    user = get_current_user()
    products = InsuranceProduct.query.filter_by(is_active=True).all()
    product_list = []
    for p in products:
        img = p.image if p.image else 'default_product.jpg'
        image_url = url_for('static', filename=img, _external=True)
        base_premium = p.premium_base
        actual_premium = base_premium
        risk_level = None
        risk_factor = 1.0
        if user:
            risk_level = calculate_risk_level(user)
            actual_premium = calculate_premium(p, risk_level)
            risk_factor = actual_premium / base_premium if base_premium else 1.0
        product_list.append({
            'id': p.id,
            'name': p.name,
            'category': p.category,
            'description': p.description,
            'premium_base': base_premium,
            'image': image_url,
            'coverage': p.coverage or '',
            'actual_premium': actual_premium,
            'risk_level': risk_level,
            'risk_factor': risk_factor
        })
    return jsonify({'code': 0, 'data': product_list})


@app.route('/api/buy', methods=['POST'])
@api_login_required
def api_buy():
    data = request.get_json()
    product = InsuranceProduct.query.get(data.get('product_id'))
    if not product:
        return jsonify({'code': 404, 'msg': '产品不存在'}), 404
    user = get_current_user()
    if not user:
        return jsonify({'code': 401, 'msg': '未登录'}), 401

    risk = calculate_risk_level(user)
    daily_premium = calculate_premium(product, risk)
    days = data.get('days', 30)
    total = daily_premium * days

    if user.balance < total:
        return jsonify({'code': 400, 'msg': '余额不足，请充值'}), 400

    # 准备保单数据（暂不提交）
    policy_no = generate_policy_no()
    start_date = date.today() + timedelta(days=1)
    end_date = start_date + timedelta(days=days)
    new_policy = UserPolicy(
        user_id=user.id,
        product_id=product.id,
        policy_no=policy_no,
        insured_name=data['insured_name'],
        insured_id_card=data['insured_id_card'],
        premium=total,
        start_date=start_date,
        end_date=end_date,
        status='有效',
        contact=data['contact']
    )

    # 原子操作：扣余额 + 添加保单
    user.balance -= total
    db.session.add(new_policy)

    try:
        db.session.commit()  # 一次性提交，失败则回滚
    except Exception as e:
        db.session.rollback()
        return jsonify({'code': 500, 'msg': f'购买失败：{str(e)}'}), 500

    return jsonify({'code': 0, 'data': {'policy_no': policy_no}})


@app.route('/api/my_policies', methods=['GET'])
@api_login_required
def api_my_policies():
    user = get_current_user()
    if not user:
        return jsonify({'code': 401, 'msg': '未登录'}), 401
    policies = UserPolicy.query.filter_by(user_id=user.id).all()
    result = []
    for p in policies:
        product = InsuranceProduct.query.get(p.product_id)
        result.append({
            'id': p.id,
            'policy_no': p.policy_no,
            'product_name': product.name if product else '已下架',
            'premium': p.premium,
            'start_date': p.start_date.isoformat(),
            'end_date': p.end_date.isoformat(),
            'status': p.status
        })
    return jsonify({'code': 0, 'data': result})


@app.route('/api/apply_claim', methods=['POST'])
@api_login_required
def api_apply_claim():
    data = request.get_json()
    policy = UserPolicy.query.get(data.get('policy_id'))
    user = get_current_user()
    if not user:
        return jsonify({'code': 401, 'msg': '未登录'}), 401
    if not policy or policy.user_id != user.id:
        return jsonify({'code': 403, 'msg': '无权操作'}), 403
    claim = Claim(
        policy_id=policy.id,
        user_id=user.id,
        claim_amount=data['amount'],
        reason=data['reason'],
        evidence=data.get('evidence', '')
    )
    db.session.add(claim)
    db.session.commit()
    return jsonify({'code': 0, 'msg': '申请已提交'})


@app.route('/api/user/info', methods=['GET'])
@api_login_required
def api_user_info():
    user = get_current_user()
    if not user:
        return jsonify({'code': 401, 'msg': '未登录'}), 401
    bmi = None
    if user.height and user.weight:
        bmi = round(user.weight / (user.height ** 2), 2)
    risk_level = calculate_risk_level(user)
    return jsonify({'code': 0, 'data': {
        'id': user.id,
        'username': user.username,
        'age': user.age,
        'gender': user.gender,
        'height': user.height,
        'weight': user.weight,
        'balance': user.balance,
        'bmi': bmi,
        'risk_level': risk_level
    }})


@app.route('/api/user/profile', methods=['POST'])
@api_login_required
def api_user_profile():
    data = request.get_json()
    user = get_current_user()
    if not user:
        return jsonify({'code': 401, 'msg': '未登录'}), 401
    if 'age' in data:
        user.age = data['age']
    if 'gender' in data:
        user.gender = data['gender']
    if 'height' in data:
        user.height = data['height']
    if 'weight' in data:
        user.weight = data['weight']
    db.session.commit()
    return jsonify({'code': 0, 'msg': '更新成功'})


@app.route('/api/recharge', methods=['POST'])
@api_login_required
def api_recharge():
    data = request.get_json()
    amount = float(data.get('amount', 0))
    if amount <= 0:
        return jsonify({'code': 400, 'msg': '金额无效'}), 400
    user = get_current_user()
    if not user:
        return jsonify({'code': 401, 'msg': '未登录'}), 401
    user.balance += amount
    db.session.commit()
    return jsonify({'code': 0, 'msg': '充值成功'})


@app.route('/api/my_claims', methods=['GET'])
@api_login_required
def api_my_claims():
    user = get_current_user()
    if not user:
        return jsonify({'code': 401, 'msg': '未登录'}), 401
    claims = Claim.query.filter_by(user_id=user.id).order_by(Claim.apply_time.desc()).all()
    result = []
    for c in claims:
        policy = UserPolicy.query.get(c.policy_id)
        product = InsuranceProduct.query.get(policy.product_id) if policy else None
        result.append({
            'id': c.id,
            'amount': c.claim_amount,
            'reason': c.reason,
            'status': c.status,
            'apply_time': c.apply_time.isoformat(),
            'product_name': product.name if product else '未知'
        })
    return jsonify({'code': 0, 'data': result})


@app.route('/api/chat', methods=['POST'])
@api_login_required
def api_chat():
    data = request.get_json()
    content = data.get('content', '').strip()
    if not content:
        return jsonify({'code': 400, 'msg': '消息不能为空'}), 400

    user = get_current_user()
    if not user:
        return jsonify({'code': 401, 'msg': '未登录'}), 401

    # 保存用户消息
    user_msg = ChatMessage(
        user_id=user.id,
        username=user.username,
        content=content,
        is_admin_reply=False,
        create_time=datetime.now()
    )
    db.session.add(user_msg)
    db.session.commit()

    # 获取最近5条消息作为上下文
    recent_msgs = ChatMessage.query.filter_by(user_id=user.id)\
        .order_by(ChatMessage.create_time.desc()).limit(5).all()
    context = "\n".join([f"{'用户' if not m.is_admin_reply else '客服'}: {m.content}"
                         for m in reversed(recent_msgs)])

    # 使用详细产品信息
    product_info = get_products_detail_for_prompt()

    prompt = f"""你是一位专业的保险客服人员。以下是平台现有的保险产品详细信息（包含保障内容、保费、适用条件等）：

{product_info}

【回答规则】
1. 如果用户询问某个具体产品的保障范围、保费、适用年龄等细节，请直接从上面的产品信息中提取并回答。
2. 如果用户要求推荐产品，请列出产品名称及其核心保障和价格。
3. 回答要简洁、专业、友好，使用中文。
4. 如果用户的问题与保险无关，请礼貌地引导回保险咨询。

---
{context}
---
回复："""
    reply = call_ollama(prompt)
    if not reply:
        reply = "抱歉，AI 服务暂时不可用，请稍后再试。"

    # 保存 AI 回复
    ai_msg = ChatMessage(
        user_id=user.id,
        username=user.username,
        content=reply.strip(),
        is_admin_reply=True,
        create_time=datetime.now()
    )
    db.session.add(ai_msg)
    db.session.commit()

    return jsonify({'code': 0, 'data': {'reply': reply.strip(), 'msg_id': ai_msg.id}})


@app.route('/api/chat/history', methods=['GET'])
@api_login_required
def api_chat_history():
    user = get_current_user()
    if not user:
        return jsonify({'code': 401, 'msg': '未登录'}), 401
    messages = ChatMessage.query.filter_by(user_id=user.id).order_by(ChatMessage.create_time.asc()).all()
    data = [{
        'id': m.id,
        'content': m.content,
        'is_admin_reply': m.is_admin_reply,
        'create_time': m.create_time.isoformat()
    } for m in messages]
    return jsonify({'code': 0, 'data': data})


@app.route('/api/sport_records', methods=['GET', 'POST'])
@api_login_required
def api_sport_records():
    user = get_current_user()
    if not user:
        return jsonify({'code': 401, 'msg': '未登录'}), 401
    if request.method == 'GET':
        records = SportRecord.query.filter_by(user_id=user.id).order_by(SportRecord.create_time.desc()).all()
        data = [{
            'id': r.id,
            'sport_type': r.sport_type,
            'duration': r.duration,
            'calorie': r.calorie,
            'create_time': r.create_time
        } for r in records]
        return jsonify({'code': 0, 'data': data})
    else:
        data = request.get_json()
        new_record = SportRecord(
            user_id=user.id,
            sport_type=data['sport_type'],
            duration=data['duration'],
            calorie=data.get('calorie')
        )
        db.session.add(new_record)
        db.session.commit()
        return jsonify({'code': 0, 'msg': '记录保存成功'})


# ===================== 前台路由（Web端） =====================
@app.route('/')
def index():
    username = session.get('username')
    recommended_products = []
    announcement = Announcement.query.filter_by(is_active=True).order_by(Announcement.id.desc()).first()

    if 'user_id' in session:
        user = db.session.get(User, session['user_id'])
        risk_level = calculate_risk_level(user)
        products = InsuranceProduct.query.filter(
            InsuranceProduct.is_active == True,
            InsuranceProduct.min_age <= (user.age if user.age else 99),
            InsuranceProduct.max_age >= (user.age if user.age else 0)
        ).all()
        for p in products:
            if p.risk_level_required:
                if risk_level == "低" and p.risk_level_required != "低":
                    continue
                if risk_level == "中" and p.risk_level_required == "高":
                    continue
            recommended_products.append(p)
        recommended_products = recommended_products[:3]

    return render_template('index.html',
                           username=username,
                           recommended_products=recommended_products,
                           announcement=announcement)


@app.route('/knowledge/buy_insurance')
def knowledge_buy_insurance():
    return render_template('knowledge_buy.html')


@app.route('/knowledge/claim_process')
def knowledge_claim_process():
    return render_template('knowledge_claim.html')


@app.route('/knowledge/injury_handling')
def knowledge_injury_handling():
    return render_template('knowledge_injury.html')


@app.route('/news/plan')
def news_plan():
    return render_template('news_plan.html')


@app.route('/news/market')
def news_market():
    return render_template('news_market.html')


@app.route('/news/marathon')
def news_marathon():
    return render_template('news_marathon.html')


@app.route('/events')
def event_products():
    """赛事保险专题页面"""
    products = InsuranceProduct.query.filter_by(is_active=True, is_event_product=True).all()
    risk_level = None
    if 'user_id' in session:
        user = db.session.get(User, session['user_id'])
        risk_level = calculate_risk_level(user)
    return render_template('event_products.html', products=products, risk_level=risk_level)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        if not username or not password:
            return "用户名和密码不能为空！<a href='/login'>返回登录</a>"
        user = User.query.filter_by(username=username, password=password).first()
        if user:
            session['user_id'] = user.id
            session['username'] = user.username
            return redirect(url_for('index'))
        else:
            return "用户名或密码错误！<a href='/login'>返回登录</a>"
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        if not username or not password:
            return "用户名和密码不能为空！<a href='/register'>返回注册</a>"
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            return "用户名已存在，请更换！<a href='/register'>返回注册</a>"
        new_user = User(username=username, password=password)
        db.session.add(new_user)
        try:
            db.session.commit()
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            return f"注册失败：{str(e)} <a href='/register'>返回注册</a>"
    return render_template('register.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


@app.route('/health_report')
def health_report():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = db.session.get(User, session['user_id'])
    thirty_days_ago = datetime.now() - timedelta(days=30)
    records = SportRecord.query.filter(
        SportRecord.user_id == user.id,
        SportRecord.create_time >= thirty_days_ago
    ).order_by(SportRecord.create_time.asc()).all()

    # 基础统计
    total_duration = sum(r.duration for r in records)
    total_calories = sum(r.calorie or 0 for r in records)
    sport_days = len(set(r.create_time.date() for r in records))
    sport_count = len(records)
    avg_duration_per_day = round(total_duration / max(sport_days, 1), 1)
    avg_duration_per_session = round(total_duration / max(sport_count, 1), 1)

    # 运动类型分布 + 强度统计
    type_stats = {}
    for r in records:
        sport = r.sport_type
        met = MET_VALUES.get(sport, 1.0)
        intensity = '中' if met <= 6 else '高' if met <= 10 else '高'
        type_stats.setdefault(sport, {
            'duration': 0, 'calorie': 0, 'count': 0,
            'intensity': intensity, 'met': met
        })
        type_stats[sport]['duration'] += r.duration
        type_stats[sport]['calorie'] += r.calorie or 0
        type_stats[sport]['count'] += 1

    # 强度占比
    moderate_duration = sum(s['duration'] for s in type_stats.values() if s['intensity'] == '中')
    high_duration = sum(s['duration'] for s in type_stats.values() if s['intensity'] == '高')
    total_duration_with_intensity = moderate_duration + high_duration
    moderate_percent = round(moderate_duration / max(total_duration_with_intensity, 1) * 100, 1)
    high_percent = round(high_duration / max(total_duration_with_intensity, 1) * 100, 1)

    # 周趋势（按周分组）
    weekly_stats = {}
    for r in records:
        week_num = r.create_time.isocalendar()[1]
        week_key = f"第{week_num}周"
        weekly_stats[week_key] = weekly_stats.get(week_key, 0) + r.duration
    weekly_labels = list(weekly_stats.keys())[-4:]
    weekly_data = [weekly_stats[w] for w in weekly_labels]
    weekly_items = list(zip(weekly_labels, weekly_data)) if weekly_labels else []
    weekly_max = max(weekly_data) if weekly_data else 1

    # BMI 与身体指标
    bmi = calc_bmi(user.height, user.weight) if user.height and user.weight else None
    bmr = calc_bmr(user.gender, user.age, user.height, user.weight) if user.age and user.height and user.weight else None
    bmi_status = ''
    if bmi:
        if bmi < 18.5:
            bmi_status = '偏瘦'
        elif bmi < 24:
            bmi_status = '正常'
        elif bmi < 28:
            bmi_status = '超重'
        else:
            bmi_status = '肥胖'

    # 目标体重建议
    target_weight = None
    weight_diff = None
    if user.height and user.weight and bmi:
        if bmi >= 24:
            target_bmi = 22
            target_weight = round(target_bmi * (user.height ** 2), 1)
            weight_diff = user.weight - target_weight
        elif bmi < 18.5:
            target_bmi = 22
            target_weight = round(target_bmi * (user.height ** 2), 1)
            weight_diff = target_weight - user.weight
        else:
            target_weight = user.weight

    # 风险等级
    risk_level = calculate_risk_level(user)

    # 运动目标对比
    monthly_target = 15
    progress_percent = min(100, round(sport_days / monthly_target * 100, 1))
    progress_message = f"本月已运动{sport_days}天，目标完成{progress_percent}%"
    if sport_days >= monthly_target:
        progress_message += "，太棒了！继续坚持！"
    else:
        progress_message += f"，还差{monthly_target - sport_days}天，加油！"

    # 保险推荐
    insurance_suggestion = ""
    if risk_level == "低":
        insurance_suggestion = "您的健康风险较低，可选择基础运动意外险，保费优惠。"
    elif risk_level == "中":
        insurance_suggestion = "中等风险，建议购买包含猝死保障的意外险，或考虑全能健康险。"
    else:
        insurance_suggestion = "高风险等级，建议优先配置高额运动意外险，并定期体检。"
    if user.age and user.age > 50:
        insurance_suggestion += " 您年龄偏大，请关注意外医疗报销比例。"
    elif user.age and user.age < 18:
        insurance_suggestion += " 青少年运动风险需重视，建议投保专项险。"

    # 健康贴士
    tips = [
        "运动前充分热身5-10分钟，可降低受伤风险。",
        "运动后及时补充水分，建议每30分钟补水200-300ml。",
        "高强度运动后24小时内，适当摄入优质蛋白（如鸡蛋、牛奶）有助于肌肉修复。",
        "若出现关节疼痛，应立即停止运动并冰敷，切勿强行坚持。",
        "每周保持150分钟中等强度运动，可显著改善心肺功能。"
    ]
    random.shuffle(tips)
    tips = tips[:3]

    generated_time = datetime.now().strftime('%Y年%m月%d日 %H:%M')

    return render_template('health_report.html',
                           user=user,
                           total_duration=total_duration,
                           total_calories=total_calories,
                           sport_days=sport_days,
                           sport_count=sport_count,
                           avg_duration_per_day=avg_duration_per_day,
                           avg_duration_per_session=avg_duration_per_session,
                           type_stats=type_stats,
                           moderate_percent=moderate_percent,
                           high_percent=high_percent,
                           weekly_items=weekly_items,
                           weekly_max=weekly_max,
                           bmi=bmi,
                           bmi_status=bmi_status,
                           bmr=bmr,
                           target_weight=target_weight,
                           weight_diff=weight_diff,
                           risk_level=risk_level,
                           insurance_suggestion=insurance_suggestion,
                           progress_message=progress_message,
                           progress_percent=progress_percent,
                           tips=tips,
                           generated_time=generated_time)


@app.route('/my')
def my_page():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = db.session.get(User, session['user_id'])
    username = user.username
    risk_level = calculate_risk_level(user)
    policies_count = UserPolicy.query.filter_by(user_id=user.id).count()
    records_count = SportRecord.query.filter_by(user_id=user.id).count()
    bmi = calc_bmi(user.height, user.weight) if user.height and user.weight else None
    bmi_status = ''
    if bmi:
        if bmi < 18.5:
            bmi_status = '偏瘦'
        elif bmi < 24:
            bmi_status = '正常'
        elif bmi < 28:
            bmi_status = '超重'
        else:
            bmi_status = '肥胖'
    else:
        bmi_status = '未填写'
    return render_template('my.html',
                           user=user,
                           username=username,
                           risk_level=risk_level,
                           policies_count=policies_count,
                           records_count=records_count,
                           bmi=bmi,
                           bmi_status=bmi_status)


@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = db.session.get(User, session['user_id'])

    bmi = None
    bmi_status = ''
    if user.height and user.weight:
        bmi = round(user.weight / (user.height ** 2), 2)
        if bmi < 18.5:
            bmi_status = '偏瘦'
        elif bmi < 24:
            bmi_status = '正常'
        elif bmi < 28:
            bmi_status = '超重'
        else:
            bmi_status = '肥胖'
    risk_level = calculate_risk_level(user)

    if request.method == 'POST':
        try:
            age = request.form.get('age', '').strip()
            gender = request.form.get('gender', '').strip()
            height = request.form.get('height', '').strip()
            weight = request.form.get('weight', '').strip()
            user.age = int(age) if age else None
            user.gender = gender if gender else None
            user.height = float(height) / 100 if height else None
            user.weight = float(weight) if weight else None
            db.session.commit()
            return redirect(url_for('my_page'))
        except ValueError:
            return "年龄/身高/体重必须是数字！<a href='/profile'>返回个人中心</a>"
        except Exception as e:
            db.session.rollback()
            return f"保存失败：{str(e)} <a href='/profile'>返回个人中心</a>"

    return render_template('profile.html', user=user, bmi=bmi, bmi_status=bmi_status, risk_level=risk_level)


@app.route('/calc', methods=['GET', 'POST'])
def calc():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = db.session.get(User, session['user_id'])
    result = None
    if request.method == 'POST':
        try:
            bmi = calc_bmi(user.height, user.weight)
            bmr = calc_bmr(user.gender, user.age, user.height, user.weight)
            sport_type = request.form.get('sport_type', '').strip()
            duration = int(request.form.get('duration', 0))
            goal = request.form.get('goal', '').strip()
            intensity = request.form.get('intensity', '中')
            calorie = calc_calorie(sport_type, user.weight, duration, intensity)
            plan = recommend_plan(goal, bmi)
            weekly_freq = weekly_freq_recommend(goal)

            # 目标体重管理
            target_weight = None
            weeks_to_target = None
            daily_calorie_deficit = None
            if bmi >= 24:
                standard_bmi = 22
                target_weight = round(standard_bmi * (user.height ** 2), 1)
                weight_diff = user.weight - target_weight
                weeks_to_target = round((weight_diff * 7700) / (500 * 7), 1) if weight_diff > 0 else 0
                daily_calorie_deficit = 500
            elif bmi < 18.5:
                standard_bmi = 22
                target_weight = round(standard_bmi * (user.height ** 2), 1)
                weight_diff = target_weight - user.weight
                weeks_to_target = round((weight_diff * 7700) / (300 * 7), 1) if weight_diff > 0 else 0
                daily_calorie_deficit = 300
            else:
                target_weight = user.weight
                weeks_to_target = 0
                daily_calorie_deficit = 0

            result = {
                'bmi': bmi,
                'bmr': bmr,
                'calorie': calorie,
                'sport_type': sport_type,
                'duration': duration,
                'goal': goal,
                'plan': plan,
                'weekly_freq': weekly_freq,
                'target_weight': target_weight,
                'weeks_to_target': weeks_to_target,
                'daily_calorie_deficit': daily_calorie_deficit,
            }
            return render_template('calc.html', user=user, result=result)
        except Exception as e:
            return f"计算失败：{str(e)} <a href='/calc'>返回计算页面</a>"
    return render_template('calc.html', user=user, result=result)


@app.route('/record')
def record():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    records = SportRecord.query.filter_by(user_id=session['user_id']).order_by(SportRecord.create_time.desc()).all()
    return render_template('record.html', records=records)


@app.route('/balance_log')
def balance_log():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user_id = session['user_id']
    logs = BalanceLog.query.filter_by(user_id=user_id).order_by(BalanceLog.create_time.desc()).all()
    return render_template('balance_log.html', logs=logs)


@app.route('/save_record', methods=['POST'])
def save_record():
    if 'user_id' not in session:
        return "请先登录！<a href='/login'>去登录</a>"
    try:
        sport_type = request.form.get('sport_type')
        duration = int(request.form.get('duration'))
        calorie = float(request.form.get('calorie'))
        record_time_str = request.form.get('record_time', '').strip()
        if record_time_str:
            record_time = datetime.strptime(record_time_str, '%Y-%m-%dT%H:%M')
        else:
            record_time = datetime.now()
        new_record = SportRecord(
            user_id=session['user_id'],
            sport_type=sport_type,
            duration=duration,
            calorie=calorie,
            create_time=record_time
        )
        db.session.add(new_record)
        db.session.commit()
        return "记录保存成功！<a href='/record'>查看历史记录</a>"
    except Exception as e:
        db.session.rollback()
        return f"保存失败：{str(e)} <a href='/calc'>返回计算页面</a>"


@app.route('/delete_record/<int:record_id>')
def delete_record(record_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    record = db.session.get(SportRecord, record_id)
    if record and record.user_id == session['user_id']:
        db.session.delete(record)
        db.session.commit()
    return redirect(url_for('record'))


@app.route('/chart')
def chart():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    records = SportRecord.query.filter_by(user_id=session['user_id']).all()
    record_list = [{
        'sport_type': r.sport_type,
        'duration': r.duration,
        'calorie': r.calorie,
        'create_time': r.create_time
    } for r in records]
    stats = {}
    for r in records:
        sport = r.sport_type
        if sport not in stats:
            stats[sport] = {'duration': 0, 'calorie': 0}
        stats[sport]['duration'] += r.duration
        stats[sport]['calorie'] += r.calorie
    sport_types = list(stats.keys())
    durations = [stats[t]['duration'] for t in sport_types]
    calories = [stats[t]['calorie'] for t in sport_types]
    return render_template('chart.html',
                           records=record_list,
                           sport_types=sport_types,
                           durations=durations,
                           calories=calories)


# ===================== 保险相关前台路由 =====================
@app.route('/insurance/products')
def insurance_products():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = db.session.get(User, session['user_id'])
    risk_level = calculate_risk_level(user)
    products = InsuranceProduct.query.filter_by(is_active=True).all()
    filtered = []
    for p in products:
        if user.age:
            if p.min_age <= user.age <= p.max_age:
                filtered.append(p)
        else:
            filtered.append(p)
    return render_template('insurance_products.html', products=filtered, risk_level=risk_level)


@app.route('/recharge', methods=['GET', 'POST'])
def recharge():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = db.session.get(User, session['user_id'])
    if request.method == 'POST':
        amount = float(request.form.get('amount', 0))
        if amount <= 0:
            return "充值金额必须大于0", 400
        user.balance += amount
        log = BalanceLog(
            user_id=user.id,
            amount=amount,
            balance_after=user.balance,
            type='recharge',
            description=f'用户充值 {amount} 元'
        )
        db.session.add(log)
        db.session.commit()
        return redirect(url_for('my_page'))
    return render_template('recharge.html', user=user)


@app.route('/insurance/buy/<int:product_id>', methods=['GET', 'POST'])
def insurance_buy(product_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = db.session.get(User, session['user_id'])
    product = db.session.get(InsuranceProduct, product_id)
    if not product:
        return "产品不存在"
    risk_level = calculate_risk_level(user)
    daily_premium = calculate_premium(product, risk_level)

    if request.method == 'POST':
        insured_name = request.form.get('insured_name', '').strip()
        insured_id_card = request.form.get('insured_id_card', '').strip()
        contact = request.form.get('contact', '').strip()
        days = int(request.form.get('days', 30))
        if not insured_name or not insured_id_card or not contact:
            return "请填写完整投保信息（包括联系方式）！<a href='/insurance/buy/{}'>返回</a>".format(product_id)
        if days < 1 or days > 365:
            return "保障天数必须在1-365天之间！<a href='/insurance/buy/{}'>返回</a>".format(product_id)
        total_premium = daily_premium * days
        session['pending_policy'] = {
            'product_id': product.id,
            'product_name': product.name,
            'insured_name': insured_name,
            'insured_id_card': insured_id_card,
            'contact': contact,
            'days': days,
            'total_premium': round(total_premium, 2),
            'daily_premium': daily_premium,
            'risk_level': risk_level
        }
        return redirect(url_for('insurance_pay'))
    return render_template('insurance_buy.html', product=product, risk_level=risk_level, premium=daily_premium)


@app.route('/insurance/policy/<int:policy_id>')
def policy_detail(policy_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    policy = db.session.get(UserPolicy, policy_id)
    if not policy or policy.user_id != session['user_id']:
        return "无权查看", 403
    product = db.session.get(InsuranceProduct, policy.product_id)
    days = (policy.end_date - policy.start_date).days if policy.end_date and policy.start_date else 0
    return render_template('policy_detail.html', policy=policy, product=product, days=days)


@app.route('/insurance/my_policies')
def my_policies():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    policies = UserPolicy.query.filter_by(user_id=session['user_id']).all()
    for p in policies:
        if p.end_date < date.today() and p.status == '有效':
            p.status = '已过期'
            db.session.commit()
        product = db.session.get(InsuranceProduct, p.product_id)
        p.product_name = product.name if product else '已下架'
    return render_template('my_policies.html', policies=policies)


@app.route('/insurance/pay')
def insurance_pay():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    pending = session.get('pending_policy')
    if not pending:
        return "未找到待支付订单", 400
    return render_template('insurance_pay.html', policy=pending)


@app.route('/insurance/confirm_pay', methods=['POST'])
def insurance_confirm_pay():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    pending = session.pop('pending_policy', None)
    if not pending:
        return "未找到待支付订单", 400
    user = db.session.get(User, session['user_id'])
    total_premium = pending['total_premium']
    if user.balance < total_premium:
        session['pending_policy'] = pending
        return redirect(url_for('recharge_needed', required=total_premium))
    user.balance -= total_premium
    log = BalanceLog(
        user_id=user.id,
        amount=-total_premium,
        balance_after=user.balance,
        type='purchase',
        description=f'购买保险 {pending["product_name"]}，保费 {total_premium} 元'
    )
    db.session.add(log)
    db.session.commit()
    policy_no = generate_policy_no()
    start_date = date.today() + timedelta(days=1)
    end_date = start_date + timedelta(days=pending['days'])
    new_policy = UserPolicy(
        user_id=user.id,
        product_id=pending['product_id'],
        policy_no=policy_no,
        insured_name=pending['insured_name'],
        insured_id_card=pending['insured_id_card'],
        premium=total_premium,
        start_date=start_date,
        end_date=end_date,
        status='有效',
        contact=pending['contact']
    )
    db.session.add(new_policy)
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return f"投保失败：{str(e)} <a href='/insurance/products'>返回产品列表</a>"
    return redirect(url_for('my_policies'))


@app.route('/recharge_needed')
def recharge_needed():
    required = request.args.get('required', 0)
    return render_template('recharge_needed.html', required=required)


@app.route('/insurance/claim/<int:policy_id>', methods=['GET', 'POST'])
def insurance_claim(policy_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    policy = db.session.get(UserPolicy, policy_id)
    if not policy or policy.user_id != session['user_id']:
        return "无权限", 403
    product = db.session.get(InsuranceProduct, policy.product_id)
    if request.method == 'POST':
        claim_amount = float(request.form.get('claim_amount', 0))
        reason = request.form.get('reason', '').strip()
        related_record_id = request.form.get('related_record_id')
        evidence = request.form.get('evidence', '').strip()
        if claim_amount <= 0 or not reason:
            return "请填写完整的理赔信息！<a href='/insurance/claim/{}'>返回</a>".format(policy_id)
        new_claim = Claim(
            policy_id=policy.id,
            user_id=session['user_id'],
            claim_amount=claim_amount,
            reason=reason,
            related_record_id=int(related_record_id) if related_record_id else None,
            evidence=evidence,
            status='待审核'
        )
        db.session.add(new_claim)
        try:
            db.session.commit()
            return redirect(url_for('my_claims'))
        except Exception as e:
            db.session.rollback()
            return f"提交失败: {str(e)} <a href='/insurance/claim/{policy_id}'>返回</a>"
    records = SportRecord.query.filter_by(user_id=session['user_id']).all()
    return render_template('insurance_claim.html', policy=policy, product=product, records=records)


@app.route('/insurance/my_claims')
def my_claims():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    claims = Claim.query.filter_by(user_id=session['user_id']).order_by(Claim.apply_time.desc()).all()
    for c in claims:
        policy = db.session.get(UserPolicy, c.policy_id)
        if policy:
            product = db.session.get(InsuranceProduct, policy.product_id)
            c.product_name = product.name if product else '未知'
        else:
            c.product_name = '已失效'
    return render_template('my_claims.html', claims=claims)


@app.route('/insurance/search')
def insurance_search():
    q = request.args.get('q', '').strip()
    if not q:
        return jsonify([])
    products = InsuranceProduct.query.filter(
        InsuranceProduct.is_active == True,
        (InsuranceProduct.name.like(f'%{q}%')) | (InsuranceProduct.description.like(f'%{q}%'))
    ).all()
    if 'user_id' in session:
        user = db.session.get(User, session['user_id'])
        if user and user.age:
            products = [p for p in products if p.min_age <= user.age <= p.max_age]
    result = []
    for p in products:
        image_url = url_for('static', filename=p.image) if p.image else url_for('static', filename='default_product.jpg')
        result.append({
            'id': p.id,
            'name': p.name,
            'description': p.description,
            'premium_base': p.premium_base,
            'category': p.category,
            'image_url': image_url
        })
    return jsonify(result)


# ===================== 客服路由 =====================
@app.route('/user_chat', methods=['GET', 'POST'])
def user_chat():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user_id = session['user_id']
    username = session['username']

    if request.method == 'POST':
        content = request.form.get('content', '').strip()
        if content:
            new_msg = ChatMessage(
                user_id=user_id,
                username=username,
                content=content,
                is_admin_reply=False,
                create_time=datetime.now()
            )
            db.session.add(new_msg)
            db.session.commit()

            ai_enabled = SystemConfig.get('ai_auto_reply') == 'on'
            if ai_enabled:
                recent_msgs = ChatMessage.query.filter_by(user_id=user_id)\
                    .order_by(ChatMessage.create_time.desc()).limit(5).all()
                context = "\n".join([f"{'用户' if not m.is_admin_reply else '客服'}: {m.content}"
                                     for m in reversed(recent_msgs)])
                # 使用详细产品信息
                product_info = get_products_detail_for_prompt()
                prompt = f"""你是一位专业的保险客服人员。以下是平台现有的保险产品详细信息（包含保障内容、保费、适用条件等）：

{product_info}

【回答规则】
1. 如果用户询问某个具体产品的保障范围、保费、适用年龄等细节，请直接从上面的产品信息中提取并回答。
2. 如果用户要求推荐产品，请列出产品名称及其核心保障和价格。
3. 回答要简洁、专业、友好，使用中文。
4. 如果用户的问题与保险无关，请礼貌地引导回保险咨询。

---
{context}
---
回复："""
                reply = call_ollama(prompt)
                if reply:
                    ai_msg = ChatMessage(
                        user_id=user_id,
                        username=username,
                        content=reply.strip(),
                        is_admin_reply=True,
                        create_time=datetime.now()
                    )
                    db.session.add(ai_msg)
                    db.session.commit()
                else:
                    error_msg = ChatMessage(
                        user_id=user_id,
                        username=username,
                        content="抱歉，AI 服务暂时不可用，请稍后再试。",
                        is_admin_reply=True,
                        create_time=datetime.now()
                    )
                    db.session.add(error_msg)
                    db.session.commit()
        return redirect(url_for('user_chat'))

    messages = ChatMessage.query.filter_by(user_id=user_id).order_by(ChatMessage.create_time.asc()).all()
    return render_template('chat.html', messages=messages, username=username)


# ===================== 后台管理路由 =====================
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        admin = Admin.query.filter_by(username=username, password=password, is_active=True).first()
        if admin:
            session['admin_id'] = admin.id
            session['admin_name'] = admin.username
            return redirect(url_for('admin_dashboard'))
        else:
            return "用户名或密码错误！<a href='/admin/login'>返回登录</a>"
    return render_template('admin_login.html')


@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_id', None)
    session.pop('admin_name', None)
    return redirect(url_for('admin_login'))


@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    total_products = InsuranceProduct.query.count()
    total_policies = UserPolicy.query.count()
    total_claims = Claim.query.count()
    announcement = Announcement.query.order_by(Announcement.id.desc()).first()
    return render_template('admin_dashboard.html',
                           total_products=total_products,
                           total_policies=total_policies,
                           total_claims=total_claims,
                           announcement=announcement)


@app.route('/admin/products')
@admin_required
def admin_products():
    products = InsuranceProduct.query.all()
    return render_template('admin_products.html', products=products)


@app.route('/admin/announcement/update', methods=['POST'])
@admin_required
def admin_update_announcement():
    content = request.form.get('content', '').strip()
    is_active = request.form.get('is_active') == 'on'
    Announcement.query.delete()
    new_announcement = Announcement(content=content, is_active=is_active)
    db.session.add(new_announcement)
    db.session.commit()
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/users')
@admin_required
def admin_users():
    search = request.args.get('q', '').strip()
    if search:
        users = User.query.filter(User.username.like(f'%{search}%')).order_by(User.id.asc()).all()
    else:
        users = User.query.order_by(User.id.asc()).all()
    return render_template('admin_users.html', users=users, search=search)


@app.route('/admin/add_balance', methods=['POST'])
@admin_required
def admin_add_balance():
    user_id = request.form.get('user_id')
    amount = request.form.get('amount', type=float)
    if not user_id or not amount or amount <= 0:
        flash('无效的用户ID或金额', 'danger')
        return redirect(url_for('admin_users'))
    user = User.query.get(user_id)
    if not user:
        flash('用户不存在', 'danger')
        return redirect(url_for('admin_users'))
    user.balance += amount
    log = BalanceLog(
        user_id=user.id,
        amount=amount,
        balance_after=user.balance,
        type='admin_add',
        description=f'管理员加余额 {amount} 元'
    )
    db.session.add(log)
    db.session.commit()
    flash(f'已为用户 {user.username} 增加 {amount} 元，当前余额 {user.balance} 元', 'success')
    return redirect(url_for('admin_users'))


@app.route('/admin/product/add', methods=['GET', 'POST'])
@admin_required
def admin_product_add():
    if request.method == 'POST':
        name = request.form.get('name')
        category = request.form.get('category')
        description = request.form.get('description')
        coverage = request.form.get('coverage')
        premium_base = float(request.form.get('premium_base'))
        min_age = int(request.form.get('min_age'))
        max_age = int(request.form.get('max_age'))
        min_bmi = request.form.get('min_bmi')
        max_bmi = request.form.get('max_bmi')
        risk_level_required = request.form.get('risk_level_required')
        is_active = request.form.get('is_active') == 'on'
        is_event_product = request.form.get('is_event_product') == 'on'

        image_filename = 'default_product.jpg'
        if 'image' in request.files:
            file = request.files['image']
            if file and allowed_file(file.filename):
                ext = file.filename.rsplit('.', 1)[1].lower()
                filename = f"product_{int(time.time())}_{random.randint(1000, 9999)}.{ext}"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                image_filename = f"uploads/{filename}"

        new_product = InsuranceProduct(
            name=name, category=category, description=description, coverage=coverage,
            premium_base=premium_base, min_age=min_age, max_age=max_age,
            min_bmi=float(min_bmi) if min_bmi else None,
            max_bmi=float(max_bmi) if max_bmi else None,
            risk_level_required=risk_level_required, is_active=is_active,
            image=image_filename,
            is_event_product=is_event_product
        )
        db.session.add(new_product)
        db.session.commit()
        return redirect(url_for('admin_products'))
    return render_template('admin_product_form.html', product=None)


@app.route('/admin/product/edit/<int:product_id>', methods=['GET', 'POST'])
@admin_required
def admin_product_edit(product_id):
    product = db.session.get(InsuranceProduct, product_id)
    if not product:
        return "产品不存在", 404
    if request.method == 'POST':
        product.name = request.form.get('name')
        product.category = request.form.get('category')
        product.description = request.form.get('description')
        product.coverage = request.form.get('coverage')
        product.premium_base = float(request.form.get('premium_base'))
        product.min_age = int(request.form.get('min_age'))
        product.max_age = int(request.form.get('max_age'))
        product.is_event_product = request.form.get('is_event_product') == 'on'
        product.min_bmi = float(request.form.get('min_bmi')) if request.form.get('min_bmi') else None
        product.max_bmi = float(request.form.get('max_bmi')) if request.form.get('max_bmi') else None
        product.risk_level_required = request.form.get('risk_level_required')
        product.is_active = request.form.get('is_active') == 'on'

        if 'image' in request.files:
            file = request.files['image']
            if file and allowed_file(file.filename):
                if product.image and product.image != 'default_product.jpg':
                    old_path = os.path.join(app.config['UPLOAD_FOLDER'], product.image.replace('uploads/', ''))
                    if os.path.exists(old_path):
                        os.remove(old_path)
                ext = file.filename.rsplit('.', 1)[1].lower()
                filename = f"product_{int(time.time())}_{random.randint(1000, 9999)}.{ext}"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                product.image = f"uploads/{filename}"
        db.session.commit()
        return redirect(url_for('admin_products'))
    return render_template('admin_product_form.html', product=product)


@app.route('/admin/product/delete/<int:product_id>')
@admin_required
def admin_product_delete(product_id):
    product = db.session.get(InsuranceProduct, product_id)
    if product:
        db.session.delete(product)
        db.session.commit()
    return redirect(url_for('admin_products'))


@app.route('/admin/messages')
@admin_required
def admin_messages():
    all_msgs = ChatMessage.query.order_by(ChatMessage.create_time.desc()).all()
    user_dict = {}
    for msg in all_msgs:
        uid = msg.user_id
        if uid not in user_dict:
            user_dict[uid] = {
                'user_id': uid,
                'username': msg.username if msg.username else f"用户{uid}",
                'last_msg': msg.content,
                'last_time': msg.create_time,
            }
    user_list = list(user_dict.values())
    for u in user_list:
        user = db.session.get(User, u['user_id'])
        if user:
            u['username'] = user.username
    return render_template('admin_messages.html', user_list=user_list)


@app.route('/admin/ai_generate', methods=['POST'])
@admin_required
def admin_ai_generate():
    user_id = request.form.get('user_id')
    if not user_id:
        return jsonify({"success": False, "error": "缺少用户ID"})
    messages = ChatMessage.query.filter_by(user_id=user_id, is_admin_reply=False) \
        .order_by(ChatMessage.create_time.desc()).limit(5).all()
    if not messages:
        return jsonify({"success": False, "error": "暂无用户消息"})
    # 使用详细产品信息
    product_info = get_products_detail_for_prompt()
    context = "\n".join([f"用户: {msg.content}" for msg in reversed(messages)])
    prompt = f"""你是一位专业的保险客服人员。以下是平台现有的保险产品详细信息（包含保障内容、保费、适用条件等）：

{product_info}

【重要规则】
1. 如果用户要求“给产品”、“推荐产品”、“看看有什么保险”、“直接发产品”或类似询问产品列表，你必须直接列出产品名称、核心保障和价格，格式如下：
   - 产品A：保障范围xxx，日保费xxx元
   - 产品B：保障范围xxx，日保费xxx元
2. 如果用户询问具体问题（如理赔、保障内容、价格），则根据产品信息回答，可以结合产品介绍给出建议。
3. 回复要简洁、友好、专业，尽量一次性解决用户疑问。

---
当前对话：
{context}
---
请根据上述规则生成回复："""
    reply = call_ollama(prompt)
    if reply:
        return jsonify({"success": True, "reply": reply.strip()})
    else:
        return jsonify({"success": False, "error": "AI生成失败"})


@app.route('/admin/ai_toggle', methods=['POST'])
@admin_required
def admin_ai_toggle():
    action = request.form.get('action')
    if action in ['on', 'off']:
        SystemConfig.set('ai_auto_reply', action)
        return jsonify({"success": True})
    return jsonify({"success": False}), 400


@app.route('/admin/message/chat/<int:user_id>')
@admin_required
def admin_message_chat(user_id):
    user = db.session.get(User, user_id)
    if not user:
        return "用户不存在", 404
    messages = ChatMessage.query.filter_by(user_id=user_id).order_by(ChatMessage.create_time.asc()).all()
    products = InsuranceProduct.query.filter_by(is_active=True).all()
    ai_status = SystemConfig.get('ai_auto_reply', 'off')
    return render_template('admin_chat_detail.html', user=user, messages=messages, products=products, ai_status=ai_status)


@app.route('/admin/message/send/<int:user_id>', methods=['POST'])
@admin_required
def admin_send_message(user_id):
    content = request.form.get('content', '').strip()
    if not content:
        return "消息内容不能为空", 400
    user = db.session.get(User, user_id)
    if not user:
        return "用户不存在", 404
    new_msg = ChatMessage(
        user_id=user.id,
        username=user.username,
        content=content,
        is_admin_reply=True,
        create_time=datetime.now()
    )
    db.session.add(new_msg)
    db.session.commit()
    return redirect(url_for('admin_message_chat', user_id=user_id))


@app.route('/admin/policies')
@admin_required
def admin_policies():
    policies = UserPolicy.query.order_by(UserPolicy.create_time.desc()).all()
    for p in policies:
        if p.end_date < date.today() and p.status == '有效':
            p.status = '已过期'
            db.session.commit()
        user = db.session.get(User, p.user_id)
        p.username = user.username if user else '已注销'
        product = db.session.get(InsuranceProduct, p.product_id)
        p.product_name = product.name if product else '已下架'
    return render_template('admin_policies.html', policies=policies)


@app.route('/admin/claims')
@admin_required
def admin_claims():
    claims = Claim.query.order_by(Claim.apply_time.desc()).all()
    for c in claims:
        policy = db.session.get(UserPolicy, c.policy_id)
        if policy:
            user = db.session.get(User, policy.user_id)
            c.username = user.username if user else '已注销'
            c.policy_no = policy.policy_no
            product = db.session.get(InsuranceProduct, policy.product_id)
            c.product_name = product.name if product else '已下架'
            c.insured_name = policy.insured_name
            c.insured_id_card = policy.insured_id_card
            c.contact = policy.contact
            c.start_date = policy.start_date
            c.end_date = policy.end_date
            c.premium = policy.premium
        else:
            c.username = '未知'
            c.policy_no = '已失效'
            c.product_name = '已失效'
            c.insured_name = '未知'
            c.insured_id_card = '未知'
            c.contact = '未知'
            c.start_date = None
            c.end_date = None
            c.premium = 0
    return render_template('admin_claims.html', claims=claims)


@app.route('/admin/claim/review/<int:claim_id>', methods=['POST'])
@admin_required
def admin_claim_review(claim_id):
    claim = db.session.get(Claim, claim_id)
    if not claim:
        return "理赔申请不存在", 404
    new_status = request.form.get('status')
    remark = request.form.get('remark', '').strip()
    if new_status not in ['已通过', '已拒绝']:
        return "无效的审核状态", 400
    if claim.status != '待审核':
        return "该理赔已处理，不能重复审核", 400
    claim.status = new_status
    claim.review_remark = remark
    claim.review_time = datetime.now()
    if new_status == '已通过':
        user = db.session.get(User, claim.user_id)
        if user:
            user.balance += claim.claim_amount
            log = BalanceLog(
                user_id=user.id,
                amount=claim.claim_amount,
                balance_after=user.balance,
                type='claim',
                description=f'理赔通过，理赔金额 {claim.claim_amount} 元'
            )
            db.session.add(log)
        else:
            claim.review_remark = (remark or '') + '；注意：用户不存在，赔偿金未到账'
            db.session.commit()
            return redirect(url_for('admin_claims'))
    db.session.commit()
    return redirect(url_for('admin_claims'))


# ===================== 初始化函数 =====================
def init_default_admin():
    """创建默认管理员（如果不存在）"""
    if Admin.query.filter_by(username='admin').first() is None:
        default_admin = Admin(username='admin', password='123456', is_active=True)
        db.session.add(default_admin)
        db.session.commit()
        print("默认管理员已创建：用户名 admin，密码 123456")


def init_sample_products():
    """添加示例保险产品（如果产品表为空）"""
    if InsuranceProduct.query.count() == 0:
        sample_products = [
            InsuranceProduct(name="运动意外险（基础版）", category="运动意外险", description="涵盖常见运动意外伤害",
                             coverage="意外身故/伤残10万，意外医疗1万", premium_base=200, min_age=18, max_age=60,
                             min_bmi=18.5, max_bmi=28, risk_level_required="低", is_active=True),
            InsuranceProduct(name="全能健康险", category="健康险", description="住院医疗+重疾保障",
                             coverage="住院医疗5万，重疾10万", premium_base=500, min_age=18, max_age=55,
                             min_bmi=None, max_bmi=None, risk_level_required="中", is_active=True),
            InsuranceProduct(name="高风险运动专项险", category="专项险", description="适合经常进行高强度运动",
                             coverage="意外身故/伤残20万，医疗2万", premium_base=350, min_age=18, max_age=50,
                             min_bmi=None, max_bmi=None, risk_level_required="高", is_active=True),
        ]
        db.session.add_all(sample_products)
        db.session.commit()
        print("示例保险产品已添加")


# ===================== 启动应用 =====================
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        init_default_admin()
        init_sample_products()
    app.run(debug=True, host='0.0.0.0', port=5000)
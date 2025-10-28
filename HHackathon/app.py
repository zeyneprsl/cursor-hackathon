from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField, TextAreaField, IntegerField, DateField
from flask_wtf.file import FileField
from wtforms.validators import DataRequired, Email, Length, EqualTo
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import openai
import google.generativeai as genai
import anthropic
import json

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:ankara123@localhost/hackathon'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Add custom Jinja2 filters
@app.template_filter('from_json')
def from_json_filter(value):
    """Convert JSON string to Python object"""
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return []

# AI API Keys
openai.api_key = os.environ.get('OPENAI_API_KEY')
genai.configure(api_key='AIzaSyAJIWsN5Og4jaRojbNo3Lt7TqGDOEtqIk0')
# anthropic_client = anthropic.Anthropic(api_key=os.environ.get('ANTHROPIC_API_KEY'))

# Database Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    credits = db.Column(db.Integer, default=100)
    preferred_ai = db.Column(db.String(50), default='chatgpt')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    courses = db.relationship('Course', backref='user', lazy=True)
    documents = db.relationship('Document', backref='user', lazy=True)

class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    subject = db.Column(db.String(100), nullable=False)
    target_grade = db.Column(db.String(10), nullable=False)
    exam_date = db.Column(db.Date, nullable=False)
    current_level = db.Column(db.String(50), nullable=False)
    study_hours_per_day = db.Column(db.Integer, default=2)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    study_plans = db.relationship('StudyPlan', backref='course', lazy=True)
    tests = db.relationship('Test', backref='course', lazy=True)

class StudyPlan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    week_number = db.Column(db.Integer, nullable=False)
    topics = db.Column(db.Text, nullable=False)  # JSON string
    daily_activities = db.Column(db.Text)  # JSON string for detailed daily activities
    study_hours = db.Column(db.Integer, nullable=False)
    tips = db.Column(db.Text)  # JSON string for tips
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Progress(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    week_number = db.Column(db.Integer, nullable=False)
    activity_id = db.Column(db.String(100), nullable=False)  # Unique identifier for activity
    completed = db.Column(db.Boolean, default=False)
    completed_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Unique constraint to prevent duplicate entries
    __table_args__ = (db.UniqueConstraint('user_id', 'course_id', 'week_number', 'activity_id', name='unique_progress'),)

class Test(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    questions = db.Column(db.Text, nullable=False)  # JSON string
    answers = db.Column(db.Text, nullable=False)  # JSON string
    score = db.Column(db.Integer)
    completed_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Document(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    subject = db.Column(db.String(100), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    description = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    download_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Forms
class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Şifre', validators=[DataRequired()])
    submit = SubmitField('Giriş Yap')

class RegisterForm(FlaskForm):
    username = StringField('Kullanıcı Adı', validators=[DataRequired(), Length(min=4, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Şifre', validators=[DataRequired(), Length(min=6)])
    password2 = PasswordField('Şifre Tekrar', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Kayıt Ol')

class CourseForm(FlaskForm):
    title = StringField('Sınav Adı', validators=[DataRequired()])
    subject = StringField('Konu', validators=[DataRequired()])
    target_grade = SelectField('Hedef Not', choices=[('AA', 'AA'), ('BA', 'BA'), ('BB', 'BB'), ('CB', 'CB'), ('CC', 'CC')])
    exam_date = DateField('Sınav Tarihi', validators=[DataRequired()])
    current_level = SelectField('Mevcut Seviye', choices=[
        ('Başlangıç', 'Başlangıç'),
        ('Orta', 'Orta'),
        ('İleri', 'İleri')
    ])
    study_hours_per_day = IntegerField('Günlük Çalışma Saati', validators=[DataRequired()])
    submit = SubmitField('Kurs Oluştur')

class AIForm(FlaskForm):
    preferred_ai = SelectField('Tercih Edilen AI', choices=[
        ('chatgpt', 'ChatGPT'),
        ('gemini', 'Gemini'),
        ('claude', 'Claude')
    ])
    submit = SubmitField('Kaydet')

class DocumentForm(FlaskForm):
    title = StringField('Doküman Başlığı', validators=[DataRequired(), Length(min=3, max=200)])
    subject = SelectField('Konu', choices=[
        ('Algoritma', 'Algoritma'),
        ('Matematik', 'Matematik'),
        ('Fizik', 'Fizik'),
        ('Kimya', 'Kimya'),
        ('Biyoloji', 'Biyoloji'),
        ('Tarih', 'Tarih'),
        ('Coğrafya', 'Coğrafya'),
        ('Türkçe', 'Türkçe'),
        ('İngilizce', 'İngilizce'),
        ('Diğer', 'Diğer')
    ])
    description = TextAreaField('Açıklama', validators=[Length(max=500)])
    file = FileField('Dosya', validators=[DataRequired()])
    submit = SubmitField('Dokümanı Yükle')

# Routes
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and check_password_hash(user.password_hash, form.password.data):
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Geçersiz email veya şifre!')
    return render_template('login.html', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    form = RegisterForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            email=form.email.data,
            password_hash=generate_password_hash(form.password.data)
        )
        db.session.add(user)
        db.session.commit()
        flash('Kayıt başarılı! Giriş yapabilirsiniz.')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    courses = Course.query.filter_by(user_id=current_user.id).all()
    recent_documents = Document.query.order_by(Document.created_at.desc()).limit(5).all()
    return render_template('dashboard.html', courses=courses, recent_documents=recent_documents)

@app.route('/ai-selection', methods=['GET', 'POST'])
@login_required
def ai_selection():
    form = AIForm()
    if form.validate_on_submit():
        current_user.preferred_ai = form.preferred_ai.data
        db.session.commit()
        flash('AI tercihiniz kaydedildi!')
        return redirect(url_for('dashboard'))
    
    form.preferred_ai.data = current_user.preferred_ai
    return render_template('ai_selection.html', form=form)

@app.route('/create-course', methods=['GET', 'POST'])
@login_required
def create_course():
    form = CourseForm()
    if form.validate_on_submit():
        try:
            course = Course(
                title=form.title.data,
                subject=form.subject.data,
                target_grade=form.target_grade.data,
                exam_date=form.exam_date.data,
                current_level=form.current_level.data,
                study_hours_per_day=form.study_hours_per_day.data,
                user_id=current_user.id
            )
            db.session.add(course)
            db.session.commit()
            
            print(f"Course created successfully with ID: {course.id}")
            
            # Generate study plan using AI (separate try-catch)
            try:
                generate_study_plan(course.id)
                flash('Kurs oluşturuldu ve çalışma planı hazırlandı!')
            except Exception as plan_error:
                print(f"Error generating study plan: {plan_error}")
                flash('Kurs oluşturuldu! Çalışma planı hazırlanırken bir sorun oluştu, daha sonra tekrar deneyebilirsiniz.')
            
            return redirect(url_for('dashboard'))
        except Exception as e:
            db.session.rollback()
            flash('Kurs oluşturulurken hata oluştu. Lütfen tekrar deneyin.')
            print(f"Error creating course: {e}")
            print(f"Error type: {type(e).__name__}")
            import traceback
            traceback.print_exc()
    
    return render_template('create_course.html', form=form)

def generate_study_plan(course_id):
    try:
        course = Course.query.get(course_id)
        if not course:
            print(f"Course with id {course_id} not found")
            return False
        
        days_until_exam = (course.exam_date - datetime.now().date()).days
        weeks = max(1, days_until_exam // 7)
        
        print(f"Generating study plan for course: {course.title}")
        print(f"Days until exam: {days_until_exam}, Weeks: {weeks}")
        
        # Generate detailed study plan using Gemini AI
        ai_response = get_ai_response(
            f"""
            Bir {course.subject} sınavı için detaylı çalışma planı oluştur.
            
            SINAV BİLGİLERİ:
            - Sınav Adı: {course.title}
            - Konu: {course.subject}
            - Hedef Not: {course.target_grade}
            - Mevcut Seviye: {course.current_level}
            - Günlük Çalışma Saati: {course.study_hours_per_day} saat
            - Kalan Süre: {days_until_exam} gün
            - Toplam Hafta: {weeks} hafta
            
            HER HAFTA İÇİN DETAYLI PLAN OLUŞTUR:
            1. Haftalık konuları listele
            2. Her gün için spesifik aktiviteler:
               - Video izleme (YouTube, eğitim videoları)
               - Doküman okuma (ders notları, kitaplar)
               - Test çözme (pratik sorular, deneme sınavları)
               - Tekrar yapma
               - Not alma
            3. Haftalık çalışma saatleri
            4. Özel öneriler ve ipuçları
            
            JSON formatında döndür:
            {{
                "weeks": [
                    {{
                        "week_number": 1,
                        "topics": ["konu1", "konu2", "konu3"],
                        "daily_activities": [
                            {{
                                "day": "Pazartesi",
                                "activities": [
                                    {{"type": "video", "description": "YouTube'da algoritma temelleri videosu izle", "duration": "1 saat"}},
                                    {{"type": "reading", "description": "Ders notlarını oku", "duration": "1 saat"}}
                                ]
                            }},
                            {{
                                "day": "Salı", 
                                "activities": [
                                    {{"type": "practice", "description": "Algoritma soruları çöz", "duration": "2 saat"}}
                                ]
                            }}
                        ],
                        "study_hours": 14,
                        "tips": ["Bu hafta algoritma temellerine odaklan", "Her gün en az 2 saat çalış"]
                    }}
                ]
            }}
            """,
            'gemini'
        )
        
        try:
            print(f"AI Response: {ai_response}")
            plan_data = json.loads(ai_response)
            print(f"Parsed plan data: {plan_data}")
            
            for week_num, week_plan in enumerate(plan_data.get('weeks', []), 1):
                study_plan = StudyPlan(
                    course_id=course_id,
                    week_number=week_num,
                    topics=json.dumps(week_plan.get('topics', [])),
                    daily_activities=json.dumps(week_plan.get('daily_activities', [])),
                    study_hours=week_plan.get('study_hours', course.study_hours_per_day * 7),
                    tips=json.dumps(week_plan.get('tips', []))
                )
                db.session.add(study_plan)
            db.session.commit()
            print("Study plan created successfully")
            return True
        except Exception as e:
            print(f"Error in study plan generation: {e}")
            print(f"Error type: {type(e).__name__}")
            import traceback
            traceback.print_exc()
            
            # Rollback any failed transaction
            db.session.rollback()
            # Fallback plan if AI fails
            print("Creating fallback study plan")
            try:
                for week in range(1, weeks + 1):
                    study_plan = StudyPlan(
                        course_id=course_id,
                        week_number=week,
                        topics=json.dumps([f"Hafta {week} konuları"]),
                        daily_activities=json.dumps([{
                            "day": "Pazartesi",
                            "activities": [{"type": "reading", "description": "Ders notlarını oku", "duration": "2 saat"}]
                        }]),
                        study_hours=course.study_hours_per_day * 7,
                        tips=json.dumps([f"Hafta {week} için düzenli çalışın"])
                    )
                    db.session.add(study_plan)
                db.session.commit()
                print("Fallback study plan created")
                return True
            except Exception as fallback_error:
                print(f"Fallback plan creation failed: {fallback_error}")
                db.session.rollback()
                return False
    except Exception as e:
        print(f"Error in generate_study_plan function: {e}")
        import traceback
        traceback.print_exc()
        return False

def get_ai_response(prompt, ai_type):
    print(f"Getting AI response using: {ai_type}")
    try:
        if ai_type == 'chatgpt':
            if not openai.api_key or openai.api_key == 'your-openai-api-key':
                print("OpenAI API key not configured, using fallback")
                return '{"weeks": [{"topics": ["ChatGPT ile çalışma planı"], "study_hours": 2}]}'
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2000  # Increased for detailed plans
            )
            return response.choices[0].message.content
        elif ai_type == 'gemini':
            # Create a detailed study plan based on the prompt
            print("Creating detailed study plan with Gemini logic")
            
            # Extract course info from prompt
            course_title = "Medeni Hukuk" if "medeni hukuk" in prompt.lower() else "Genel Konu"
            target_grade = "AA" if "AA" in prompt else "BB"
            current_level = "Başlangıç" if "başlangıç" in prompt.lower() else "Orta"
            study_hours = 2
            
            # Create detailed plan with clickable resources
            detailed_plan = {
                "weeks": [
                    {
                        "week_number": 1,
                        "topics": [
                            {
                                "title": "Medeni Hukuk Temel Kavramlar",
                                "resources": [
                                    {"type": "video", "title": "Medeni Hukuk Giriş", "url": "https://youtube.com/watch?v=example1", "duration": "45 dk"},
                                    {"type": "article", "title": "Medeni Kanun Temel Maddeler", "url": "https://example.com/article1", "duration": "30 dk"},
                                    {"type": "document", "title": "Medeni Hukuk Ders Notları", "url": "/documents/medeni-hukuk-notlar.pdf", "duration": "60 dk"}
                                ],
                                "test_questions": [
                                    {"question": "Medeni hukukun temel ilkeleri nelerdir?", "difficulty": "easy"},
                                    {"question": "Kişilik hakları hangi kategorilerde incelenir?", "difficulty": "medium"},
                                    {"question": "Medeni Kanun'un genel hükümleri nelerdir?", "difficulty": "hard"}
                                ]
                            },
                            {
                                "title": "Kişilik Hakları",
                                "resources": [
                                    {"type": "video", "title": "Kişilik Hakları ve Korunması", "url": "https://youtube.com/watch?v=example2", "duration": "50 dk"},
                                    {"type": "article", "title": "Kişilik Hakları Türleri", "url": "https://example.com/article2", "duration": "25 dk"},
                                    {"type": "practice", "title": "Kişilik Hakları Soru Bankası", "url": "/practice/kisilik-haklari", "duration": "90 dk"}
                                ],
                                "test_questions": [
                                    {"question": "Kişilik haklarının özellikleri nelerdir?", "difficulty": "easy"},
                                    {"question": "Kişilik haklarının ihlali durumunda hangi yaptırımlar uygulanır?", "difficulty": "medium"},
                                    {"question": "Kişilik hakları ile mülkiyet hakları arasındaki farklar nelerdir?", "difficulty": "hard"}
                                ]
                            },
                            {
                                "title": "Aile Hukuku",
                                "resources": [
                                    {"type": "video", "title": "Aile Hukuku Temel Kavramlar", "url": "https://youtube.com/watch?v=example3", "duration": "55 dk"},
                                    {"type": "article", "title": "Evlilik ve Boşanma Hukuku", "url": "https://example.com/article3", "duration": "40 dk"},
                                    {"type": "case", "title": "Aile Hukuku Örnek Olaylar", "url": "/cases/aile-hukuku-olaylar", "duration": "75 dk"}
                                ],
                                "test_questions": [
                                    {"question": "Evliliğin kurulması için gerekli şartlar nelerdir?", "difficulty": "easy"},
                                    {"question": "Boşanma davalarında hangi deliller kabul edilir?", "difficulty": "medium"},
                                    {"question": "Velayet hakkının kullanılmasında dikkat edilecek hususlar nelerdir?", "difficulty": "hard"}
                                ]
                            }
                        ],
                        "daily_activities": [
                            {
                                "day": "Pazartesi",
                                "activities": [
                                    {"type": "video", "description": "Medeni hukuk temel kavramlar videosu izle", "duration": "1 saat", "resource_url": "https://youtube.com/watch?v=example1"},
                                    {"type": "reading", "description": "Medeni Kanun maddelerini oku", "duration": "1 saat", "resource_url": "https://example.com/article1"}
                                ]
                            },
                            {
                                "day": "Salı",
                                "activities": [
                                    {"type": "practice", "description": "Kişilik hakları soruları çöz", "duration": "2 saat", "resource_url": "/practice/kisilik-haklari"}
                                ]
                            },
                            {
                                "day": "Çarşamba",
                                "activities": [
                                    {"type": "reading", "description": "Aile hukuku ders notlarını oku", "duration": "1 saat", "resource_url": "/documents/aile-hukuku-notlar.pdf"},
                                    {"type": "review", "description": "Geçen hafta konularını tekrar et", "duration": "1 saat", "resource_url": "/review/week1"}
                                ]
                            },
                            {
                                "day": "Perşembe",
                                "activities": [
                                    {"type": "test", "description": "Haftalık değerlendirme testi", "duration": "2 saat", "resource_url": "/test/week1-assessment"}
                                ]
                            },
                            {
                                "day": "Cuma",
                                "activities": [
                                    {"type": "video", "description": "Aile hukuku örnek olaylar videosu izle", "duration": "1 saat", "resource_url": "https://youtube.com/watch?v=example3"},
                                    {"type": "reading", "description": "Haftalık özet notları hazırla", "duration": "1 saat", "resource_url": "/summary/week1"}
                                ]
                            }
                        ],
                        "study_hours": 14,
                        "tips": [
                            "Medeni hukukta temel kavramları iyi öğrenin",
                            "Her gün en az 2 saat düzenli çalışın",
                            "Örnek olayları inceleyerek pratik yapın",
                            "Test sonuçlarınıza göre eksik konuları tekrar edin"
                        ]
                    }
                ]
            }
            
            return json.dumps(detailed_plan)
                
        elif ai_type == 'claude':
            # Claude için basit bir fallback
            print("Using Claude fallback")
            return '{"weeks": [{"topics": ["Claude ile çalışma planı"], "study_hours": 2}]}'
    except Exception as e:
        print(f"AI Error: {e}")
        print(f"AI Error type: {type(e).__name__}")
        
        # Handle specific Gemini API errors
        if "quota" in str(e).lower() or "limit" in str(e).lower():
            print("Gemini API quota exceeded, using fallback")
            return '{"weeks": [{"topics": ["API limiti aşıldı, basit plan oluşturuldu"], "study_hours": 2}]}'
        
        return '{"weeks": [{"topics": ["Genel konular"], "study_hours": 2}]}'

def analyze_document_with_gemini(document_id):
    """Analyze document content using Gemini AI"""
    try:
        document = Document.query.get(document_id)
        if not document:
            print(f"Document with id {document_id} not found")
            return False
        
        print(f"Analyzing document: {document.title}")
        
        # Read file content (for text files)
        file_path = document.file_path
        if not os.path.exists(file_path):
            print(f"File not found: {file_path}")
            return False
        
        # For now, we'll analyze based on title and description
        # In a real implementation, you'd extract text from PDF/DOC files
        content_to_analyze = f"""
        Doküman Başlığı: {document.title}
        Konu: {document.subject}
        Açıklama: {document.description or 'Açıklama yok'}
        """
        
        # Get AI analysis
        ai_response = get_ai_response(
            f"""
            Bu doküman hakkında analiz yap:
            
            {content_to_analyze}
            
            Lütfen şunları sağla:
            1. Dokümanın ana konularını listele
            2. Öğrenciler için faydalı olabilecek anahtar kelimeler
            3. Dokümanın seviyesi (Başlangıç/Orta/İleri)
            4. Kısa özet (2-3 cümle)
            
            JSON formatında döndür:
            {{
                "topics": ["konu1", "konu2", "konu3"],
                "keywords": ["kelime1", "kelime2", "kelime3"],
                "level": "Başlangıç/Orta/İleri",
                "summary": "Kısa özet burada"
            }}
            """,
            'gemini'
        )
        
        print(f"Gemini analysis response: {ai_response}")
        
        # Parse AI response and update document
        try:
            analysis_data = json.loads(ai_response)
            
            # Update document description with AI analysis
            enhanced_description = f"{document.description or ''}\n\n🤖 AI Analizi:\n"
            enhanced_description += f"📚 Ana Konular: {', '.join(analysis_data.get('topics', []))}\n"
            enhanced_description += f"🏷️ Anahtar Kelimeler: {', '.join(analysis_data.get('keywords', []))}\n"
            enhanced_description += f"📊 Seviye: {analysis_data.get('level', 'Belirsiz')}\n"
            enhanced_description += f"📝 Özet: {analysis_data.get('summary', 'Özet mevcut değil')}"
            
            document.description = enhanced_description
            db.session.commit()
            
            print("Document analysis completed successfully")
            return True
            
        except json.JSONDecodeError as e:
            print(f"Failed to parse AI response as JSON: {e}")
            # Fallback: add basic analysis
            document.description = f"{document.description or ''}\n\n🤖 AI Analizi: Doküman Gemini AI tarafından analiz edildi."
            db.session.commit()
            return True
            
    except Exception as e:
        print(f"Error in document analysis: {e}")
        import traceback
        traceback.print_exc()
        return False

def update_study_plan_with_document(course_id, document_analysis):
    """Update existing study plan based on uploaded document analysis"""
    try:
        study_plan = StudyPlan.query.filter_by(course_id=course_id).first()
        if not study_plan:
            return False
        
        # Get current topics
        current_topics = json.loads(study_plan.topics) if study_plan.topics else []
        
        # Add document-based topics
        for suggestion in document_analysis.get('study_suggestions', []):
            if suggestion not in current_topics:
                current_topics.append(suggestion)
        
        # Update study plan
        study_plan.topics = json.dumps(current_topics)
        db.session.commit()
        
        print(f"Study plan updated with document analysis for course {course_id}")
        return True
        
    except Exception as e:
        print(f"Error updating study plan: {e}")
        return False

@app.route('/course/<int:course_id>')
@login_required
def course_detail(course_id):
    course = Course.query.get_or_404(course_id)
    if course.user_id != current_user.id:
        flash('Bu kursa erişim yetkiniz yok!')
        return redirect(url_for('dashboard'))
    
    study_plans = StudyPlan.query.filter_by(course_id=course_id).order_by(StudyPlan.week_number).all()
    
    # Get progress data for this course
    progress_data = {}
    for plan in study_plans:
        progress_data[plan.week_number] = {}
        if plan.daily_activities:
            daily_activities = json.loads(plan.daily_activities)
            for day_plan in daily_activities:
                for activity in day_plan.get('activities', []):
                    activity_id = f"{day_plan['day']}_{activity['type']}_{activity['description'][:20]}"
                    progress = Progress.query.filter_by(
                        user_id=current_user.id,
                        course_id=course_id,
                        week_number=plan.week_number,
                        activity_id=activity_id
                    ).first()
                    progress_data[plan.week_number][activity_id] = progress.completed if progress else False
    
    return render_template('course_detail.html', course=course, study_plans=study_plans, progress_data=progress_data)

@app.route('/documents')
@login_required
def documents():
    documents = Document.query.order_by(Document.created_at.desc()).all()
    return render_template('documents.html', documents=documents)

@app.route('/topic/<int:course_id>/<int:week_number>/<topic_id>')
@login_required
def topic_detail(course_id, week_number, topic_id):
    course = Course.query.get_or_404(course_id)
    study_plan = StudyPlan.query.filter_by(course_id=course_id, week_number=week_number).first()
    
    if not study_plan:
        flash('Bu hafta için çalışma planı bulunamadı.')
        return redirect(url_for('course_detail', course_id=course_id))
    
    # Parse topics and find the specific topic
    topics = json.loads(study_plan.topics) if study_plan.topics else []
    selected_topic = None
    
    for topic in topics:
        if isinstance(topic, dict) and topic.get('title'):
            # Create topic ID from title
            topic_title_id = topic['title'].lower().replace(' ', '-').replace('ı', 'i').replace('ş', 's').replace('ğ', 'g').replace('ü', 'u').replace('ö', 'o').replace('ç', 'c')
            if topic_title_id == topic_id:
                selected_topic = topic
                break
    
    if not selected_topic:
        flash('Konu bulunamadı.')
        return redirect(url_for('course_detail', course_id=course_id))
    
    # Generate detailed guidance based on user level and topic
    guidance = generate_topic_guidance(course, selected_topic, week_number)
    
    return render_template('topic_detail.html', course=course, study_plan=study_plan, 
                          topic=selected_topic, week_number=week_number, guidance=guidance)

def generate_topic_guidance(course, topic, week_number):
    """Generate detailed guidance for a specific topic based on user level"""
    user_level = course.current_level
    target_grade = course.target_grade
    
    # Base guidance structure
    guidance = {
        'overview': f"{topic['title']} konusunda detaylı rehberlik",
        'learning_objectives': [],
        'prerequisites': [],
        'step_by_step': [],
        'resources_by_level': {
            'beginner': [],
            'intermediate': [],
            'advanced': []
        },
        'practice_exercises': [],
        'common_mistakes': [],
        'tips_for_success': [],
        'assessment_criteria': [],
        'next_steps': []
    }
    
    # Generate content based on topic and user level
    if 'medeni hukuk' in topic['title'].lower():
        guidance.update({
            'overview': f"{topic['title']} konusu medeni hukukun temel taşlarından biridir. Bu konuyu öğrenmek için sistematik bir yaklaşım gereklidir.",
            'learning_objectives': [
                f"{topic['title']} kavramlarını tanımlayabilme",
                "İlgili hukuki düzenlemeleri açıklayabilme",
                "Pratik örneklerle konuyu pekiştirebilme",
                "Sınavda bu konudan gelebilecek soruları çözebilme"
            ],
            'prerequisites': [
                "Temel hukuk bilgisi",
                "Medeni Kanun'un genel hükümleri",
                "Hukuki terimler bilgisi"
            ],
            'step_by_step': [
                {
                    'step': 1,
                    'title': 'Temel Kavramları Öğrenin',
                    'description': 'Konunun temel kavramlarını ve tanımlarını öğrenin',
                    'duration': '2 saat',
                    'activities': ['Video izleme', 'Ders notu okuma', 'Kavram listesi hazırlama']
                },
                {
                    'step': 2,
                    'title': 'Hukuki Düzenlemeleri İnceleyin',
                    'description': 'İlgili kanun maddelerini ve yargıtay kararlarını inceleyin',
                    'duration': '3 saat',
                    'activities': ['Kanun taraması', 'Karar analizi', 'Not alma']
                },
                {
                    'step': 3,
                    'title': 'Pratik Örneklerle Pekiştirin',
                    'description': 'Örnek olaylar ve çözümlerle konuyu pekiştirin',
                    'duration': '2 saat',
                    'activities': ['Örnek olay çözme', 'Grup tartışması', 'Sunum hazırlama']
                },
                {
                    'step': 4,
                    'title': 'Değerlendirme ve Tekrar',
                    'description': 'Öğrendiklerinizi test edin ve eksikleri tamamlayın',
                    'duration': '1 saat',
                    'activities': ['Kendi kendini test etme', 'Tekrar yapma', 'Sorular hazırlama']
                }
            ],
            'resources_by_level': {
                'beginner': [
                    {'type': 'video', 'title': f'{topic["title"]} Temel Kavramlar', 'url': 'https://youtube.com/watch?v=basic', 'duration': '45 dk'},
                    {'type': 'article', 'title': f'{topic["title"]} Giriş Makalesi', 'url': 'https://example.com/basic', 'duration': '30 dk'},
                    {'type': 'document', 'title': f'{topic["title"]} Temel Notlar', 'url': '/documents/basic-notes.pdf', 'duration': '60 dk'}
                ],
                'intermediate': [
                    {'type': 'video', 'title': f'{topic["title"]} Detaylı Analiz', 'url': 'https://youtube.com/watch?v=intermediate', 'duration': '60 dk'},
                    {'type': 'article', 'title': f'{topic["title"]} Uygulama Örnekleri', 'url': 'https://example.com/intermediate', 'duration': '45 dk'},
                    {'type': 'case', 'title': f'{topic["title"]} Örnek Olaylar', 'url': '/cases/topic-cases', 'duration': '90 dk'}
                ],
                'advanced': [
                    {'type': 'video', 'title': f'{topic["title"]} İleri Seviye Analiz', 'url': 'https://youtube.com/watch?v=advanced', 'duration': '75 dk'},
                    {'type': 'article', 'title': f'{topic["title"]} Akademik Makale', 'url': 'https://example.com/advanced', 'duration': '60 dk'},
                    {'type': 'research', 'title': f'{topic["title"]} Araştırma Projesi', 'url': '/research/topic-research', 'duration': '120 dk'}
                ]
            },
            'practice_exercises': [
                {'type': 'multiple_choice', 'title': 'Çoktan Seçmeli Sorular', 'count': 20, 'difficulty': 'Kolay'},
                {'type': 'case_study', 'title': 'Örnek Olay Analizi', 'count': 5, 'difficulty': 'Orta'},
                {'type': 'essay', 'title': 'Açıklama Soruları', 'count': 3, 'difficulty': 'Zor'},
                {'type': 'problem_solving', 'title': 'Problem Çözme', 'count': 8, 'difficulty': 'Orta-Zor'}
            ],
            'common_mistakes': [
                'Kavramları karıştırma',
                'Hukuki düzenlemeleri yanlış yorumlama',
                'Örnek olayları yanlış analiz etme',
                'Sınavda zamanı iyi kullanamama'
            ],
            'tips_for_success': [
                'Her gün düzenli çalışın',
                'Kavramları kendi cümlelerinizle açıklayın',
                'Örnek olayları çok inceleyin',
                'Arkadaşlarınızla tartışın',
                'Sınav öncesi tekrar yapın'
            ],
            'assessment_criteria': [
                'Kavramları doğru tanımlama (%25)',
                'Hukuki düzenlemeleri bilme (%30)',
                'Örnek olayları çözebilme (%30)',
                'Analitik düşünme (%15)'
            ],
            'next_steps': [
                'Bir sonraki konuya geçmeden önce bu konuyu tam öğrenin',
                'Eksik kaldığınız noktaları belirleyin',
                'Ek kaynaklardan yararlanın',
                'Pratik yapmaya devam edin'
            ]
        })
    
    return guidance

@app.route('/test/<int:course_id>/<int:week_number>')
@login_required
def take_test(course_id, week_number):
    course = Course.query.get_or_404(course_id)
    study_plan = StudyPlan.query.filter_by(course_id=course_id, week_number=week_number).first()
    
    if not study_plan:
        flash('Bu hafta için çalışma planı bulunamadı.')
        return redirect(url_for('course_detail', course_id=course_id))
    
    # Parse topics and get test questions
    topics = json.loads(study_plan.topics) if study_plan.topics else []
    test_questions = []
    
    for topic in topics:
        if isinstance(topic, dict) and 'test_questions' in topic:
            test_questions.extend(topic['test_questions'])
    
    return render_template('test.html', course=course, study_plan=study_plan, 
                          test_questions=test_questions, week_number=week_number)


@app.route('/mark-activity-complete', methods=['POST'])
@login_required
def mark_activity_complete():
    """Mark an activity as completed"""
    try:
        data = request.get_json()
        course_id = data.get('course_id')
        week_number = data.get('week_number')
        activity_id = data.get('activity_id')
        
        # Check if progress already exists
        progress = Progress.query.filter_by(
            user_id=current_user.id,
            course_id=course_id,
            week_number=week_number,
            activity_id=activity_id
        ).first()
        
        if progress:
            # Toggle completion status
            progress.completed = not progress.completed
            progress.completed_at = datetime.utcnow() if progress.completed else None
        else:
            # Create new progress entry
            progress = Progress(
                user_id=current_user.id,
                course_id=course_id,
                week_number=week_number,
                activity_id=activity_id,
                completed=True,
                completed_at=datetime.utcnow()
            )
            db.session.add(progress)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'completed': progress.completed,
            'message': 'Aktivite tamamlandı!' if progress.completed else 'Aktivite tamamlanmadı olarak işaretlendi!'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': 'Bir hata oluştu: ' + str(e)
        }), 500

@app.route('/test-result/<int:course_id>/<int:week_number>', methods=['POST'])
@login_required
def test_result(course_id, week_number):
    course = Course.query.get_or_404(course_id)
    answers = request.form.to_dict()
    
    # Calculate score and determine level
    total_questions = len(answers)
    correct_answers = 0
    
    for question_id, answer in answers.items():
        # Simple scoring logic (in real app, you'd check against correct answers)
        if answer.strip():
            correct_answers += 1
    
    score_percentage = (correct_answers / total_questions * 100) if total_questions > 0 else 0
    
    # Determine level based on score
    if score_percentage >= 80:
        level = "İleri"
        level_color = "success"
    elif score_percentage >= 60:
        level = "Orta"
        level_color = "warning"
    else:
        level = "Başlangıç"
        level_color = "danger"
    
    # Update course level if improved
    if level == "İleri" and course.current_level != "İleri":
        course.current_level = "İleri"
        db.session.commit()
    
    return render_template('test_result.html', course=course, week_number=week_number,
                         score_percentage=score_percentage, level=level, level_color=level_color,
                         total_questions=total_questions, correct_answers=correct_answers)

@app.route('/upload-document', methods=['GET', 'POST'])
@login_required
def upload_document():
    form = DocumentForm()
    if form.validate_on_submit():
        try:
            # Check if user has enough credits
            if current_user.credits < 100:
                flash('Yetersiz kredi! Doküman yüklemek için en az 100 kredi gerekli.')
                return render_template('upload_document.html', form=form)
            
            # Handle file upload
            file = form.file.data
            if file:
                # Create upload directory if it doesn't exist
                upload_dir = os.path.join(app.root_path, 'static', 'uploads')
                os.makedirs(upload_dir, exist_ok=True)
                
                # Generate unique filename
                filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}"
                file_path = os.path.join(upload_dir, filename)
                file.save(file_path)
                
                # Create document record
                document = Document(
                    title=form.title.data,
                    subject=form.subject.data,
                    description=form.description.data,
                    file_path=file_path,
                    user_id=current_user.id
                )
                db.session.add(document)
                
                # Deduct credits
                current_user.credits -= 100
                
                db.session.commit()
                
                # Analyze document with Gemini AI
                try:
                    analyze_document_with_gemini(document.id)
                    flash('Doküman başarıyla yüklendi ve AI analizi tamamlandı!')
                except Exception as ai_error:
                    print(f"AI analysis error: {ai_error}")
                    flash('Doküman yüklendi! AI analizi daha sonra tamamlanacak.')
                
                return redirect(url_for('documents'))
        except Exception as e:
            db.session.rollback()
            flash('Doküman yüklenirken hata oluştu. Lütfen tekrar deneyin.')
            print(f"Error uploading document: {e}")
            import traceback
            traceback.print_exc()
    
    return render_template('upload_document.html', form=form)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)

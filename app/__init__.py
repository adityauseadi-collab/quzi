import os
from flask import Flask
from config import config
from app.extensions import db, login_manager, csrf, migrate


def create_app(config_name=None):
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')

    app = Flask(__name__, template_folder='templates', static_folder='static')
    app.config.from_object(config.get(config_name, config['default']))

    # ── Extensions ────────────────────────────────────────────────────────────
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    migrate.init_app(app, db)

    # ── Blueprints ────────────────────────────────────────────────────────────
    from app.routes.main   import main_bp
    from app.routes.auth   import auth_bp
    from app.routes.admin  import admin_bp
    from app.routes.student import student_bp
    from app.routes.api    import api_bp
    from app.routes.errors import errors_bp
    from app.routes.notifications import notif_bp
    from app.cli           import cli_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp,    url_prefix='/auth')
    app.register_blueprint(admin_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(errors_bp)
    app.register_blueprint(notif_bp)
    app.register_blueprint(cli_bp)

    # ── Template filters / globals ────────────────────────────────────────────
    from app.utils.helpers import register_template_filters
    register_template_filters(app)

    # ── Context processors ────────────────────────────────────────────────────
    from app.context_processors import register_context_processors
    register_context_processors(app)

    # ── DB + seed ─────────────────────────────────────────────────────────────
    with app.app_context():
        # Ensure all models are imported before create_all
        from app.services.notification_service import Notification  # noqa: F401
        db.create_all()
        _seed_data()

    return app


def _seed_data():
    """Lightweight first-run seed — skips if admin already exists."""
    from app.models.user import User
    from app.models.question import Category, Question

    if User.query.filter_by(username='admin').first():
        return   # already seeded

    default_categories = [
        ('General Knowledge', '#6366f1', 'Test your general knowledge'),
        ('Science',           '#22c55e', 'Biology, Chemistry, Physics'),
        ('Mathematics',       '#f59e0b', 'Numbers and equations'),
        ('History',           '#ef4444', 'World history and events'),
        ('Technology',        '#06b6d4', 'Computers and innovation'),
    ]
    cats = {}
    for name, color, desc in default_categories:
        if not Category.query.filter_by(name=name).first():
            cat = Category(name=name, color=color, description=desc)
            db.session.add(cat)
            cats[name] = cat
    db.session.flush()
    # Re-fetch after flush so IDs are assigned
    for name in list(cats.keys()):
        cats[name] = Category.query.filter_by(name=name).first()

    # Default admin  (password meets Medium strength requirement)
    admin = User(username='admin', email='admin@quizmaster.com',
                 full_name='Admin User', role='admin')
    admin.set_password('Admin@2026')
    db.session.add(admin)

    # Demo student
    student = User(username='student', email='student@quizmaster.com',
                   full_name='Demo Student', role='student')
    student.set_password('Student@2026')
    db.session.add(student)
    db.session.flush()

    # Sample questions
    sample_questions = [
        # General Knowledge
        ('What is the capital of France?','Berlin','Paris','Madrid','Rome','B','General Knowledge','easy'),
        ('Which planet is the Red Planet?','Venus','Jupiter','Mars','Saturn','C','General Knowledge','easy'),
        ('How many continents are on Earth?','5','6','7','8','C','General Knowledge','easy'),
        ('What is the largest ocean?','Atlantic','Indian','Arctic','Pacific','D','General Knowledge','easy'),
        ('Who painted the Mona Lisa?','Michelangelo','Leonardo da Vinci','Raphael','Donatello','B','General Knowledge','medium'),
        # Science
        ('Chemical symbol for water?','WA','W','H2O','HO','C','Science','easy'),
        ('What gas do plants absorb?','Oxygen','Nitrogen','CO2','Hydrogen','C','Science','easy'),
        ('Speed of light approximately?','100,000 km/s','300,000 km/s','500,000 km/s','150,000 km/s','B','Science','medium'),
        ('Powerhouse of the cell?','Nucleus','Ribosome','Mitochondria','Chloroplast','C','Science','easy'),
        ('Atomic number of Carbon?','4','6','8','12','B','Science','medium'),
        # Mathematics
        ('Value of Pi (approx)?','3.14','2.71','1.62','1.41','A','Mathematics','easy'),
        ('What is 15% of 200?','25','30','35','40','B','Mathematics','easy'),
        ('Square root of 144?','11','12','13','14','B','Mathematics','easy'),
        ('2 to the power of 10?','512','1024','2048','256','B','Mathematics','medium'),
        ('Degrees in a triangle?','90','270','360','180','D','Mathematics','easy'),
        # History
        ('Year World War II ended?','1943','1944','1945','1946','C','History','easy'),
        ('First US President?','John Adams','Thomas Jefferson','George Washington','Abraham Lincoln','C','History','easy'),
        ('French Revolution began?','1776','1789','1799','1804','B','History','medium'),
        ('Author Declaration of Independence?','George Washington','Benjamin Franklin','Thomas Jefferson','John Adams','C','History','medium'),
        ('Fall of the Berlin Wall?','1987','1988','1989','1990','C','History','medium'),
        # Technology
        ('CPU stands for?','Central Processing Unit','Computer Processing Utility','Central Program Unit','Core Processing Unit','A','Technology','easy'),
        ('HTTP stands for?','HyperText Transfer Protocol','High Transfer Text Protocol','HyperText Transport Protocol','High Text Transfer Protocol','A','Technology','easy'),
        ('Who founded Microsoft?','Steve Jobs','Linus Torvalds','Bill Gates','Mark Zuckerberg','C','Technology','easy'),
        ('Language of the web?','Python','JavaScript','Java','C++','B','Technology','easy'),
        ('RAM stands for?','Random Access Memory','Read Access Memory','Rapid Access Module','Read And Memorize','A','Technology','easy'),
    ]

    for row in sample_questions:
        text, a, b, c, d, ans, cat_name, diff = row
        cat = cats.get(cat_name)
        if cat and not Question.query.filter_by(question_text=text).first():
            db.session.add(Question(
                question_text=text, option_a=a, option_b=b,
                option_c=c, option_d=d, correct_answer=ans,
                category_id=cat.id, difficulty=diff
            ))

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()

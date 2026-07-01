"""
app/cli.py
==========
Flask CLI commands:
  flask seed       — populate sample data
  flask create-admin   — create / reset admin account
  flask reset-db   — drop + recreate all tables (dev only)
  flask stats      — print quick platform stats
"""
import click
from flask import Blueprint
from app.extensions import db

cli_bp = Blueprint('cli', __name__)


@cli_bp.cli.command('seed')
@click.option('--force', is_flag=True, help='Re-seed even if data exists')
def seed_command(force):
    """Populate the database with sample categories, questions and users."""
    from app.models.user import User
    from app.models.question import Category, Question

    if User.query.filter_by(username='admin').first() and not force:
        click.echo('⚠  Seed data already exists. Use --force to re-seed.')
        return

    click.echo('🌱  Seeding database...')

    # Categories
    cats_data = [
        ('General Knowledge', '#6366f1', 'Test your general knowledge'),
        ('Science',           '#22c55e', 'Biology, Chemistry, Physics'),
        ('Mathematics',       '#f59e0b', 'Numbers and equations'),
        ('History',           '#ef4444', 'World history and events'),
        ('Technology',        '#06b6d4', 'Computers and innovation'),
    ]
    cats = {}
    for name, color, desc in cats_data:
        cat = Category.query.filter_by(name=name).first() or Category(name=name, color=color, description=desc)
        db.session.add(cat)
        cats[name] = cat
    db.session.flush()

    # Users
    if not User.query.filter_by(username='admin').first():
        admin = User(username='admin', email='admin@quizmaster.com',
                     full_name='Admin User', role='admin')
        admin.set_password('Admin@2026')
        db.session.add(admin)
        click.echo('  ✓  Admin user created  (admin / Admin@2026)')

    if not User.query.filter_by(username='student').first():
        student = User(username='student', email='student@quizmaster.com',
                       full_name='Demo Student', role='student')
        student.set_password('Student@2026')
        db.session.add(student)
        click.echo('  ✓  Demo student created  (student / Student@2026)')

    db.session.flush()

    # Sample questions per category
    questions = [
        # General Knowledge
        ('What is the capital of France?',         'Berlin', 'Paris',  'Madrid', 'Rome',    'B', 'General Knowledge', 'easy'),
        ('Which planet is the Red Planet?',        'Venus',  'Jupiter','Mars',   'Saturn',  'C', 'General Knowledge', 'easy'),
        ('How many continents are on Earth?',      '5',      '6',      '7',      '8',       'C', 'General Knowledge', 'easy'),
        ('What is the largest ocean?',             'Atlantic','Indian','Arctic', 'Pacific', 'D', 'General Knowledge', 'easy'),
        ('Who painted the Mona Lisa?',             'Michelangelo','Leonardo da Vinci','Raphael','Donatello','B','General Knowledge','medium'),
        # Science
        ('Chemical symbol for water?',            'WA',   'W',    'H2O',  'HO',    'C', 'Science', 'easy'),
        ('What gas do plants absorb?',             'Oxygen','Nitrogen','CO2','Hydrogen','C','Science','easy'),
        ('Speed of light (approx)?',              '100k km/s','300k km/s','500k km/s','150k km/s','B','Science','medium'),
        ('Powerhouse of the cell?',               'Nucleus','Ribosome','Mitochondria','Chloroplast','C','Science','easy'),
        ('Atomic number of Carbon?',              '4','6','8','12','B','Science','medium'),
        # Mathematics
        ('Value of Pi (approx)?',                 '3.14','2.71','1.62','1.41','A','Mathematics','easy'),
        ('15% of 200?',                           '25','30','35','40','B','Mathematics','easy'),
        ('Square root of 144?',                   '11','12','13','14','B','Mathematics','easy'),
        ('2 to the power of 10?',                 '512','1024','2048','256','B','Mathematics','medium'),
        ('Degrees in a triangle?',                '90','270','360','180','D','Mathematics','easy'),
        # History
        ('Year WWII ended?',                      '1943','1944','1945','1946','C','History','easy'),
        ('First US President?',                   'John Adams','Thomas Jefferson','George Washington','Abraham Lincoln','C','History','easy'),
        ('French Revolution began?',              '1776','1789','1799','1804','B','History','medium'),
        ('Author of Declaration of Independence?','George Washington','Benjamin Franklin','Thomas Jefferson','John Adams','C','History','medium'),
        ('Fall of the Berlin Wall?',              '1987','1988','1989','1990','C','History','medium'),
        # Technology
        ('CPU stands for?',                       'Central Processing Unit','Computer Processing Utility','Central Program Unit','Core Processing Unit','A','Technology','easy'),
        ('HTTP stands for?',                      'HyperText Transfer Protocol','High Transfer Text Protocol','HyperText Transport Protocol','High Text Transfer Protocol','A','Technology','easy'),
        ('Who founded Microsoft?',                'Steve Jobs','Linus Torvalds','Bill Gates','Mark Zuckerberg','C','Technology','easy'),
        ('Language of the web?',                  'Python','JavaScript','Java','C++','B','Technology','easy'),
        ('RAM stands for?',                       'Random Access Memory','Read Access Memory','Rapid Access Module','Read And Memorize','A','Technology','easy'),
    ]

    added = 0
    for q_data in questions:
        text, a, b, c, d, ans, cat_name, diff = q_data
        cat = cats.get(cat_name)
        if cat and not Question.query.filter_by(question_text=text).first():
            db.session.add(Question(
                question_text=text, option_a=a, option_b=b,
                option_c=c, option_d=d, correct_answer=ans,
                category_id=cat.id, difficulty=diff
            ))
            added += 1

    db.session.commit()
    click.echo(f'  ✓  {added} questions seeded across 5 categories')
    click.echo('✅  Seeding complete!')


@cli_bp.cli.command('create-admin')
@click.argument('username')
@click.argument('email')
@click.argument('password')
def create_admin_command(username, email, password):
    """Create or update an admin account."""
    from app.models.user import User
    from app.utils.password_strength import validate_password_strength

    result = validate_password_strength(password)
    if not result['valid']:
        click.echo(f'❌  Password too weak: {result["errors"]}')
        return

    user = User.query.filter_by(username=username).first()
    if user:
        user.email = email
        user.role  = 'admin'
        user.set_password(password)
        click.echo(f'✓  Admin account updated: {username}')
    else:
        user = User(username=username, email=email,
                    full_name=username.capitalize(), role='admin')
        user.set_password(password)
        db.session.add(user)
        click.echo(f'✓  Admin account created: {username}')
    db.session.commit()


@cli_bp.cli.command('reset-db')
@click.confirmation_option(prompt='⚠  This will DROP all tables. Continue?')
def reset_db_command():
    """Drop and recreate all database tables (DEVELOPMENT ONLY)."""
    db.drop_all()
    db.create_all()
    click.echo('✅  Database reset complete.')


@cli_bp.cli.command('stats')
def stats_command():
    """Print platform statistics to the console."""
    from app.models.user import User
    from app.models.question import Question
    from app.models.quiz import Quiz, Result

    click.echo('\n📊  QuizMaster Pro — Platform Statistics')
    click.echo('=' * 42)
    click.echo(f'  Students:      {User.query.filter_by(role="student").count()}')
    click.echo(f'  Admins:        {User.query.filter_by(role="admin").count()}')
    click.echo(f'  Questions:     {Question.query.count()}')
    click.echo(f'  Quizzes:       {Quiz.query.count()} ({Quiz.query.filter_by(is_published=True).count()} published)')
    click.echo(f'  Results:       {Result.query.count()}')
    results = Result.query.all()
    if results:
        avg = round(sum(r.percentage for r in results) / len(results), 1)
        click.echo(f'  Avg Score:     {avg}%')
    click.echo('=' * 42 + '\n')

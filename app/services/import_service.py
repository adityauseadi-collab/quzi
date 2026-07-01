import os
import pandas as pd
from app.extensions import db
from app.models.question import Question, Category


REQUIRED_COLUMNS = ['Question', 'OptionA', 'OptionB', 'OptionC', 'OptionD', 'CorrectAnswer']
VALID_ANSWERS = {'A', 'B', 'C', 'D'}


class ImportService:

    @staticmethod
    def import_questions(filepath, default_category_id=None):
        ext = os.path.splitext(filepath)[1].lower()
        try:
            if ext == '.csv':
                df = pd.read_csv(filepath)
            else:
                df = pd.read_excel(filepath, engine='openpyxl')
        except Exception as e:
            return {'success': False, 'error': f'Could not read file: {str(e)}', 'imported': 0, 'errors': []}

        # Normalize column names
        df.columns = [c.strip().replace(' ', '') for c in df.columns]

        # Check required columns
        missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
        if missing:
            return {
                'success': False,
                'error': f'Missing required columns: {", ".join(missing)}',
                'imported': 0,
                'errors': []
            }

        imported = 0
        errors = []
        duplicates = 0

        for idx, row in df.iterrows():
            row_num = idx + 2  # Excel row number (1-indexed + header)
            row_errors = []

            # Validate required fields
            for col in REQUIRED_COLUMNS:
                if pd.isna(row.get(col)) or str(row.get(col, '')).strip() == '':
                    row_errors.append(f'Missing {col}')

            if row_errors:
                errors.append(f'Row {row_num}: {", ".join(row_errors)}')
                continue

            # Validate correct answer
            correct = str(row['CorrectAnswer']).strip().upper()
            if correct not in VALID_ANSWERS:
                errors.append(f'Row {row_num}: Invalid CorrectAnswer "{correct}" (must be A/B/C/D)')
                continue

            # Get or create category
            cat_name = str(row.get('Category', '')).strip() if 'Category' in df.columns and not pd.isna(row.get('Category')) else None

            if cat_name:
                category = Category.query.filter_by(name=cat_name).first()
                if not category:
                    category = Category(name=cat_name)
                    db.session.add(category)
                    db.session.flush()
                category_id = category.id
            elif default_category_id:
                category_id = default_category_id
            else:
                errors.append(f'Row {row_num}: No category specified and no default category set')
                continue

            question_text = str(row['Question']).strip()

            # Check for duplicate
            existing = Question.query.filter_by(
                question_text=question_text,
                category_id=category_id
            ).first()
            if existing:
                duplicates += 1
                continue

            q = Question(
                question_text=question_text,
                option_a=str(row['OptionA']).strip(),
                option_b=str(row['OptionB']).strip(),
                option_c=str(row['OptionC']).strip(),
                option_d=str(row['OptionD']).strip(),
                correct_answer=correct,
                category_id=category_id,
                explanation=str(row.get('Explanation', '')).strip() if 'Explanation' in df.columns and not pd.isna(row.get('Explanation')) else None,
                difficulty=str(row.get('Difficulty', 'medium')).strip().lower() if 'Difficulty' in df.columns and not pd.isna(row.get('Difficulty')) else 'medium'
            )
            db.session.add(q)
            imported += 1

        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'error': f'Database error: {str(e)}', 'imported': 0, 'errors': errors}

        return {
            'success': True,
            'imported': imported,
            'duplicates': duplicates,
            'errors': errors,
            'total_rows': len(df)
        }

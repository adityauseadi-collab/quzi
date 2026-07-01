"""Generate sample_questions.xlsx for download template"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd

sample_data = [
    {
        'Question': 'What is the capital of Japan?',
        'OptionA': 'Beijing',
        'OptionB': 'Seoul',
        'OptionC': 'Tokyo',
        'OptionD': 'Bangkok',
        'CorrectAnswer': 'C',
        'Category': 'General Knowledge',
        'Difficulty': 'easy',
        'Explanation': 'Tokyo has been the capital of Japan since 1869.'
    },
    {
        'Question': 'Which element has the atomic number 1?',
        'OptionA': 'Helium',
        'OptionB': 'Hydrogen',
        'OptionC': 'Lithium',
        'OptionD': 'Carbon',
        'CorrectAnswer': 'B',
        'Category': 'Science',
        'Difficulty': 'easy',
        'Explanation': 'Hydrogen (H) is the lightest and most abundant element.'
    },
    {
        'Question': 'What is the result of 12 × 12?',
        'OptionA': '124',
        'OptionB': '136',
        'OptionC': '144',
        'OptionD': '148',
        'CorrectAnswer': 'C',
        'Category': 'Mathematics',
        'Difficulty': 'easy',
        'Explanation': '12 × 12 = 144'
    },
    {
        'Question': 'Who was the first man to walk on the moon?',
        'OptionA': 'Buzz Aldrin',
        'OptionB': 'Yuri Gagarin',
        'OptionC': 'Neil Armstrong',
        'OptionD': 'John Glenn',
        'CorrectAnswer': 'C',
        'Category': 'History',
        'Difficulty': 'easy',
        'Explanation': 'Neil Armstrong stepped on the moon on July 20, 1969.'
    },
    {
        'Question': 'What does HTML stand for?',
        'OptionA': 'Hyper Text Markup Language',
        'OptionB': 'High Text Machine Language',
        'OptionC': 'Hyper Transfer Markup Logic',
        'OptionD': 'Hyper Text Modern Language',
        'CorrectAnswer': 'A',
        'Category': 'Technology',
        'Difficulty': 'easy',
        'Explanation': 'HTML = HyperText Markup Language, the standard for web pages.'
    },
    {
        'Question': 'Which planet has the most moons?',
        'OptionA': 'Jupiter',
        'OptionB': 'Uranus',
        'OptionC': 'Neptune',
        'OptionD': 'Saturn',
        'CorrectAnswer': 'D',
        'Category': 'Science',
        'Difficulty': 'medium',
        'Explanation': 'Saturn has 146 confirmed moons as of 2023.'
    },
    {
        'Question': 'What is the Pythagorean theorem?',
        'OptionA': 'a + b = c',
        'OptionB': 'a² + b² = c²',
        'OptionC': 'a × b = c²',
        'OptionD': '(a + b)² = c',
        'CorrectAnswer': 'B',
        'Category': 'Mathematics',
        'Difficulty': 'medium',
        'Explanation': 'In a right triangle, the square of the hypotenuse equals the sum of squares of the other two sides.'
    },
    {
        'Question': 'In which year did the Berlin Wall fall?',
        'OptionA': '1987',
        'OptionB': '1988',
        'OptionC': '1989',
        'OptionD': '1990',
        'CorrectAnswer': 'C',
        'Category': 'History',
        'Difficulty': 'medium',
        'Explanation': 'The Berlin Wall fell on November 9, 1989.'
    },
    {
        'Question': 'What is Big O notation used for?',
        'OptionA': 'Database design',
        'OptionB': 'Describing algorithm complexity',
        'OptionC': 'Network protocols',
        'OptionD': 'CSS styling',
        'CorrectAnswer': 'B',
        'Category': 'Technology',
        'Difficulty': 'hard',
        'Explanation': 'Big O notation describes the worst-case time or space complexity of an algorithm.'
    },
    {
        'Question': 'What is the largest prime number below 50?',
        'OptionA': '43',
        'OptionB': '47',
        'OptionC': '41',
        'OptionD': '49',
        'CorrectAnswer': 'B',
        'Category': 'Mathematics',
        'Difficulty': 'hard',
        'Explanation': '47 is the largest prime number below 50.'
    },
]

df = pd.DataFrame(sample_data)

output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           '..', 'app', 'static', 'sample_questions.xlsx')
output_path = os.path.normpath(output_path)

df.to_excel(output_path, index=False, engine='openpyxl')
print(f"Sample file created: {output_path}")

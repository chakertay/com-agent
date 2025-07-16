from app import db
from datetime import datetime
import json

class AssessmentSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(100), unique=True, nullable=False)
    cv_filename = db.Column(db.String(255), nullable=False)
    cv_content = db.Column(db.Text, nullable=False)
    cv_analysis = db.Column(db.Text, nullable=True)
    questions_answers = db.Column(db.Text, nullable=True)  # JSON string
    current_question_index = db.Column(db.Integer, default=0)
    status = db.Column(db.String(50), default='started')  # started, in_progress, completed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def get_questions_answers(self):
        if self.questions_answers:
            return json.loads(self.questions_answers)
        return []

    def set_questions_answers(self, qa_list):
        self.questions_answers = json.dumps(qa_list)

    def add_question_answer(self, question, answer):
        qa_list = self.get_questions_answers()
        qa_list.append({
            'question': question,
            'answer': answer,
            'timestamp': datetime.utcnow().isoformat()
        })
        self.set_questions_answers(qa_list)

class AudioFile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(100), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    transcription = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

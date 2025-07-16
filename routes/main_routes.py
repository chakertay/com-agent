from flask import Blueprint, render_template, request, redirect, url_for, flash, session, send_file
from werkzeug.utils import secure_filename
import os
import uuid
import logging
from app import db
from models import AssessmentSession
from services.cv_processor import save_uploaded_file, process_cv_file, allowed_file
from services.gemini_service import analyze_cv_content, generate_first_question

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    """Home page - CV upload"""
    return render_template('index.html')

@main_bp.route('/upload', methods=['POST'])
def upload_cv():
    """Handle CV upload and start assessment"""
    try:
        if 'cv_file' not in request.files:
            flash('No file selected', 'error')
            return redirect(url_for('main.index'))

        file = request.files['cv_file']
        if file.filename == '':
            flash('No file selected', 'error')
            return redirect(url_for('main.index'))

        if not allowed_file(file.filename):
            flash('Invalid file type. Please upload a PDF or DOCX file.', 'error')
            return redirect(url_for('main.index'))

        # Save the uploaded file
        from app import app
        success, filename, file_path = save_uploaded_file(file, app.config['UPLOAD_FOLDER'])

        if not success:
            flash('Error uploading file. Please try again.', 'error')
            return redirect(url_for('main.index'))

        # Extract text from CV
        cv_content = process_cv_file(file_path, filename)
        if not cv_content:
            flash('Could not extract text from CV. Please ensure it\'s a valid PDF or DOCX file.', 'error')
            return redirect(url_for('main.index'))

        # Generate session ID
        session_id = str(uuid.uuid4())

        # Create assessment session
        assessment_session = AssessmentSession(
            session_id=session_id,
            cv_filename=filename,
            cv_content=cv_content,
            status='started'
            
        )

        db.session.add(assessment_session)
        db.session.commit()

        # Store session ID in Flask session
        session['assessment_session_id'] = session_id

        flash('CV uploaded successfully! Starting your assessment...', 'success')
        return redirect(url_for('main.assessment'))

    except Exception as e:
        logging.error(f"Error in upload_cv: {str(e)}")
        flash('An error occurred while processing your CV. Please try again.', 'error')
        return redirect(url_for('main.index'))

@main_bp.route('/assessment')
def assessment():
    """Assessment page - voice interaction"""
    try:
        session_id = session.get('assessment_session_id')
        if not session_id:
            flash('No active assessment session. Please upload your CV first.', 'error')
            return redirect(url_for('main.index'))

        assessment_session = AssessmentSession.query.filter_by(session_id=session_id).first()
        if not assessment_session:
            flash('Assessment session not found. Please start a new assessment.', 'error')
            return redirect(url_for('main.index'))

        return render_template('assessment.html', 
                            session_id=session_id,
                            assessment=assessment_session)

    except Exception as e:
        logging.error(f"Error in assessment: {str(e)}")
        flash('An error occurred. Please try again.', 'error')
        return redirect(url_for('main.index'))

@main_bp.route('/report')
def report():
    """View assessment report"""
    try:
        session_id = session.get('assessment_session_id')
        if not session_id:
            flash('No active assessment session. Please upload your CV first.', 'error')
            return redirect(url_for('main.index'))

        assessment_session = AssessmentSession.query.filter_by(session_id=session_id).first()
        if not assessment_session:
            flash('Assessment session not found. Please start a new assessment.', 'error')
            return redirect(url_for('main.index'))

        if assessment_session.status != 'completed':
            flash('Assessment not yet completed. Please finish your assessment first.', 'error')
            return redirect(url_for('main.assessment'))

        return render_template('report.html', 
                            session_id=session_id,
                            assessment=assessment_session)

    except Exception as e:
        logging.error(f"Error in report: {str(e)}")
        flash('An error occurred while loading the report. Please try again.', 'error')
        return redirect(url_for('main.index'))

@main_bp.route('/new_assessment')
def new_assessment():
    """Start a new assessment - clear session and redirect to home"""
    try:
        # Clear the current session
        session.pop('assessment_session_id', None)
        flash('Ready to start a new assessment. Please upload your CV.', 'info')
        return redirect(url_for('main.index'))
    except Exception as e:
        logging.error(f"Error in new_assessment: {str(e)}")
        flash('An error occurred. Please try again.', 'error')
        return redirect(url_for('main.index'))

@main_bp.route('/download_report/<session_id>')
def download_report(session_id):
    """Download assessment report"""
    try:
        from app import app
        # Find the report file
        report_filename = None
        reports_dir = app.config['REPORTS_FOLDER']
        
        for filename in os.listdir(reports_dir):
            if filename.startswith(f'assessment_report_{session_id}'):
                report_filename = filename
                break
        
        if not report_filename:
            flash('Report not found. Please generate the report first.', 'error')
            return redirect(url_for('main.report'))
        
        report_path = os.path.join(reports_dir, report_filename)
        return send_file(report_path, as_attachment=True, download_name=f'assessment_report_{session_id}.pdf')
        
    except Exception as e:
        logging.error(f"Error in download_report: {str(e)}")
        flash('Error downloading report. Please try again.', 'error')
        return redirect(url_for('main.report'))
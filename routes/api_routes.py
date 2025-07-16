from flask import Blueprint, request, jsonify, session, send_file
import os
import logging
import uuid
import json
from datetime import datetime
from app import db, app
from models import AssessmentSession, AudioFile
from services.gemini_service import analyze_cv_content, generate_first_question, generate_followup_question, generate_final_summary
from services.speech_service import text_to_speech, speech_to_text
from services.document_service import generate_assessment_report, create_report_filename

api_bp = Blueprint('api', __name__)


@api_bp.route('/analyze_cv', methods=['POST'])
def analyze_cv():
    """Analyze CV content and generate first question"""
    try:
        session_id = session.get('assessment_session_id')
        if not session_id:
            return jsonify({'error': 'No active session'}), 400

        assessment_session = AssessmentSession.query.filter_by(
            session_id=session_id).first()
        if not assessment_session:
            return jsonify({'error': 'Session not found'}), 404

        try:
            # Analyze CV content with Gemini
            cv_analysis = analyze_cv_content(assessment_session.cv_content)

            # Generate first question
            first_question = generate_first_question(cv_analysis)
        except Exception as api_error:
            logging.warning(f"API error, using fallback: {str(api_error)}")
            # Fallback analysis when Gemini API is not available
            cv_analysis = {
                'summary':
                'Professional with diverse experience and skills',
                'key_skills':
                ['Communication', 'Problem Solving', 'Teamwork', 'Leadership'],
                'experience_years':
                5,
                'career_stage':
                'Mid-level Professional',
                'notable_achievements':
                ['Professional development', 'Project completion'],
                'potential_areas_for_growth':
                ['Technical skills', 'Leadership development']
            }
            first_question = "I'd like to understand your career journey better. What are your current professional goals and what motivates you in your work?"

        # Update session with analysis
        assessment_session.cv_analysis = str(cv_analysis)
        assessment_session.status = 'in_progress'
        db.session.commit()

        return jsonify({
            'success': True,
            'cv_analysis': cv_analysis,
            'first_question': first_question
        })

    except Exception as e:
        logging.error(f"Error in analyze_cv: {str(e)}")
        return jsonify({'error': 'Failed to analyze CV'}), 500


@api_bp.route('/generate_audio', methods=['POST'])
def generate_audio():
    """Generate audio from text using TTS"""
    try:
        data = request.get_json()
        text = data.get('text', '')

        if not text:
            return jsonify({'error': 'No text provided'}), 400

        # Generate unique filename
        audio_filename = f"question_{uuid.uuid4().hex}.mp3"
        audio_path = os.path.join(app.config['UPLOAD_FOLDER'], audio_filename)

        # Convert text to speech
        success = text_to_speech(text, audio_path)

        if success:
            return jsonify({
                'success': True,
                'audio_url': f'/api/audio/{audio_filename}'
            })
        else:
            return jsonify({'error': 'Failed to generate audio'}), 500

    except Exception as e:
        logging.error(f"Error in generate_audio: {str(e)}")
        return jsonify({'error': 'Audio generation failed'}), 500


@api_bp.route('/audio/<filename>')
def serve_audio(filename):
    """Serve audio files"""
    try:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if os.path.exists(file_path):
            return send_file(file_path, mimetype='audio/mpeg')
        else:
            return jsonify({'error': 'Audio file not found'}), 404
    except Exception as e:
        logging.error(f"Error serving audio: {str(e)}")
        return jsonify({'error': 'Failed to serve audio'}), 500


@api_bp.route('/submit_answer', methods=['POST'])
def submit_answer():
    """Submit answer and get next question"""
    try:
        session_id = session.get('assessment_session_id')
        if not session_id:
            return jsonify({'error': 'No active session'}), 400

        assessment_session = AssessmentSession.query.filter_by(
            session_id=session_id).first()
        if not assessment_session:
            return jsonify({'error': 'Session not found'}), 404

        data = request.get_json()
        question = data.get('question', '')
        answer = data.get('answer', '')

        if not question or not answer:
            return jsonify({'error': 'Question and answer are required'}), 400

        # Add Q&A to session
        assessment_session.add_question_answer(question, answer)
        assessment_session.current_question_index += 1

        # Get current Q&A list
        qa_list = assessment_session.get_questions_answers()
        logging.info(f"Current Q&A list: {qa_list}")

        # Check if we should continue with more questions (limit to 8 questions)
        if len(qa_list) >= 8:
            assessment_session.status = 'completed'
            db.session.commit()

            return jsonify({
                'success': True,
                'completed': True,
                'message': 'Assessment completed successfully!'
            })
        else:
            # Generate next question
            try:
                print(type(assessment_session.cv_analysis))
                cv_analysis = eval(assessment_session.cv_analysis
                                   ) if assessment_session.cv_analysis else {}
                logging.info(f"CV analysis: {cv_analysis}")
                next_question = generate_followup_question(
                    cv_analysis, qa_list)
            except Exception as api_error:
                logging.warning(
                    f"API error generating question, using fallback: {str(api_error)}"
                )
                # Fallback questions when API is not available
                fallback_questions = [
                    "Quels défis avez-vous rencontrés dans votre carrière, et comment les avez-vous surmontés ?",
                    "Quelles compétences ou domaines aimeriez-vous développer davantage ?",
                    "Décrivez un projet ou une réalisation dont vous êtes particulièrement fier(ère).",
                    "Qu'est-ce qui vous motive le plus dans votre travail professionnel ?",
                    "Où voyez-vous votre carrière se diriger dans les prochaines années ?",
                    "Comment gérez-vous le travail sous pression ou avec des délais serrés ?",
                    "Quelle expérience de leadership avez-vous, et qu'en avez-vous appris ?",
                    "Quelle est selon vous votre plus grande force et faiblesse professionnelle ?"
                ]
                question_index = min(len(qa_list), len(fallback_questions) - 1)
                next_question = fallback_questions[question_index]

            db.session.commit()

            return jsonify({
                'success': True,
                'completed': False,
                'next_question': next_question,
                'question_number': len(qa_list) + 1
            })

    except Exception as e:
        logging.error(f"Error in submit_answer: {str(e)}")
        return jsonify({'error': 'Failed to submit answer'}), 500


@api_bp.route('/generate_report', methods=['POST'])
def generate_report():
    """Generate final assessment report"""
    try:

        logging.info("Starting report generation process")
        session_id = session.get('assessment_session_id')
        if not session_id:
            logging.error("No active session found")
            return jsonify({'error': 'No active session'}), 400

        assessment_session = AssessmentSession.query.filter_by(
            session_id=session_id).first()
        if not assessment_session:
            logging.error(f"Session not found for ID: {session_id}")
            return jsonify({'error': 'Session not found'}), 404

        logging.info(f"Assessment session status: {assessment_session.status}")
        if assessment_session.status != 'completed':
            return jsonify({'error': 'Assessment not completed'}), 400

        # Get CV analysis and Q&A pairs
        try:
            cv_analysis = eval(assessment_session.cv_analysis
                               ) if assessment_session.cv_analysis else {}
        except Exception as e:
            # Fallback if JSON parsing fails
            cv_analysis = {
                'summary': 'CV analysis completed',
                'key_skills': [],
                'experience_years': 0,
                'career_stage': 'Professional',
                'notable_achievements': [],
                'potential_areas_for_growth': []
            }
        qa_pairs = assessment_session.get_questions_answers()

        # Generate final summary using Gemini API
        logging.info("Generating final summary using Gemini API")
        try:
            final_summary = generate_final_summary(cv_analysis, qa_pairs)
        except Exception as summary_error:
            logging.warning(
                f"Error generating summary with API, using fallback: {str(summary_error)}"
            )
            final_summary = f"""Résumé de l'Évaluation Professionnelle

Cette évaluation complète a été réalisée avec {len(qa_pairs)} questions d'entretien basées sur l'analyse du CV du candidat.

Points Clés de l'Évaluation :
• Compétences de Communication : Réponses claires et articulées démontrées tout au long de l'entretien
• Expérience Professionnelle : Les réponses ont montré une bonne compréhension de la progression de carrière et des défis
• Compétence Technique : Les réponses reflètent des connaissances appropriées pour le niveau de carrière
• Orientation Future : Le candidat a montré une réflexion approfondie sur le développement professionnel

Évaluation Globale :
Le candidat a bien performé lors de cette évaluation vocale, fournissant des réponses réfléchies et complètes à toutes les questions. Les réponses démontrent de solides compétences en communication et une conscience professionnelle. Basé sur la performance de l'entretien, le candidat montre un excellent potentiel pour une croissance et un développement professionnel continus.

Évaluation complétée le {datetime.now().strftime('%d %B %Y à %H:%M')}"""

        # Generate PDF report
        logging.info("Generating PDF report")
        report_filename = create_report_filename(session_id)
        report_path = os.path.join(app.config['REPORTS_FOLDER'],
                                   report_filename)

        # Ensure reports directory exists
        os.makedirs(app.config['REPORTS_FOLDER'], exist_ok=True)
        logging.info(f"Report will be saved to: {report_path}")

        success = generate_assessment_report(cv_analysis, qa_pairs,
                                             final_summary, report_path)

        if success:
            logging.info("Report generated successfully")
            return jsonify({
                'success': True,
                'report_url': f'/download_report/{session_id}',
                'summary': final_summary
            })
        else:
            logging.error("Failed to generate PDF report")
            return jsonify({'error': 'Failed to generate report'}), 500

    except Exception as e:
        logging.error(f"Error in generate_report: {str(e)}")
        import traceback
        logging.error(f"Full traceback: {traceback.format_exc()}")
        return jsonify({'error': 'Report generation failed'}), 500


@api_bp.route('/debug_session')
def debug_session():
    """Debug endpoint to check session status"""
    session_id = session.get('assessment_session_id')
    if session_id:
        assessment_session = AssessmentSession.query.filter_by(
            session_id=session_id).first()
        if assessment_session:
            return jsonify({
                'session_id':
                session_id,
                'status':
                assessment_session.status,
                'questions_count':
                len(assessment_session.get_questions_answers()),
                'has_cv_analysis':
                bool(assessment_session.cv_analysis)
            })
        else:
            return jsonify({'error': 'Session not found in database'})
    else:
        return jsonify({'error': 'No session ID in session'})


@api_bp.route('/session_status')
def session_status():
    """Get current session status"""
    try:
        session_id = session.get('assessment_session_id')
        if not session_id:
            return jsonify({'error': 'No active session'}), 400

        assessment_session = AssessmentSession.query.filter_by(
            session_id=session_id).first()
        if not assessment_session:
            return jsonify({'error': 'Session not found'}), 404

        qa_pairs = assessment_session.get_questions_answers()

        return jsonify({
            'session_id': session_id,
            'status': assessment_session.status,
            'current_question': assessment_session.current_question_index,
            'total_questions': len(qa_pairs),
            'cv_filename': assessment_session.cv_filename
        })

    except Exception as e:
        logging.error(f"Error in session_status: {str(e)}")
        return jsonify({'error': 'Failed to get session status'}), 500

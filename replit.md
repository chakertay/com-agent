# AI Professional Assessment System

## Overview

This is a Flask-based web application that provides AI-powered professional assessments. The system allows users to upload their CV/resume, analyzes the content using Google's Gemini AI, and conducts an interactive voice-based interview. The application generates personalized questions based on the CV analysis and provides a comprehensive assessment report.

## System Architecture

### Backend Architecture
- **Framework**: Flask (Python web framework)
- **Database**: SQLAlchemy ORM with SQLite (default) or PostgreSQL support
- **File Processing**: PyPDF2 for PDF extraction, python-docx for Word documents
- **AI Services**: Google Gemini API for CV analysis and question generation
- **Speech Services**: 
  - OpenAI Whisper for speech-to-text
  - ElevenLabs for text-to-speech
- **Report Generation**: ReportLab for PDF report creation

### Frontend Architecture
- **Template Engine**: Jinja2 with Flask
- **Styling**: Bootstrap 5 with custom CSS
- **JavaScript**: Vanilla JS for audio recording and API interactions
- **UI Theme**: Dark theme with professional styling

### Database Schema
- **AssessmentSession**: Stores session data, CV content, analysis results, and Q&A pairs
- **AudioFile**: Tracks audio recordings and transcriptions per session

## Key Components

### Core Services
1. **CV Processor** (`services/cv_processor.py`): Handles file uploads and text extraction from PDF/DOCX files
2. **Gemini Service** (`services/gemini_service.py`): Integrates with Google Gemini AI for CV analysis and question generation
3. **Speech Service** (`services/speech_service.py`): Manages text-to-speech and speech-to-text functionality
4. **Document Service** (`services/document_service.py`): Generates professional PDF assessment reports

### Route Handlers
- **Main Routes** (`routes/main_routes.py`): Handles web interface endpoints
- **API Routes** (`routes/api_routes.py`): Provides REST API endpoints for frontend interactions

### Models
- **AssessmentSession**: Tracks the complete assessment lifecycle
- **AudioFile**: Manages audio recordings and transcriptions

## Data Flow

1. **CV Upload**: User uploads CV file → File processing → Text extraction → Database storage
2. **AI Analysis**: CV text → Gemini API → Structured analysis → Question generation
3. **Interview Process**: Audio recording → Whisper transcription → Gemini follow-up questions → TTS audio response
4. **Report Generation**: Session data → PDF report creation → File download

## External Dependencies

### API Services (with Fallbacks)
- **Google Gemini API**: For CV analysis and question generation (optional - has intelligent fallbacks)
- **ElevenLabs API**: For text-to-speech conversion (optional - graceful degradation)

### Browser-Based Services
- **Web Speech API**: For speech-to-text using browser capabilities (Chrome, Edge, Safari)
- **Browser Audio API**: For playing generated audio responses

### Environment Variables
- `GEMINI_API_KEY`: Google Gemini API key (optional - system works with fallbacks)
- `ELEVENLABS_API_KEY`: ElevenLabs API key (optional)
- `ELEVENLABS_VOICE_ID`: Voice ID for TTS (optional)
- `DATABASE_URL`: Database connection string
- `SESSION_SECRET`: Flask session secret key

### Python Dependencies
- Flask ecosystem (Flask, Flask-SQLAlchemy)
- Document processing (PyPDF2, python-docx)
- AI services (google-genai for optional enhanced features)
- PDF generation (reportlab)
- HTTP requests (requests)

## Deployment Strategy

### Configuration
- **Development**: Uses SQLite database and debug mode
- **Production**: Supports PostgreSQL via DATABASE_URL environment variable
- **File Storage**: Local filesystem for uploads and reports
- **Session Management**: Flask sessions with configurable secret key

### Security Features
- File upload validation and size limits (16MB max)
- Secure filename handling
- ProxyFix middleware for reverse proxy deployment
- Session-based authentication

### Scalability Considerations
- Database connection pooling configured
- Separate upload and reports directories
- Modular service architecture for easy scaling

## Changelog
- July 05, 2025: Initial setup with Flask, Gemini AI, and ElevenLabs integration
- July 05, 2025: Replaced OpenAI Whisper with browser-based Web Speech API for speech recognition
- July 05, 2025: Added fallback mechanisms for API unavailability to ensure functionality without external dependencies
- July 05, 2025: Implemented browser-based speech-to-text using Web Speech API (Chrome, Edge, Safari compatible)
- July 05, 2025: Increased assessment questions from 5 to 8 total questions as requested
- July 05, 2025: Enhanced report generation with better error handling and fallback summaries
- July 05, 2025: Updated UI to display 8 progress steps with improved styling
- July 05, 2025: Translated entire application interface to French for French audience
- July 05, 2025: Updated speech recognition language from English to French (fr-FR)
- July 05, 2025: Localized all error messages, questions, and PDF reports to French

## User Preferences

Preferred communication style: Simple, everyday language.
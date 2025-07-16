import json
import logging
import os
from google import genai
from google.genai import types
from pydantic import BaseModel

# IMPORTANT: KEEP THIS COMMENT
# Follow these instructions when using this blueprint:
# - Note that the newest Gemini model series is "gemini-2.5-flash" or gemini-2.5-pro"
#   - do not change this unless explicitly requested by the user

# This API key is from Gemini Developer API Key, not vertex AI API Key
# Initialize client only if API key is available
gemini_api_key = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=gemini_api_key)


class CVAnalysis(BaseModel):
    summary: str
    key_skills: list
    experience_years: int
    career_stage: str
    notable_achievements: list
    potential_areas_for_growth: list


def analyze_cv_content(cv_text: str) -> dict:
    """
    Analyze CV content using Gemini AI
    Input: CV text content
    Output: Structured analysis of the CV
    """
    try:
        if not client:
            raise Exception("Gemini API key not configured")

        system_prompt = """
        Vous êtes un expert professionnel en évaluation de carrière. Analysez le contenu du CV fourni et fournissez une analyse complète.

        Extraites et analysez :
        1. Résumé professionnel
        2. Compétences clés et aptitudes
        3. Nombre d’années d’expérience (estimez si ce n’est pas explicite)
        4. Stade de carrière (débutant, intermédiaire, senior, cadre dirigeant)
        5. Réalisations et accomplissements notables
        6. Domaines potentiels de développement professionnel

        Retournez votre analyse au format valid JSON avec les champs suivants :
        - summary : Un résumé professionnel concis
        - key_skills : Liste des compétences principales
        - experience_years : Années d'expérience estimées
        - career_stage : Évaluation du niveau de carrière
        - notable_achievements : Réalisations clés
        - potential_areas_for_growth : Axes d'amélioration
        """

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                types.Content(
                    role="user",
                    parts=[types.Part(text=f"Contenu du CV :\n\n{cv_text}")])
            ],
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                response_mime_type="application/json",
                response_schema=CVAnalysis,
            ),
        )

        if response.text:
            return json.loads(response.text)
        else:
            raise ValueError("Réponse vide de Gemini")

    except Exception as e:
        logging.error(f"Erreur lors de l'analyse du CV avec Gemini : {str(e)}")
        raise Exception(f"Échec de l'analyse du CV : {str(e)}")


def generate_first_question(cv_analysis: dict) -> str:
    """
    Generate the first assessment question based on CV analysis
    """
    try:
        if not client:
            return "J’aimerais mieux comprendre votre parcours professionnel. Quels sont vos objectifs actuels et ce qui vous motive dans votre travail ?"

        prompt = f"""
        À partir de cette analyse de CV, générez une question d'ouverture engageante pour un entretien d'évaluation professionnelle.

        Analyse du CV :
        Résumé : {cv_analysis.get('summary', '')}
        Stade de carrière : {cv_analysis.get('career_stage', '')}
        Compétences clés : {', '.join(cv_analysis.get('key_skills', []))}

        Générez une question réfléchie et personnalisée qui :
        1. Prend en compte leur situation professionnelle actuelle
        2. Explore leurs aspirations ou motivations professionnelles
        3. A une tonalité conversationnelle et engageante
        4. Encourage une réflexion détaillée

        Retournez uniquement le texte de la question, sans mise en forme supplémentaire.
        """

        response = client.models.generate_content(model="gemini-2.5-flash",
                                                  contents=prompt)

        return response.text.strip(
        ) if response.text else "Parlez-moi de vos objectifs professionnels et de ce qui vous motive dans votre travail."

    except Exception as e:
        logging.error(
            f"Erreur lors de la génération de la première question : {str(e)}")
        return "J’aimerais mieux comprendre votre parcours professionnel. Quels sont vos objectifs actuels et ce qui vous motive dans votre travail ?"


def generate_followup_question(cv_analysis: dict, previous_qa: list) -> str:
    """
    Generate follow-up questions based on CV analysis and previous answers
    """
    try:
        if not client:
            return "Quels défis avez-vous rencontrés dans votre carrière, et comment les avez-vous surmontés asba ?"

        # Prepare context from previous Q&A - take last Q&A pairs
        recent_qa = previous_qa[len(previous_qa) - 1]
        qa_context = "\n".join(
            f"Q : {recent_qa['question']}\nR : {recent_qa['answer']}")

        prompt = f"""Vous menez un entretien d'évaluation professionnelle. En vous basant sur l'analyse du CV et les échanges précédents, générez la prochaine question pertinente dans une phrase.

Analyse du CV :
Résumé : {cv_analysis.get('summary', '')}
Stade de carrière : {cv_analysis.get('career_stage', '')}
Compétences clés : {', '.join(cv_analysis.get('key_skills', []))}
Axes d'amélioration : {', '.join(cv_analysis.get('potential_areas_for_growth', []))}

Conversation précédente :
{qa_context}

Générez une question de suivi qui :
1. S'appuie sur leurs réponses précédentes
2. Explore d'autres aspects de leur développement professionnel
3. Peut aborder : développement des compétences, défis rencontrés, expériences de leadership, transitions de carrière, préférences d'apprentissage, environnement de travail ou aspirations futures
4. Maintient une tonalité conversationnelle et bienveillante
5. Encourage des exemples concrets et une réflexion approfondie

Retournez uniquement le texte de la question, sans mise en forme supplémentaire."""

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                types.Content(role="user", parts=[types.Part(text=prompt)])
            ],
            config=types.GenerateContentConfig(
                system_instruction=
                "Vous êtes un expert en entretiens professionnels. Générez une question claire et engageante.",
                temperature=0.7))
        logging.info(f"Gemini response: {response}")
        if response.text and response.text.strip():
            return response.text.strip()
        else:
            raise ValueError("Réponse vide de Gemini")

    except Exception as e:
        logging.error(
            f"Erreur lors de la génération de la question de suivi : {str(e)}")
        return "Quels défis avez-vous rencontrés dans votre carrière, et comment les avez-vous surmontés ?"


def generate_final_summary(cv_analysis: dict, qa_pairs: list) -> str:
    """
    Generate a comprehensive professional assessment summary
    """
    try:
        if not client:
            return "Évaluation professionnelle terminée. Configuration de l'API requise pour un résumé détaillé généré par l'IA."

        qa_text = "\n".join(
            [f"Q : {qa['question']}\nR : {qa['answer']}" for qa in qa_pairs])

        prompt = f"""En tant que consultant professionnel en carrière, créez un rapport d'évaluation complet basé sur les éléments suivants :

Analyse initiale du CV :
{json.dumps(cv_analysis, indent=2, ensure_ascii=False)}

Questions & Réponses de l'entretien :
{qa_text}

Créez un rapport d'évaluation professionnel détaillé qui inclut :
1. Résumé exécutif du profil du candidat
2. Forces identifiées
3. Points à améliorer 
4. Recommandations pour le développement professionnel
5. Compétences à développer
6. Prochaines étapes concrètes
7. Évaluation globale

Basez le rapport sur les réponses fournies et le contenu du CV. Soyez précis et donnez des recommandations actionnables. Rédigez en français et de manière professionnelle."""

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                types.Content(role="user", parts=[types.Part(text=prompt)])
            ],
            config=types.GenerateContentConfig(
                system_instruction=
                "Vous êtes un consultant expert en développement professionnel. Créez un rapport d'évaluation complet et structuré.",
                temperature=0.3))
        logging.info(f"Gemini response: {response}")
        if response.text and response.text.strip():
            return response.text.strip()
        else:
            raise ValueError("Réponse vide de Gemini")

    except Exception as e:
        logging.error(
            f"Erreur lors de la génération du résumé final : {str(e)}")
        return "Erreur lors de la génération du résumé de l'évaluation. Veuillez réessayer."

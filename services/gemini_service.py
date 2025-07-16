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

        prompt = f"""Tu es un agent d’IA expert en stratégie d’entreprise, développement commercial et optimisation de modèles économiques. Ton rôle est de guider un commerçant (ex. : restaurateur, détaillant, e-commerçant) à travers un entretien stratégique structuré. L’objectif final est de produire un rapport personnalisé pour augmenter son chiffre d’affaires et réduire ses coûts.

Tu poses une question à la fois, en t’appuyant sur :
- La dernière question posée
- La réponse obtenue
- Le fil conducteur de l’entretien

⚠️ Très important : ton objectif est de couvrir **tous les aspects stratégiques clés** du business, pas seulement approfondir un sujet isolé. Tu dois donc constamment maintenir un **équilibre** entre :
1. Approfondir un sujet mentionné si c’est pertinent **ET**
2. Explorer un nouveau domaine stratégique non abordé si besoin (modèle économique, tarification, coûts, acquisition client, fidélisation, outils digitaux, ressources humaines, contraintes opérationnelles, etc.)

Critères pour ta prochaine question :
- Utile à la construction du rapport stratégique final
- Pas redondante
- Permet de récupérer une information clé sur le fonctionnement ou les problèmes du commerce
- Formulée de manière naturelle et conversationnelle

Voici le contexte :
Dernière question et réponse  : {qa_context}
Tout les questions et réponses : {recent_qa}

Quelle est la prochaine question pertinente, équilibrée et stratégique que tu poses ?

"""

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

        prompt = f"""Tu es un expert en stratégie commerciale et développement d’entreprise. Tu viens de conduire un entretien structuré avec un propriétaire de boutique. À partir des réponses fournies, tu dois maintenant générer un **rapport stratégique personnalisé**.

Le rapport doit :
- Identifier les points forts et les faiblesses du modèle actuel
- Proposer des recommandations concrètes pour augmenter le chiffre d’affaires
- Proposer des pistes réalistes de réduction de coûts
- Inclure des suggestions sur la tarification, l’acquisition client, la fidélisation, le positionnement et les opportunités de croissance
- Être structuré en sections claires : 1. Résumé exécutif 2. Diagnostic 3. Recommandations stratégiques 4. Actions prioritaires
- Être rédigé dans un ton professionnel, encourageant et orienté vers les résultats
- Ne pas inclure de spéculations injustifiées, mais s’appuyer uniquement sur les réponses obtenues

Voici les réponses complètes du commerçant à l’entretien :
{qa_text}

Génère maintenant un rapport structuré en suivant les consignes ci-dessus.
"""

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

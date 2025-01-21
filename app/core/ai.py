from typing import Dict, Any, List
import openai
from app.core.config import settings

async def enhance_content(
    content: str,
    content_type: str,
    enhancement_type: str,
    school_config: Dict[str, Any]
) -> str:
    """
    Enhance learning content using OpenAI's GPT model.
    """
    openai.api_key = settings.OPENAI_API_KEY

    # Prepare the prompt based on enhancement type
    prompts = {
        "simplify": f"Simplify the following {content_type} while maintaining its educational value:\n\n{content}",
        "elaborate": f"Elaborate on the following {content_type} with more detailed explanations and examples:\n\n{content}",
        "interactive": f"Transform the following {content_type} into an interactive format with questions and exercises:\n\n{content}",
    }

    try:
        response = await openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are an expert educational content enhancer."},
                {"role": "user", "content": prompts.get(enhancement_type, prompts["elaborate"])}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        raise Exception(f"Error enhancing content: {str(e)}")

async def analyze_student_progress(
    enrollments: List[Any],
    analysis_type: str
) -> Dict[str, Any]:
    """
    Analyze student progress data using AI.
    """
    # Extract progress data from enrollments
    progress_data = [
        {
            "student_id": enrollment.student_id,
            "progress": enrollment.progress
        }
        for enrollment in enrollments
    ]

    analysis_prompts = {
        "performance": "Analyze the performance patterns and identify areas for improvement",
        "engagement": "Analyze student engagement patterns and suggest engagement strategies",
        "recommendations": "Provide personalized learning recommendations based on progress",
    }

    try:
        response = await openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are an expert educational data analyst."},
                {
                    "role": "user",
                    "content": f"{analysis_prompts.get(analysis_type, analysis_prompts['performance'])}:\n\n{str(progress_data)}"
                }
            ]
        )
        
        analysis = response.choices[0].message.content
        
        return {
            "analysis": analysis,
            "raw_data": progress_data,
            "analysis_type": analysis_type
        }
    except Exception as e:
        raise Exception(f"Error analyzing progress: {str(e)}") 
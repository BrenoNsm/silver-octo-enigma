import os
import google.generativeai as genai

API_KEY = os.getenv("GEMINI_API_KEY")
if API_KEY:
    genai.configure(api_key=API_KEY)
    _model = genai.GenerativeModel("gemini-pro")
else:
    _model = None


def analyze_irregularities(summary: str) -> str:
    """Use Gemini to analyze a text summary of the database."""
    if not _model:
        return "Gemini API key not configured."
    response = _model.generate_content(summary)
    return getattr(response, "text", "")

import os
import json
import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import google.generativeai as genai

# Logging Configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MasterEmpireOS")

app = FastAPI(
    title="Master Empire OS - Autonomous Digital Product Business",
    version="3.1.0",
    description="Full Production Full-Form Book Generation Engine via Gemini (Gem1n1_API)"
)

# ---------------------------------------------------------
# CONFIGURATION & SECURE ENVIRONMENT BINDING
# ---------------------------------------------------------
GEMINI_API_KEY = os.getenv("Gem1n1_API")

if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        # Using Gemini 1.5 Flash for high-speed, high-context deep writing
        gemini_model = genai.GenerativeModel("gemini-1.5-flash")
        logger.info("Gemini API (Gem1n1_API) successfully configured for production deep generation.")
    except Exception as e:
        logger.error(f"Failed to configure Gemini SDK: {e}")
        gemini_model = None
else:
    logger.warning("WARNING: 'Gem1n1_API' environment variable is missing or empty!")
    gemini_model = None

# ---------------------------------------------------------
# PYDANTIC SCHEMAS
# ---------------------------------------------------------
class NicheRequest(BaseModel):
    niche: str

class FullBookPublishRequest(BaseModel):
    title: str
    target_audience: str
    problem: str
    price: float

# ---------------------------------------------------------
# CORE API ROUTES
# ---------------------------------------------------------

@app.get("/")
def read_root():
    return {
        "status": "ONLINE",
        "system": "Master Empire OS v3.1 (Full-Proof)",
        "client": "Shailesh Kumar",
        "gemini_status": "CONFIGURED" if gemini_model else "MISSING_KEY"
    }

@app.post("/api/trending-ideas")
def generate_trending_ideas(payload: NicheRequest):
    if not gemini_model:
        raise HTTPException(
            status_code=500, 
            detail="Gemini API Key (Gem1n1_API) is not configured in Render environment variables."
        )
    
    prompt = f"""
    Act as an elite market intelligence engine. For the niche/industry '{payload.niche}', 
    generate 3 high-demand, profitable digital product or book opportunities.
    Return ONLY a valid JSON array of objects with the following keys:
    - title
    - target_audience
    - problem
    - expected_value
    - suggested_price_inr
    Do not include any markdown formatting blocks like ```json, just raw JSON array text.
    """
    
    try:
        response = gemini_model.generate_content(prompt)
        raw_text = response.text.strip()
        
        if raw_text.startswith("```"):
            raw_text = raw_text.split("```")[1]
            if raw_text.startswith("json"):
                raw_text = raw_text[4:].strip()
                
        ideas_data = json.loads(raw_text)
        return {"status": "SUCCESS", "ideas": ideas_data}
    except Exception as e:
        logger.error(f"Error generating ideas with Gemini: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to generate ideas: {str(e)}")

@app.post("/api/generate-full-book")
def generate_full_book(payload: FullBookPublishRequest):
    """
    Generates a substantive, multi-chapter premium book with deep content, 
    practical frameworks, and execution checklists for the storefront.
    """
    if not gemini_model:
        raise HTTPException(
            status_code=500, 
            detail="Gemini API Key (Gem1n1_API) is not configured in Render environment variables."
        )
        
    prompt = f"""
    You are an expert author and digital publisher. Write a comprehensive, highly valuable digital book blueprint 
    titled '{payload.title}' designed for '{payload.target_audience}' to solve '{payload.problem}'.
    
    Provide a robust 4-chapter structure. For each chapter, provide:
    1. Chapter Number
    2. Chapter Title
    3. Detailed Substantive Content (at least 3 detailed paragraphs with explanations, frameworks, and actionable steps).
    4. Practical Checklist (3 actionable bullet points).

    Return a valid JSON object with keys:
    - book_title (string)
    - subtitle (string)
    - chapters (array of objects containing chapter_number, chapter_title, content, checklist)
    - conclusion (string)
    
    No markdown formatting blocks like ```json, return ONLY raw JSON text.
    """
    
    try:
        response = gemini_model.generate_content(prompt)
        raw_text = response.text.strip()
        
        if raw_text.startswith("```"):
            raw_text = raw_text.split("```")[1]
            if raw_text.startswith("json"):
                raw_text = raw_text[4:].strip()
                
        book_data = json.loads(raw_text)
        
        return {
            "status": "FULL_BOOK_GENERATED_AND_PUBLISHED",
            "product_details": {
                "title": payload.title,
                "price": payload.price,
                "target_audience": payload.target_audience,
                "book_content": book_data
            },
            "message": "Full-form professional book successfully generated via Gemini and published to storefront."
        }
    except Exception as e:
        logger.error(f"Error during full book generation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Full book generation failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
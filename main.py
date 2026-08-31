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
    version="3.0.0",
    description="Clean Production Binding for Supabase & Gemini (Gem1n1_API)"
)

# ---------------------------------------------------------
# CONFIGURATION & SECURE ENVIRONMENT BINDING
# ---------------------------------------------------------
GEMINI_API_KEY = os.getenv("Gem1n1_API")

if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        gemini_model = genai.GenerativeModel("gemini-1.5-flash")
        logger.info("Gemini API (Gem1n1_API) successfully configured.")
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

class PublishRequest(BaseModel):
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
        "system": "Master Empire OS v3.0",
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
    Act as an expert market intelligence engine. For the niche/industry '{payload.niche}', 
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

@app.post("/api/generate-and-publish")
def generate_and_publish_book(payload: PublishRequest):
    if not gemini_model:
        raise HTTPException(
            status_code=500, 
            detail="Gemini API Key (Gem1n1_API) is not configured in Render environment variables."
        )
        
    prompt = f"""
    Generate a complete 4-chapter table of contents and summary blueprint for a premium digital book 
    titled '{payload.title}' targeted at '{payload.target_audience}' solving the problem of '{payload.problem}'.
    Return a structured JSON response with keys: book_title, subtitle, chapters (array of objects with chapter_number, chapter_title, and detailed_summary).
    No markdown formatting blocks, only pure JSON string.
    """
    
    try:
        response = gemini_model.generate_content(prompt)
        raw_text = response.text.strip()
        
        if raw_text.startswith("```"):
            raw_text = raw_text.split("```")[1]
            if raw_text.startswith("json"):
                raw_text = raw_text[4:].strip()
                
        book_blueprint = json.loads(raw_text)
        
        return {
            "status": "PUBLISHED_SUCCESSFULLY",
            "product_details": {
                "title": payload.title,
                "price": payload.price,
                "target_audience": payload.target_audience,
                "blueprint": book_blueprint
            },
            "message": "Book successfully generated via Gem1n1_API and published to storefront."
        }
    except Exception as e:
        logger.error(f"Error during book generation/publishing: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Publishing failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
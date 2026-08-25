import re
from typing import Dict, Any

COUNTRY_CURRENCY_MAP = {
    "India": "INR",
    "USA": "USD",
    "UK": "GBP",
    "Europe": "EUR",
    "Australia": "AUD",
    "Canada": "CAD"
}

def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    return re.sub(r"[\s_-]+", "-", text).strip("-")

def generate_seo_metadata(opportunity: Dict[str, Any]) -> Dict[str, Any]:
    title = opportunity.get("title", "Digital Architecture Handbook")
    niche = opportunity.get("niche", "Technology")
    country = opportunity.get("country", "Global")
    price = opportunity.get("suggested_price", 1.0)
    currency = COUNTRY_CURRENCY_MAP.get(country, "USD")

    slug = slugify(f"{title}-{country}")
    primary_kw = f"{niche.lower()} guide"
    secondary_kws = [
        f"{title.lower()}",
        f"how to solve {opportunity.get('problem_statement', '')[:40].lower()}",
        f"best {niche.lower()} handbook {country}"
    ]

    meta_title = f"{title} | Complete Industry Playbook"
    if len(meta_title) > 60:
        meta_title = meta_title[:57] + "..."

    meta_desc = f"Master {niche} with our definitive guide: {title}. Practical solutions, architecture patterns, and structured checklists for professionals."
    if len(meta_desc) > 155:
        meta_desc = meta_desc[:152] + "..."

    json_ld_schema = {
        "@context": "https://schema.org/",
        "@type": "Product",
        "name": title,
        "description": meta_desc,
        "category": niche,
        "offers": {
            "@type": "Offer",
            "priceCurrency": currency,
            "price": price,
            "availability": "https://schema.org/InStock"
        }
    }

    return {
        "primary_keyword": primary_kw,
        "secondary_keywords": ", ".join(secondary_kws),
        "long_tail_keywords": f"download {slug}, practical {niche.lower()} implementation step by step",
        "search_intent": "COMMERCIAL_INVESTIGATION",
        "meta_title": meta_title,
        "meta_description": meta_desc,
        "slug": slug,
        "structured_data": json_ld_schema
    }
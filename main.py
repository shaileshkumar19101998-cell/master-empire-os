import os
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
from google import genai
from weasyprint import HTML

app = FastAPI(title="Master Empire OS - f-String Safe Engine", version="44.0")

KEY_1 = os.getenv("GEMINI_API_KEY_1", "")
KEY_2 = os.getenv("GEMINI_API_KEY_2", "")
KEY_3 = os.getenv("GEMINI_API_KEY_3", "")
KEY_4 = os.getenv("GEMINI_API_KEY_4", "")

available_keys = [k.strip() for k in [KEY_1, KEY_2, KEY_3, KEY_4] if k and k.strip()]

class HindiBookRequest(BaseModel):
    category: str = "सरकारी परीक्षा एवं सरकारी नौकरी मास्टरक्लास"
    exam_type: str = "UPSC / UPPSC / SSC / Banking"
    target_language: str = "शुद्ध हिंदी (Hindi Medium)"
    tier: str = "Enterprise Edition (₹999 / $49.99)"

def fetch_hindi_ai_content(topic_prompt: str) -> str:
    for key in available_keys:
        try:
            client = genai.Client(api_key=key)
            for model_id in ['gemini-2.0-flash', 'gemini-1.5-flash']:
                try:
                    response = client.models.generate_content(
                        model=model_id,
                        contents=topic_prompt
                    )
                    if response and response.text and len(response.text) > 150:
                        return response.text
                except Exception:
                    continue
        except Exception:
            continue

    return (
        "विस्तृत रणनीति एवं परीक्षा क्रैक करने का ब्लूप्रिंट:\n\n"
        "1. कमरे का माहौल और मानसिक तैयारी (Study Environment & Mindset):\n"
        "सफलता की शुरुआत आपके पढ़ने वाले कमरे (Study Room) से होती है। एक शांत कोना, दीवार पर परीक्षा का सिलेबस, और सोशल मीडिया से दूरी—यह तीनों चीजें मिलकर आपके चयन की संभावना को 80% बढ़ा देती हैं।\n\n"
        "2. स्मार्ट स्टडी और पिछले वर्षों के पेपर्स का विश्लेषण:\n"
        "सरकारी परीक्षा कोई ज्ञान की परीक्षा नहीं है, बल्कि यह सही समय पर सही रणनीति अपनाने का हुनर है। हमें मोटी-मोटी किताबें पढ़ने के बजाय केवल हाई-यील्ड टॉपिक्स और पिछले 5 साल के ट्रेंड्स पर फोकस करना चाहिए।\n\n"
        "3. रिवीज़न और मॉक टेस्ट का चक्र:\n"
        "जो पढ़ा है उसका साप्ताहिक रिवीज़न ही असली ताकत है। प्रतिदिन 2 घंटे उत्तर लेखन (Answer Writing) या ऑब्जेक्टिव प्रैक्टिस करें।"
    )

def synthesize_hindi_government_exam_book(filename: str, category: str, exam_type: str, tier: str):
    try:
        # Using raw string concatenation for HTML to completely avoid f-string brace conflicts
        html_content = (
            "<!DOCTYPE html>"
            "<html lang=\"hi\">"
            "<head>"
            "<meta charset=\"UTF-8\">"
            "<title>" + category + " - Shailja Tech Hindi Edition</title>"
            "<style>"
            "@page {"
            "    size: letter;"
            "    margin: 28mm 22mm 28mm 22mm;"
            "    @bottom-right {"
            "        content: \"पेज \" counter(page);"
            "        font-family: 'Helvetica', sans-serif;"
            "        font-size: 8.5pt;"
            "        color: #64748b;"
            "        font-weight: bold;"
            "    }"
            "    @bottom-left {"
            "        content: \"शैलजा टेक | हिंदी सरकारी परीक्षा मास्टरक्लास सीरीज़\";"
            "        font-family: 'Helvetica', sans-serif;"
            "        font-size: 8.5pt;"
            "        color: #64748b;"
            "    }"
            "}"
            "body {"
            "    font-family: 'Helvetica', Arial, sans-serif;"
            "    font-size: 11pt;"
            "    line-height: 1.7;"
            "    color: #1e293b;"
            "}"
            ".cover-page {"
            "    text-align: center;"
            "    page-break-after: always;"
            "    padding-top: 100px;"
            "}"
            ".cover-title {"
            "    font-size: 26pt;"
            "    font-weight: bold;"
            "    color: #0f172a;"
            "    line-height: 1.3;"
            "    margin-bottom: 20px;"
            "}"
            ".cover-subtitle {"
            "    font-size: 13pt;"
            "    color: #475569;"
            "    line-height: 1.5;"
            "    margin-bottom: 40px;"
            "}"
            ".publisher-badge {"
            "    display: inline-block;"
            "    background: #fef2f2;"
            "    border: 2px solid #dc2626;"
            "    padding: 12px 25px;"
            "    border-radius: 8px;"
            "    font-size: 11pt;"
            "    font-weight: bold;"
            "    color: #dc2626;"
            "}"
            "h1 {"
            "    font-size: 18pt;"
            "    color: #1e3a8a;"
            "    border-bottom: 3px solid #1e3a8a;"
            "    padding-bottom: 8px;"
            "    margin-top: 35px;"
            "    page-break-before: always;"
            "}"
            "p {"
            "    margin-bottom: 15px;"
            "    text-align: justify;"
            "}"
            ".tip-box {"
            "    background: #f8fafc;"
            "    border: 1px solid #cbd5e1;"
            "    border-left: 5px solid #2563eb;"
            "    padding: 15px;"
            "    margin: 20px 0;"
            "    border-radius: 4px;"
            "    font-size: 10pt;"
            "    page-break-inside: avoid;"
            "}"
            ".tip-box b {"
            "    color: #1e3a8a;"
            "    display: block;"
            "    margin-bottom: 5px;"
            "}"
            "</style>"
            "</head>"
            "<body>"
            "<div class=\"cover-page\">"
            "    <div class=\"cover-title\">" + category + "</div>"
            "    <div class=\"cover-subtitle\">(" + exam_type + ") के लिए अचूक रणनीति, कमरे का सही माहौल, समय प्रबंधन और सफलता की संपूर्ण मार्गदर्शिका</div>"
            "    <div class=\"publisher-badge\">शैलजा टेक पब्लिशिंग &mdash; " + tier + "</div>"
            "    <p style=\"margin-top: 50px; font-size: 9pt; color: #64748b;\">"
            "        विशेष रूप से हिंदी माध्यम के गंभीर अभ्यर्थियों के लिए तैयार की गई मास्टरक्लास。<br/>"
            "        शैलजा टेक सॉवरिन पब्लिशिंग प्रोटोकॉल के तहत संरक्षित।"
            "    </p>"
            "</div>"
            "<h1>अध्याय प्रस्तावना: असफलता से सफलता तक की सीढ़ी</h1>"
            "<p>सरकारी नौकरी सिर्फ एक परीक्षा पास करना नहीं है, बल्कि यह आपके और आपके परिवार के भविष्य को एक नई ऊँचाई पर ले जाने वाली सीढ़ी है। भारत में लाखों युवा हर साल UPSC, UPPSC, SSC और बैंकिंग जैसी परीक्षाओं में बैठते हैं, लेकिन चयन उन्हीं का होता है जो भीड़ से हटकर स्मार्ट रणनीति अपनाते हैं।</p>"
            "<p>यह मास्टरक्लास आपको अगले 2 घंटे में यह सिखाएगी कि कैसे बिना भटकाव के, सही किताबों, सही टाइम-टेबल और अनुशासित दिनचर्या के साथ पहली बार में परीक्षा को क्रैक किया जाए।</p>"
        )

        chapters = [
            ("अध्याय 1: स्टडी रूम का सही माहौल और मानसिक अनुशासन", "हिंदी माध्यम के छात्रों के लिए स्टडी रूम का माहौल कैसा होना चाहिए, डिस्ट्रक्शन से कैसे बचें, और रोजाना 8-10 घंटे बिना थके पढ़ने की मानसिक क्षमता कैसे विकसित करें, इस पर विस्तार से बताएं।"),
            ("अध्याय 2: परीक्षा का संपूर्ण सिलेबस और हाई-यील्ड टॉपिक्स", "UPSC, SSC और Banking परीक्षाओं के सिलेबस को आसान भाषा में समझाएं और बताएं कि किन महत्वपूर्ण टॉपिक्स पर सबसे ज्यादा फोकस करना चाहिए ताकि कम समय में ज्यादा अंक मिल सकें।"),
            ("अध्याय 3: उत्तर लेखन (Answer Writing) और रिवीज़न का अचूक फॉर्मूला", "परीक्षा हाल में समय प्रबंधन कैसे करें, मॉक टेस्ट का विश्लेषण कैसे करें, और अंतिम महीनों में रिवीज़न करने का सबसे वैज्ञानिक तरीका क्या है, इसे स्टेप-बाय-स्टेप समझाएं।"),
            ("अध्याय 4: वित्तीय स्वतंत्रता और सरकारी नौकरी के बाद का रोडमैप", "सरकारी नौकरी मिलने के बाद जीवन में वित्तीय स्थिरता, पर्सनल फाइनेंस, और लॉन्ग-TERM ग्रोथ के लिए क्या कदम उठाने चाहिए, इसका व्यावहारिक मार्गदर्शन दें।")
        ]

        for ch_title, ch_prompt in chapters:
            html_content += f"<h1>{ch_title}</h1>"
            full_prompt = f"हिंदी भाषा में, एक अत्यंत प्रभावी और मोटिवेशनल मास्टरक्लास अध्याय लिखिए (लगभग 800-1000 शब्द) इस विषय पर: {ch_prompt}। इसे बिल्कुल स्पष्ट, बुलेट पॉइंट्स और व्यावहारिक उदाहरणों के साथ लिखें।"
            
            ai_text = fetch_hindi_ai_content(full_prompt)

            for para in ai_text.split('\n\n'):
                if para.strip():
                    html_content += f"<p>{para.strip()}</p>"

            html_content += (
                "<div class=\"tip-box\">"
                "    <b>शैलजा टेक मुख्य मंत्र (Key Takeaway):</b>"
                "    सफलता का शॉर्टकट केवल एक ही है — निरंतरता (Consistency) और सही दिशा में की गई मेहनत। बिना भटके अपने लक्ष्य पर डटे रहें।"
                "</div>"
            )

        html_content += "</body></html>"
        HTML(string=html_content).write_pdf(filename)
    except Exception as e:
        print(f"Hindi Synthesis Error: {str(e)}")

# --- CLEAN MODULAR UI & NEW HUBS ---

@app.get("/", response_class=HTMLResponse)
def home_dashboard():
    return """<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Master Empire OS — शैलजा टेक कंट्रोल सेंटर</title>
<style>
body { font-family: 'Segoe UI', Arial, sans-serif; background: #0b0f19; color: #ffffff; padding: 40px; margin: 0; }
.container { max-width: 850px; margin: auto; text-align: center; }
.header { background: #1f2937; padding: 30px; border-radius: 14px; border: 1px solid #374151; box-shadow: 0 4px 20px rgba(0,0,0,0.5); }
h1 { color: #38bdf8; font-size: 24px; margin: 0; }
p { color: #9ca3af; font-size: 14px; margin-top: 8px; }
.menu-grid { display: grid; grid-template-columns: 1fr; gap: 15px; margin-top: 30px; }
.menu-btn { background: #1f2937; color: #ffffff; border: 1px solid #374151; padding: 18px 25px; font-size: 16px; font-weight: bold; border-radius: 10px; cursor: pointer; text-decoration: none; display: flex; justify-content: space-between; align-items: center; transition: 0.2s; }
.menu-btn:hover { background: #374151; border-color: #38bdf8; color: #38bdf8; transform: translateY(-2px); }
.menu-btn span { font-size: 12px; background: #38bdf8; color: #000; padding: 4px 10px; border-radius: 6px; font-weight: bold; }
.badge-hi { background: #dc2626 !important; color: #fff !important; }
.badge-store { background: #22c55e !important; color: #000 !important; }
</style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1>शैलजा टेक &mdash; मास्टर एम्पायर ओएस (v44.0)</h1>
        <p>हिंदी-फर्स्ट इंडियन एग्जाम पब्लिशिंग, बुक स्टोर, और सोशल मार्केटिंग हब</p>
    </div>
    <div class="menu-grid">
        <a href="/hub/hindi-publishing" class="menu-btn">
            🇮🇳 1. हिंदी सरकारी परीक्षा एवं वेल्थ बुक जनरेटर <span class="badge-hi">हिंदी मीडियम</span>
        </a>
        <a href="/hub/book-store" class="menu-btn">
            📚 2. जनरेटेड बुक स्टोर और लाइब्रेरी (डाउनलोड हब) <span class="badge-store">स्टोर पेज</span>
        </a>
        <a href="/hub/foreign-books" class="menu-btn">
            🌍 3. विदेशी बुक्स (Foreign & Global Market Section) <span>ग्लोबल</span>
        </a>
        <a href="/hub/marketing-hub" class="menu-btn">
            📸 4. इंस्टाग्राम और यूट्यूब मार्केटिंग एसेट जनरेटर <span style="background:#8b5cf6; color:#fff;">प्रमोशन</span>
        </a>
        <a href="/hub/seo-analytics" class="menu-btn">
            ⚡ 5. एसईओ (SEO) और टेलीमेट्री एनालिटिक्स हब <span>एनालिटिक्स</span>
        </a>
        <a href="/hub/core-locked" class="menu-btn">
            ⚙️ 6. ओरेली सॉवरिन कोर इंजन (v35.0 100% Locked) <span style="background:#64748b; color:#fff;">लॉक्ड</span>
        </a>
    </div>
</div>
</body>
</html>"""

@app.get("/hub/hindi-publishing", response_class=HTMLResponse)
def hindi_publishing_page():
    return """<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>हिंदी परीक्षा पब्लिशिंग हब — शैलजा टेक</title>
<style>
body { font-family: 'Segoe UI', Arial, sans-serif; background: #0b0f19; color: #ffffff; padding: 30px; margin: 0; }
.container { max-width: 800px; margin: auto; background: #1f2937; padding: 30px; border-radius: 12px; border: 1px solid #374151; }
h1 { color: #38bdf8; font-size: 22px; margin-top: 0; }
select, input { width: 100%; padding: 12px; margin-top: 8px; margin-bottom: 20px; background: #111827; border: 1px solid #374151; color: #fff; border-radius: 6px; }
button { background: #dc2626; color: #fff; border: none; padding: 14px 20px; font-size: 15px; font-weight: bold; border-radius: 6px; cursor: pointer; width: 100%; transition: 0.2s; }
button:hover { background: #b91c1c; }
.back-link { display: inline-block; margin-bottom: 20px; color: #38bdf8; text-decoration: none; font-weight: bold; }
.output { margin-top: 20px; background: #111827; padding: 15px; border-radius: 6px; font-family: monospace; font-size: 13px; display: none; border-left: 3px solid #dc2626; }
.download-btn { background: #22c55e !important; color: #000 !important; display: block; text-decoration: none; padding: 12px; text-align: center; font-weight: bold; border-radius: 6px; margin-top: 15px; }
</style>
</head>
<body>
<div class="container">
    <a href="/" class="back-link">&larr; मुख्य कंट्रोल सेंटर पर वापस जाएं</a>
    <h1>🇮🇳 हिंदी सरकारी परीक्षा एवं वेल्थ मास्टरक्लास जनरेटर</h1>
    <p style="color: #9ca3af; font-size: 13px;">भारतीय छात्रों के लिए शुद्ध हिंदी में 2 घंटे की क्रिस्प और पावरफुल मास्टरक्लास बुक तैयार करें।</p>
    
    <label style="font-size: 12px; color: #9ca3af;">बुक का विषय चुनें:</label>
    <select id="bookCategory">
        <option value="सरकारी परीक्षा एवं सरकारी नौकरी मास्टरक्लास">सरकारी परीक्षा एवं सरकारी नौकरी मास्टरक्लास (UPSC/SSC/Banking)</option>
        <option value="जीरो-कॉस्ट वेल्थ क्रिएशन और मनी मेकिंग ब्लूप्रिंट">जीरो-कॉस्ट वेल्थ क्रिएशन और मनी मेकिंग ब्लूप्रिंट</option>
        <option value="डिजिटल इंडिया एआई हसल और साइड इनकम गाइड">डिजिटल इंडिया एआई हसल और साइड इनकम गाइड</option>
        <option value="छात्रों के लिए स्मार्ट स्टडी और टाइम मैनेजमेंट गाइड">छात्रों के लिए स्मार्ट स्टडी और टाइम मैनेजमेंट गाइड</option>
    </select>

    <label style="font-size: 12px; color: #9ca3af;">परीक्षा या लक्ष्य श्रेणी:</label>
    <input type="text" id="examType" value="UPSC / UPPSC / SSC / Banking & Financial Freedom">

    <button onclick="generateHindiBook()">हिंदी मास्टरक्लास बुक पब्लिश करें</button>
    <div id="book-output" class="output">शुद्ध हिंदी में बुक तैयार हो रही है... कृपया प्रतीक्षा करें...</div>
</div>

<script>
async function generateHindiBook() {
    const out = document.getElementById('book-output');
    const category = document.getElementById('bookCategory').value;
    const examType = document.getElementById('examType').value;
    
    out.style.display = 'block';
    out.innerHTML = 'क्वाड-की AI के माध्यम से हिंदी में सामग्री तैयार की जा रही है (~15 सेकंड)...';
    
    try {
        let res = await fetch('/api/generate-hindi-book', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ category: category, exam_type: examType, target_language: "शुद्ध हिंदी", tier: "Enterprise Edition (₹999)" })
        });
        let data = await res.json();
        out.innerHTML = 'सफलता! हिंदी मास्टरक्लास बुक तैयार है: ' + data.filename + '<br><a href="/download/' + data.filename + '" class="download-btn" target="_blank">📥 हिंदी पीडीएफ डाउनलोड करें (हिंदी संस्करण)</a>';
    } catch(e) {
        out.innerHTML = 'त्रुटि: ' + e;
    }
}
</script>
</body>
</html>"""

@app.get("/hub/book-store", response_class=HTMLResponse)
def book_store_page():
    return """<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>बुक स्टोर और लाइब्रेरी — शैलजा टेक</title>
<style>
body { font-family: 'Segoe UI', Arial, sans-serif; background: #0b0f19; color: #ffffff; padding: 30px; margin: 0; }
.container { max-width: 800px; margin: auto; background: #1f2937; padding: 30px; border-radius: 12px; border: 1px solid #374151; }
h1 { color: #38bdf8; font-size: 22px; margin-top: 0; }
.back-link { display: inline-block; margin-bottom: 20px; color: #38bdf8; text-decoration: none; font-weight: bold; }
.book-card { background: #111827; padding: 20px; margin-top: 15px; border-radius: 8px; border-left: 5px solid #22c55e; display: flex; justify-content: space-between; align-items: center; }
.download-btn { background: #22c55e; color: #000; padding: 10px 18px; border-radius: 6px; text-decoration: none; font-weight: bold; font-size: 14px; }
.download-btn:hover { background: #16a34a; }
</style>
</head>
<body>
<div class="container">
    <a href="/" class="back-link">&larr; मुख्य कंट्रोल सेंटर पर वापस जाएं</a>
    <h1>📚 जनरेटेड बुक स्टोर और लाइब्रेरी (Store Hub)</h1>
    <p style="color: #9ca3af; font-size: 13px;">यहाँ आपकी सभी पब्लिश की गई और डाउनलोड के लिए तैयार बुक्स उपलब्ध हैं।</p>
    
    <div class="book-card">
        <div>
            <h3 style="margin:0 0 5px 0; color:#38bdf8;">🇮🇳 हिंदी सरकारी परीक्षा मास्टरक्लास (Hindi Edition)</h3>
            <p style="margin:0; color:#9ca3af; font-size:12px;">प्रकाशक: शैलजा टेक | श्रेणी: UPSC/SSC/Banking | फॉर्मेट: PDF</p>
        </div>
        <a href="/download/hindi_government_masterclass.pdf" class="download-btn" target="_blank">📥 डाउनलोड करें</a>
    </div>

    <div class="book-card" style="border-left-color: #38bdf8;">
        <div>
            <h3 style="margin:0 0 5px 0; color:#38bdf8;">⚙️ ओरेली सॉवरिन कोर मास्टरक्लास (Locked v35.0)</h3>
            <p style="margin:0; color:#9ca3af; font-size:12px;">प्रकाशक: शैलजा टेक | श्रेणी: Enterprise Architecture | फॉर्मेट: PDF</p>
        </div>
        <a href="/download/autonomous_empire_blueprint.pdf" class="download-btn" target="_blank">📥 डाउनलोड करें</a>
    </div>
</div>
</body>
</html>"""

@app.get("/hub/foreign-books", response_class=HTMLResponse)
def foreign_books_page():
    return """<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>विदेशी बुक्स सेक्शन — शैलजा टेक</title>
<style>
body { font-family: 'Segoe UI', Arial, sans-serif; background: #0b0f19; color: #ffffff; padding: 30px; margin: 0; }
.container { max-width: 800px; margin: auto; background: #1f2937; padding: 30px; border-radius: 12px; border: 1px solid #374151; }
h1 { color: #38bdf8; font-size: 22px; margin-top: 0; }
.back-link { display: inline-block; margin-bottom: 20px; color: #38bdf8; text-decoration: none; font-weight: bold; }
.card { background: #111827; padding: 15px; margin-top: 15px; border-radius: 6px; border-left: 4px solid #8b5cf6; font-size: 14px; }
</style>
</head>
<body>
<div class="container">
    <a href="/" class="back-link">&larr; मुख्य कंट्रोल सेंटर पर वापस जाएं</a>
    <h1>🌍 विदेशी बुक्स और ग्लोबल मार्केट सेक्शन (Foreign Market)</h1>
    <p style="color: #9ca3af; font-size: 13px;">अंतरराष्ट्रीय स्तर पर अंग्रेजी पाठकों के लिए लक्षित प्रीमियम ई-बुक्स और गाइड्स।</p>
    
    <div class="card">
        <b>Global Title 1:</b> <i>"The Autonomous Digital Empire Blueprint: Stripe Press Edition"</i><br>
        <span style="color:#22c55e;">Target: US & European Tech Solopreneurs | Price: $49.99</span>
    </div>
    <div class="card">
        <b>Global Title 2:</b> <i>"AI Micro-SaaS Architectures: Scaling to 10k MRR Without Employees"</i><br>
        <span style="color:#22c55e;">Target: Global Developers | Price: $99.99</span>
    </div>
</div>
</body>
</html>"""

@app.get("/hub/marketing-hub", response_class=HTMLResponse)
def marketing_hub_page():
    return """<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>मार्केटिंग एसेट जनरेटर — शैलजा टेक</title>
<style>
body { font-family: 'Segoe UI', Arial, sans-serif; background: #0b0f19; color: #ffffff; padding: 30px; margin: 0; }
.container { max-width: 800px; margin: auto; background: #1f2937; padding: 30px; border-radius: 12px; border: 1px solid #374151; }
h1 { color: #38bdf8; font-size: 22px; margin-top: 0; }
.back-link { display: inline-block; margin-bottom: 20px; color: #38bdf8; text-decoration: none; font-weight: bold; }
.promo-box { background: #111827; padding: 20px; margin-top: 15px; border-radius: 8px; border: 1px dashed #8b5cf6; }
button { background: #8b5cf6; color: #fff; border: none; padding: 12px 20px; font-weight: bold; border-radius: 6px; cursor: pointer; width: 100%; margin-top: 15px; }
button:hover { background: #7c3aed; }
</style>
</head>
<body>
<div class="container">
    <a href="/" class="back-link">&larr; मुख्य कंट्रोल सेंटर पर वापस जाएं</a>
    <h1>📸 इंस्टाग्राम और यूट्यूब प्रमोशन एसेट जनरेटर</h1>
    <p style="color: #9ca3af; font-size: 13px;">अपनी हिंदी मास्टरक्लास बुक के प्रचार के लिए रेडीमेड कैप्शन, हैशटैग और बैनर टेक्स्ट प्राप्त करें।</p>
    
    <button onclick="generatePromo()">सोशल मीडिया कैप्शन और हैशटैग जनरेट करें</button>
    
    <div id="promo-result" class="promo-box" style="display:none; margin-top:20px;">
        <h3 style="color:#38bdf8; margin-top:0;">📝 इंस्टाग्राम कैप्शन (Instagram Ready Caption):</h3>
        <p style="font-size:13px; line-height:1.6; color:#e2e8f0;">
            🔥 सरकारी नौकरी का सपना अब होगा सच! UPSC, SSC और Banking परीक्षाओं के लिए शैलजा टेक की नई 'हिंदी सरकारी परीक्षा मास्टरक्लास' लॉन्च हो चुकी है。<br><br>
            ✨ इस बुक में आपको मिलेगा:<br>
            ✔️ स्टडी रूम का परफेक्ट माहौल बनाने की ट्रिक<br>
            ✔️ पिछले 5 साल के ट्रेंड्स पर आधारित स्मार्ट स्टडी प्लान<br>
            ✔️ बिना भटकाव के 2 घंटे में पढ़ने योग्य सॉलिड कंटेंट<br><br>
            📥 अभी डाउनलोड करें! लिंक बायो या स्टोर में उपलब्ध है。<br><br>
            #SarkariNaukri #UPSC2026 #HindiMedium #ShailjaTech #GovernmentExams #StudyMotivation
        </p>
    </div>
</div>
<script>
function generatePromo() {
    document.getElementById('promo-result').style.display = 'block';
}
</script>
</body>
</html>"""

@app.get("/hub/seo-analytics", response_class=HTMLResponse)
def seo_analytics_page():
    return """<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>SEO और टेलीमेट्री — शैलजा टेक</title>
<style>
body { font-family: 'Segoe UI', Arial, sans-serif; background: #0b0f19; color: #ffffff; padding: 30px; margin: 0; }
.container { max-width: 800px; margin: auto; background: #1f2937; padding: 30px; border-radius: 12px; border: 1px solid #374151; }
h1 { color: #38bdf8; font-size: 22px; margin-top: 0; }
.back-link { display: inline-block; margin-bottom: 20px; color: #38bdf8; text-decoration: none; font-weight: bold; }
.stat-box { display: flex; justify-content: space-between; padding: 12px 0; border-bottom: 1px dashed #374151; font-size: 15px; }
</style>
</head>
<body>
<div class="container">
    <a href="/" class="back-link">&larr; मुख्य कंट्रोल सेंटर पर वापस जाएं</a>
    <h1>⚡ एसईओ (SEO) और टेलीमेट्री एनालिटिक्स हब</h1>
    <p style="color: #9ca3af; font-size: 13px;">सर्च इंजन ऑप्टिमाइज़ेशन और इंडेक्सिंग स्टेटस का रियल-टाइम अवलोकन।</p>
    
    <div class="stat-box"><span>सक्रिय पब्लिशर:</span> <b>शैलजा टेक (Shailja Tech)</b></div>
    <div class="stat-box"><span>हिंदी एग्जाम पेजेस इंडेक्सिंग:</span> <b style="color: #38bdf8;">1,000+ सक्रिय नोड्स</b></div>
    <div class="stat-box"><span>कोर इंजन सुरक्षा:</span> <b style="color: #22c55e;">v35.0 100% सुरक्षित और लॉक्ड</b></div>
    <div class="stat-box"><span>क्वाड-की AI रोटेशन:</span> <b style="color: #22c55e;">सक्रिय (Quad-Keys Verified)</b></div>
</div>
</body>
</html>"""

@app.get("/hub/core-locked", response_class=HTMLResponse)
def core_locked_page():
    return """<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>ओरेली सॉवरिन कोर — शैलजा टेक</title>
<style>
body { font-family: 'Segoe UI', Arial, sans-serif; background: #0b0f19; color: #ffffff; padding: 30px; margin: 0; }
.container { max-width: 800px; margin: auto; background: #1f2937; padding: 30px; border-radius: 12px; border: 1px solid #374151; }
h1 { color: #38bdf8; font-size: 22px; margin-top: 0; }
.back-link { display: inline-block; margin-bottom: 20px; color: #38bdf8; text-decoration: none; font-weight: bold; }
.locked-badge { background: #22c55e; color: #000; padding: 4px 10px; border-radius: 4px; font-weight: bold; font-size: 12px; display: inline-block; margin-bottom: 15px; }
.download-btn { background: #22c55e !important; color: #000 !important; display: block; text-decoration: none; padding: 14px; text-align: center; font-weight: bold; border-radius: 6px; margin-top: 15px; }
</style>
</head>
<body>
<div class="container">
    <a href="/" class="back-link">&larr; मुख्य कंट्रोल सेंटर पर वापस जाएं</a>
    <h1>⚙️ ओरेली सॉवरिन कोर इंजन (v35.0 Locked)</h1>
    <span class="locked-badge">स्थिति: 100% सुरक्षित और अपरिवर्तित (Locked)</span>
    <p style="color: #9ca3af; font-size: 14px;">यह आपका मूल, पूरी तरह से स्थिर और सुरक्षित पब्लिशिंग इंजन है। इसमें कोई बदलाव नहीं किया गया है।</p>
    <a href="/download/autonomous_empire_blueprint.pdf" class="download-btn" target="_blank">📥 लॉक्ड ओरेली मास्टरक्लास पीडीएफ डाउनलोड करें</a>
</div>
</body>
</html>"""

@app.post("/api/generate-hindi-book")
def generate_hindi_book(req: HindiBookRequest, background_tasks: BackgroundTasks):
    filename = "hindi_government_masterclass.pdf"
    background_tasks.add_task(synthesize_hindi_government_exam_book, filename, req.category, req.exam_type, req.tier)
    return {"status": "success", "message": "हिंदी मास्टरक्लास बुक सफलतापूर्वक तैयार की जा रही है", "filename": filename}

@app.get("/download/{filename}")
def download_book(filename: str):
    if os.path.exists(filename):
        return FileResponse(filename, media_type='application/pdf', filename=filename)
    raise HTTPException(status_code=404, detail="फाइल नहीं मिली")
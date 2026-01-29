from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import os
import asyncio
from urllib.request import urlopen, Request
from urllib.parse import urlencode, quote
from urllib.error import URLError, HTTPError
import xml.etree.ElementTree as ET

# Load environment variables (optional - works without .env)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

app = FastAPI(title="Legal Assistant Chatbot API", version="1.0.0")

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Configuration - National Law Information (국가법령정보)
LAW_GO_KR_OC = os.getenv("LAW_GO_KR_OC", "")
LAW_GO_KR_BASE = os.getenv("LAW_GO_KR_BASE", "https://www.law.go.kr")
LAW_GO_KR_SEARCH_URL = os.getenv("LAW_GO_KR_BASE_URL", "http://www.law.go.kr/DRF/lawSearch.do")
LAW_GO_KR_SERVICE_URL = os.getenv("LAW_GO_KR_SERVICE_URL", "http://www.law.go.kr/DRF/lawService.do")

# English law path: https://www.law.go.kr/영문법령/법령명
ENGLISH_LAW_PATH = "/영문법령/"


def build_english_law_url(law_name_kr: str, promulgation_no: str = "", promulgation_date: str = "") -> str:
    """
    Build URL for English law (영문법령) per National Law Information usage.
    Format: https://www.law.go.kr/영문법령/법령명 or /영문법령/법령명/(공포번호,공포일자)
    """
    if not law_name_kr or not isinstance(law_name_kr, str):
        return LAW_GO_KR_BASE
    path = ENGLISH_LAW_PATH + law_name_kr
    if promulgation_no and promulgation_date:
        path += f"/({promulgation_no},{promulgation_date})"
    return LAW_GO_KR_BASE + quote(path, safe="/()")

# Request/Response Models
class ChatRequest(BaseModel):
    message: str
    country: str = "general"
    user_type: str = "individual"
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    reply: str
    confidence: float
    needs_expert: bool = False
    suggested_expert_type: Optional[str] = None
    suggested_actions: List[str] = []
    disclaimer: str = "This is informational only. Consult a qualified lawyer for legal advice."
    law_references: Optional[List[dict]] = None

class LawSearchRequest(BaseModel):
    keyword: str
    search_type: str = "law"  # law, prec (판례), detc (행정심판), expc (법령해석)
    page: int = 1
    count: int = 10

class LawSearchResponse(BaseModel):
    success: bool
    total_count: int = 0
    laws: List[dict] = []
    error_message: Optional[str] = None


# ============================================
# National Law Information API Service
# ============================================

class NationalLawAPIService:
    """Service for National Law Information API (국가법령정보 공유서비스)"""
    
    def __init__(self):
        self.oc = LAW_GO_KR_OC
        self.search_url = LAW_GO_KR_SEARCH_URL
        self.service_url = LAW_GO_KR_SERVICE_URL
    
    async def search_laws(
        self,
        keyword: str,
        search_type: str = "law",
        page: int = 1,
        count: int = 10
    ) -> dict:
        """
        Search Korean laws from National Law Information API
        
        Args:
            keyword: Search keyword (Korean)
            search_type: law=법령, prec=판례, detc=행정심판, expc=법령해석
            page: Page number
            count: Results per page (max 100)
        """
        if not self.oc:
            return {
                "success": False,
                "error": "API not configured. Please set LAW_GO_KR_OC in .env file."
            }
        
        # lsStmd = 법령체계도목록조회 (law list search)
        params = {
            "OC": self.oc,
            "target": "lsStmd",
            "type": "XML",
            "query": keyword,
            "display": min(count, 100),
            "page": page
        }
        
        try:
            url = f"{self.search_url}?{urlencode(params)}"
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: urlopen(Request(url), timeout=15).read().decode("utf-8")
            )
            return self._parse_search_response(response)
        except (URLError, HTTPError) as e:
            return {"success": False, "error": str(e)}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def get_law_detail(self, law_id: str) -> dict:
        """Get detailed law content by MST number"""
        if not self.oc:
            return {"success": False, "error": "API not configured"}
        
        params = {
            "OC": self.oc,
            "target": "law",
            "type": "XML",
            "MST": law_id
        }
        
        try:
            url = f"{self.service_url}?{urlencode(params)}"
            loop = asyncio.get_running_loop()
            def _fetch():
                return urlopen(Request(url), timeout=15).read().decode("utf-8")
            response = await loop.run_in_executor(None, _fetch)
            return self._parse_detail_response(response)
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _parse_search_response(self, xml_text: str) -> dict:
        """Parse API XML response (lsStmd format)"""
        try:
            root = ET.fromstring(xml_text)
            
            total_count = 0
            total_elem = root.find(".//totalCnt")
            if total_elem is not None and total_elem.text:
                total_count = int(total_elem.text)
            
            laws = []
            for item in root.findall(".//law"):
                law_data = {
                    "law_id": self._get_xml_text(item, "법령일련번호") or self._get_xml_text(item, "법령ID") or self._get_xml_text(item, "MST"),
                    "law_name": self._get_xml_text(item, "법령명한글") or self._get_xml_text(item, "법령명"),
                    "promulgation_date": self._get_xml_text(item, "공포일자"),
                    "enforcement_date": self._get_xml_text(item, "시행일자"),
                    "ministry": self._get_xml_text(item, "소관부처명") or self._get_xml_text(item, "소관부처"),
                    "law_type": self._get_xml_text(item, "법령구분명") or self._get_xml_text(item, "법령구분"),
                }
                laws.append(law_data)
            
            return {
                "success": True,
                "total_count": total_count,
                "laws": laws
            }
        except ET.ParseError as e:
            return {"success": False, "error": f"XML parsing error: {str(e)}"}
    
    def _parse_detail_response(self, xml_text: str) -> dict:
        """Parse law detail XML response"""
        try:
            root = ET.fromstring(xml_text)
            
            law_content = {
                "success": True,
                "law_id": self._get_xml_text(root, "법령ID") or self._get_xml_text(root, "MST"),
                "law_name": self._get_xml_text(root, "법령명"),
                "promulgation_date": self._get_xml_text(root, "공포일자"),
                "enforcement_date": self._get_xml_text(root, "시행일자"),
                "articles": []
            }
            
            for article in root.findall(".//조문"):
                article_data = {
                    "article_no": self._get_xml_text(article, "조문번호"),
                    "article_title": self._get_xml_text(article, "조문제목"),
                    "article_content": self._get_xml_text(article, "조문내용"),
                }
                law_content["articles"].append(article_data)
            
            return law_content
        except ET.ParseError as e:
            return {"success": False, "error": f"XML parsing error: {str(e)}"}
    
    def _get_xml_text(self, element, tag: str) -> str:
        """Safely get text from XML element"""
        if element is None:
            return ""
        child = element.find(f".//{tag}")
        return child.text if child is not None and child.text else ""


# Initialize API service
law_api_service = NationalLawAPIService()


# ============================================
# English Laws (영문법령) - National Law Information
# ============================================
# Curated list: law names that have English versions at https://www.law.go.kr/영문법령/법령명
# Format per usage: /영문법령/법령명 or /영문법령/법령명/(공포번호,공포일자)

ENGLISH_LAW_ENTRIES = {
    "visa": [
        {"name_kr": "출입국관리법", "name_en": "Immigration Control Act"},
        {"name_kr": "출입국관리법시행령", "name_en": "Enforcement Decree of the Immigration Control Act"},
    ],
    "company": [
        {"name_kr": "상법", "name_en": "Commercial Act"},
        {"name_kr": "외국인투자촉진법", "name_en": "Foreign Investment Promotion Act"},
        {"name_kr": "외국인투자촉진법시행령", "name_en": "Enforcement Decree of the Foreign Investment Promotion Act"},
    ],
    "tax": [
        {"name_kr": "법인세법", "name_en": "Corporate Tax Act"},
        {"name_kr": "소득세법", "name_en": "Income Tax Act"},
        {"name_kr": "부가가치세법", "name_en": "Value-Added Tax Act"},
    ],
    "contract": [
        {"name_kr": "민법", "name_en": "Civil Act"},
        {"name_kr": "약관의규제에관한법률", "name_en": "Act on the Regulation of Terms and Conditions"},
        {"name_kr": "독점규제및공정거래에관한법률", "name_en": "Monopoly Regulation and Fair Trade Act"},
        {"name_kr": "개인정보보호법", "name_en": "Personal Information Protection Act"},
    ],
    "labor": [
        {"name_kr": "근로기준법", "name_en": "Labor Standards Act"},
        {"name_kr": "최저임금법", "name_en": "Minimum Wage Act"},
    ],
    "investment": [
        {"name_kr": "외국인투자촉진법", "name_en": "Foreign Investment Promotion Act"},
        {"name_kr": "외국인투자촉진법시행령", "name_en": "Enforcement Decree of the Foreign Investment Promotion Act"},
    ],
    "digital": [
        {"name_kr": "정보통신망이용촉진및정보보호등에관한법률", "name_en": "Act on Promotion of Information and Communications Network Utilization and Information Protection, Etc."},
        {"name_kr": "정보통신망이용촉진및정보보호등에관한법률시행령", "name_en": "Enforcement Decree of the Act on Promotion of Information and Communications Network Utilization and Information Protection, Etc."},
    ],
    "ip": [
        {"name_kr": "상표법", "name_en": "Trademark Act"},
        {"name_kr": "부정경쟁방지및영업비밀보호에관한법률", "name_en": "Unfair Competition Prevention and Trade Secret Protection Act"},
        {"name_kr": "특허법", "name_en": "Patent Act"},
    ],
    "esg": [
        {"name_kr": "환경보전법", "name_en": "Environment Conservation Act"},
        {"name_kr": "산업안전보건법", "name_en": "Industrial Safety and Health Act"},
    ],
}

# Korean keywords for National Law Information API search (optional)
INTENT_TO_LAW_KEYWORDS = {
    "visa": ["출입국관리법", "체류"],
    "company": ["상법", "외국인투자촉진법", "법인"],
    "tax": ["법인세법", "소득세법", "부가가치세법"],
    "contract": ["민법", "계약"],
    "labor": ["근로기준법", "최저임금법", "근로"],
    "investment": ["외국인투자촉진법", "시행령"],
    "digital": ["정보통신망법"],
    "ip": ["상표법", "부정경쟁방지법"],
    "esg": [],
}

LEGAL_KNOWLEDGE = {
    "general": {
        "visa": {
            "answer": "Korea is promoting flexible visa policies to attract skilled foreigners, including preferential residency for those contributing to national strategic interests. Main business visas: D-8 (investment), E-7 (professional), D-9 (trade), D-10 (job seeking). Compliance with the Labor Standards Act (minimum wage, working hours, termination rules) remains essential.",
            "keywords": ["visa", "work permit", "residence", "talent"],
            "confidence": 0.9,
            "related_laws": ["출입국관리법 (Immigration Control Act)", "근로기준법 (Labor Standards Act)"]
        },
        "company": {
            "answer": "Corporate establishment follows the Commercial Act. Steps: (1) Choose company type (2) Name approval (3) Incorporation docs (4) Capital deposit (min KRW 100M for foreigners) (5) Court registration (6) Tax registration. Foreign Investment Promotion Act: investments of KRW 100 million or more (≥10% equity) require prior reporting to MOTIE. Tax reductions and other incentives under the Act continue to apply.",
            "keywords": ["company", "corporation", "registration", "business", "motie"],
            "confidence": 0.85,
            "related_laws": ["상법 (Commercial Act)", "외국인투자촉진법 (Foreign Investment Promotion Act)"]
        },
        "tax": {
            "answer": "Corporate tax 10–25%, VAT 10%, individual income tax 6–45%. Foreign businesses should leverage tax treaties. General incentives under the Foreign Investment Promotion Act (tax reductions, etc.) apply alongside new investment measures.",
            "keywords": ["tax", "vat", "corporate tax", "tax treaty"],
            "confidence": 0.8,
            "related_laws": ["법인세법", "소득세법", "부가가치세법"]
        },
        "contract": {
            "answer": "Contracts should include parties, term, payment, termination, and jurisdiction. Korean translation is important for legal proceedings. Fair trade: comply with the Monopoly Regulation and Fair Trade Act and the Subcontract Act. Dispute resolution: choose strategically between litigation and arbitration.",
            "keywords": ["contract", "agreement", "fair trade", "subcontract"],
            "confidence": 0.7,
            "related_laws": ["민법 (Civil Act)", "약관의규제에관한법률", "공정거래법"]
        },
        "labor": {
            "answer": "Labor Standards Act (minimum wage, working hours, termination rules) remains essential. The 'Yellow Envelope Act' (effective March 2026): subcontracted workers may bargain directly with the prime contractor; limits on claiming damages for strikes—significant for foreign manufacturers and large contractors. Visa policies for talent and foundational labor compliance continue.",
            "keywords": ["labor", "employment", "worker", "wage", "yellow envelope", "strike", "subcontract"],
            "confidence": 0.85,
            "related_laws": ["근로기준법 (Labor Standards Act)", "최저임금법 (Minimum Wage Act)"]
        },
        "investment": {
            "answer": "Foreign Investment & Government Incentives: (1) Expanded cash grants—government has temporarily increased the maximum cash support to 75% (effective 2025) for investments in designated high-tech and strategic sectors. (2) Mandatory reporting: Under the Foreign Investment Promotion Act, investments of KRW 100 million or more (with at least 10% equity) require prior reporting to MOTIE. (3) Ongoing support: Tax reductions and other benefits under the Act continue alongside these new measures.",
            "keywords": ["investment", "motie", "fdi", "cash grant", "incentive"],
            "confidence": 0.9,
            "related_laws": ["외국인투자촉진법", "외국인투자촉진법 시행령"]
        },
        "digital": {
            "answer": "Digital Platform & Emerging Technology: (1) Platform accountability: New rules (effective 2025) require large-scale online platforms (e.g., Google, Meta, Netflix) to establish and provide real-time customer support in Korea. (2) AI Basic Act: Companies commercializing AI must meet transparency obligations (e.g., disclosing AI use, watermarks on AI-generated content). (3) Content & network: Proposed amendments to the Information and Communications Network Act to combat fake news may increase liability and operational requirements for global platform operators.",
            "keywords": ["digital", "platform", "ai", "fake news", "information communications"],
            "confidence": 0.85,
            "related_laws": ["정보통신망법", "AI 기본법"]
        },
        "ip": {
            "answer": "Technology Security & IP: (1) National Core Technology (NCT): Companies with state-designated core technologies must obtain prior MOTIE approval for overseas M&As or technology exports; strict penalties for violations. (2) Trademark Act (effective July 2025): Opposition period shortened to 30 days; significantly higher ceiling for punitive damages for intentional infringement. (3) General IP: Patent, trademark, and trade secret protection under the Unfair Competition Prevention Act remain vital.",
            "keywords": ["ip", "trademark", "patent", "nct", "unfair competition"],
            "confidence": 0.85,
            "related_laws": ["상표법", "부정경쟁방지법"]
        },
        "esg": {
            "answer": "Supply Chain, ESG & Human Rights Due Diligence: Active discussions are underway for a 'Korean version' of the Corporate Sustainability Due Diligence Act. It would mandate human rights and environmental due diligence throughout the supply chain, aligning Korea with global ESG trends. Foreign businesses should monitor this legislation.",
            "keywords": ["esg", "supply chain", "due diligence", "human rights", "sustainability"],
            "confidence": 0.8,
            "related_laws": []
        }
    },
    "USA": {
        "visa": {
            "answer": "US citizens: D-8-4 Startup Visa available with KRW 100M+ investment. KORUS FTA provides benefits. Consider D-10 for job seeking first.",
            "confidence": 0.85
        },
        "company": {
            "answer": "US companies: Consider Joint Venture with Korean partner for market entry. LLC equivalent is 유한회사. Tax treaty exists between US-Korea.",
            "confidence": 0.8
        }
    },
    "UAE": {
        "visa": {
            "answer": "UAE citizens: Visa-free entry for 30 days. For longer stays: D-8 (investment) or E-7 (professional). Documents need UAE Foreign Ministry and Korean Embassy legalization.",
            "confidence": 0.85
        },
        "company": {
            "answer": "UAE companies: Consider Free Economic Zones (Incheon, Busan) for incentives. Minimum capital KRW 100M. Local partner recommended for Middle East connections.",
            "confidence": 0.8
        }
    },
    "UK": {
        "visa": {
            "answer": "UK citizens: D-8 or E-7 visa recommended. Brexit didn't affect Korea-UK visa arrangements. Working holiday visa available for under 30s.",
            "confidence": 0.85
        }
    }
}

INTENT_KEYWORDS = {
    "visa": ["visa", "residence", "immigration", "work permit", "stay", "talent"],
    "company": ["company", "corporation", "registration", "business", "incorporation", "establish", "commercial act"],
    "tax": ["tax", "vat", "corporate tax", "income tax", "tax treaty"],
    "contract": ["contract", "agreement", "document"],
    "labor": ["labor", "employment", "worker", "wage", "working hours", "severance", "yellow envelope", "subcontract", "strike"],
    "investment": ["investment", "motie", "fdi", "cash grant", "incentive", "foreign investment promotion"],
    "digital": ["digital", "platform", "ai", "artificial intelligence", "netflix", "google", "meta", "fake news", "information communications"],
    "ip": ["ip", "intellectual property", "trademark", "patent", "nct", "national core technology", "unfair competition"],
    "esg": ["esg", "supply chain", "due diligence", "human rights", "sustainability", "environmental"],
    "general": ["hello", "hi", "help", "info"]
}

HIGH_RISK_KEYWORDS = ["lawsuit", "dispute", "termination", "court", "litigation", "sue"]


def detect_intent(message: str) -> tuple[str, float]:
    """Detect user intent from message"""
    message_lower = message.lower()
    best_intent = "general"
    best_score = 0.0
    
    for intent, keywords in INTENT_KEYWORDS.items():
        score = sum(1 for keyword in keywords if keyword in message_lower)
        if score > best_score:
            best_score = score
            best_intent = intent
    
    confidence = min(best_score / 3, 1.0)
    return best_intent, confidence


def _safe_reply():
    return {
        "reply": "I'm sorry, I couldn't process that. Please try again or rephrase your question.",
        "confidence": 0.3,
        "needs_expert": False,
        "suggested_expert_type": None,
        "suggested_actions": [],
        "law_references": [],
    }


async def get_response(intent: str, country: str, message: str) -> dict:
    """Generate response centered on English laws (영문법령) via National Law Information."""
    message = (message or "").strip()
    intent = intent or "general"
    country = country or "general"
    
    law_references = []
    
    # Primary: English law links (영문법령) - no API key required
    if intent in ENGLISH_LAW_ENTRIES:
        for entry in ENGLISH_LAW_ENTRIES[intent][:5]:
            try:
                name_kr = entry.get("name_kr") or entry.get("name", "")
                name_en = entry.get("name_en") or name_kr
                url = build_english_law_url(name_kr)
                law_references.append({
                    "name": name_kr,
                    "name_en": name_en,
                    "url": url,
                    "id": name_kr,
                })
            except Exception:
                continue
    
    # Optional: enrich with API search results if configured
    if intent in INTENT_TO_LAW_KEYWORDS and LAW_GO_KR_OC:
        try:
            for keyword in INTENT_TO_LAW_KEYWORDS[intent]:
                api_result = await law_api_service.search_laws(
                    keyword=keyword,
                    search_type="law",
                    count=3
                )
                if api_result.get("success") and api_result.get("laws"):
                    for law in api_result["laws"][:2]:
                        law_name = law.get("law_name")
                        if law_name and not any(r.get("name") == law_name for r in law_references):
                            url = build_english_law_url(law_name)
                            law_references.append({
                                "name": law_name,
                                "name_en": law_name,
                                "url": url,
                                "id": law.get("law_id"),
                            })
                    break
        except Exception:
            pass
    
    # Get response from knowledge base
    try:
        if country in LEGAL_KNOWLEDGE and intent in LEGAL_KNOWLEDGE[country]:
            data = LEGAL_KNOWLEDGE[country][intent]
            response_text = data["answer"]
            confidence = data.get("confidence", 0.7)
        elif intent in LEGAL_KNOWLEDGE["general"]:
            data = LEGAL_KNOWLEDGE["general"][intent]
            response_text = data["answer"]
            confidence = data.get("confidence", 0.7)
        else:
            response_text = "I understand you're asking about general. For specific legal advice, I recommend consulting with a qualified lawyer or e-mailing virtual.esq@gmail.com."
            confidence = 0.3
    except Exception:
        return _safe_reply()
    
    # Add short note when we have law links (UI shows clickable links from law_references)
    if law_references:
        response_text += "\n\n📚 English Laws (영문법령): See links below for official translations (National Law Information)."
    
    # Check if expert is needed
    msg_lower = message.lower()
    needs_expert = any(keyword in msg_lower for keyword in HIGH_RISK_KEYWORDS)
    expert_type = "litigation" if any(k in msg_lower for k in ["lawsuit", "court", "sue"]) else "general"
    
    # Suggested actions
    suggested_actions = []
    if intent == "visa":
        suggested_actions = ["Check visa requirements", "Download application form", "Find immigration lawyer"]
    elif intent == "company":
        suggested_actions = ["Company registration checklist", "Document templates", "Local agent contact"]
    elif intent == "tax":
        suggested_actions = ["Tax treaty information", "Tax calendar", "Find tax accountant"]
    elif intent == "investment":
        suggested_actions = ["MOTIE reporting guide", "Cash grant eligibility", "Find investment lawyer"]
    elif intent == "digital":
        suggested_actions = ["Platform compliance checklist", "AI disclosure requirements", "Find tech lawyer"]
    elif intent == "labor":
        suggested_actions = ["Yellow Envelope Act summary", "Labor Standards checklist", "Find labor lawyer"]
    elif intent == "ip":
        suggested_actions = ["NCT approval process", "Trademark opposition guide", "Find IP lawyer"]
    elif intent == "esg":
        suggested_actions = ["ESG due diligence framework", "Supply chain checklist", "Find ESG advisor"]
    
    if confidence < 0.5:
        response_text += "\n\n⚠️ Note: This is general information. For accurate advice, please consult a legal expert."
    
    try:
        return {
            "reply": response_text,
            "confidence": confidence,
            "needs_expert": needs_expert,
            "suggested_expert_type": expert_type if needs_expert else None,
            "suggested_actions": suggested_actions,
            "law_references": law_references,
        }
    except Exception:
        return _safe_reply()


# ============================================
# API Endpoints
# ============================================

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Legal Assistant Chatbot",
        "version": "1.0.0",
        "focus": "English laws (영문법령) via National Law Information",
        "law_base_url": LAW_GO_KR_BASE,
        "english_law_path": "https://www.law.go.kr/영문법령/법령명",
        "endpoints": {
            "POST /chat": "Chat with legal assistant",
            "GET /health": "Health check",
            "GET /countries": "Supported countries",
            "GET /english-laws": "List English laws by topic",
            "GET /english-laws/url": "Build English law URL",
            "POST /laws/search": "Search laws (API key required)",
            "GET /laws/{law_id}": "Get law details"
        },
        "supported_countries": ["USA", "UAE", "UK", "general"],
        "api_status": {
            "national_law_info_configured": bool(LAW_GO_KR_OC)
        }
    }


@app.get("/english-laws")
async def list_english_laws(topic: Optional[str] = None):
    """
    List English laws (영문법령) by topic.
    Topics: visa, company, tax, contract, labor.
    If topic is omitted, returns all.
    """
    if topic:
        entries = ENGLISH_LAW_ENTRIES.get(topic, [])
        return {
            "topic": topic,
            "laws": [
                {
                    "name_kr": e["name_kr"],
                    "name_en": e["name_en"],
                    "url": build_english_law_url(e["name_kr"]),
                }
                for e in entries
            ],
            "source": f"{LAW_GO_KR_BASE}{ENGLISH_LAW_PATH}",
        }
    return {
        "topics": list(ENGLISH_LAW_ENTRIES.keys()),
        "laws_by_topic": {
            t: [
                {"name_kr": e["name_kr"], "name_en": e["name_en"], "url": build_english_law_url(e["name_kr"])}
                for e in entries
            ]
            for t, entries in ENGLISH_LAW_ENTRIES.items()
        },
        "source": f"{LAW_GO_KR_BASE}{ENGLISH_LAW_PATH}",
        "usage": "https://www.law.go.kr → Enter path: /영문법령/법령명",
    }


@app.get("/english-laws/url")
async def build_english_law_url_endpoint(
    law_name: str,
    promulgation_no: Optional[str] = None,
    promulgation_date: Optional[str] = None,
):
    """
    Build National Law Information URL for an English law (영문법령).
    Usage: /영문법령/법령명 or /영문법령/법령명/(공포번호,공포일자)
    """
    url = build_english_law_url(law_name, promulgation_no or "", promulgation_date or "")
    return {"law_name": law_name, "url": url, "path_rule": "/영문법령/법령명 or /영문법령/법령명/(공포번호,공포일자)"}


@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """Chatbot response endpoint"""
    try:
        message = request.message or ""
        intent, _ = detect_intent(message)
        response_data = await get_response(intent, request.country or "general", message)
        refs = response_data.get("law_references")
        if refs is not None and not isinstance(refs, list):
            refs = []
        return ChatResponse(
            reply=str(response_data.get("reply", "")),
            confidence=float(response_data.get("confidence", 0.5)),
            needs_expert=bool(response_data.get("needs_expert", False)),
            suggested_expert_type=response_data.get("suggested_expert_type"),
            suggested_actions=response_data.get("suggested_actions") or [],
            law_references=refs,
        )
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")


@app.post("/laws/search", response_model=LawSearchResponse)
async def search_laws(request: LawSearchRequest):
    """Search Korean laws via National Law Information API"""
    result = await law_api_service.search_laws(
        keyword=request.keyword,
        search_type=request.search_type,
        page=request.page,
        count=request.count
    )
    
    return LawSearchResponse(
        success=result.get("success", False),
        total_count=result.get("total_count", 0),
        laws=result.get("laws", []),
        error_message=result.get("error")
    )


@app.get("/laws/{law_id}")
async def get_law_detail(law_id: str):
    """Get detailed law content"""
    result = await law_api_service.get_law_detail(law_id)
    
    if not result.get("success"):
        raise HTTPException(
            status_code=404 if "not found" in result.get("error", "").lower() else 500,
            detail=result.get("error", "Failed to retrieve law details")
        )
    
    return result


@app.get("/health")
async def health_check():
    """Health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "legal-chatbot",
        "api_status": {
            "national_law_info": "configured" if LAW_GO_KR_OC else "not configured"
        }
    }


@app.get("/countries")
async def get_countries():
    """Supported countries list"""
    return {
        "countries": ["USA", "UAE", "UK", "general"],
        "description": "Countries currently supported by the legal chatbot"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)

import re
from typing import Any

from app.models.schemas import DetectedContextIndicator
from app.services.detection.scam_classifier import predict_scam_text


# Comprehensive Telecommunication Scam & Social Engineering Taxonomy
INDICATOR_RULES: list[dict[str, Any]] = [
    # 1. CREDENTIAL & OTP HARVESTING (CRITICAL)
    {
        "category": "CREDENTIAL_OTP",
        "label": "Request for OTP / Verification Code",
        "severity": "CRITICAL",
        "weight": 0.50,
        "explanation": "The caller actively solicits a one-time password (OTP), authentication PIN, CVV, password, or verification credentials.",
        "why_it_matters": "Legitimate financial institutions never request OTPs, passwords, or CVVs over phone calls. Disclosing this grants attackers unauthorized account access.",
        "pattern": (
            r"\b(?:tell|give|share|provide|send|disclose|read\s*out|confirm|verify|enter|forward|repeat|say)\b[\w\s]{0,35}\b(?:otp|one[- ]time\s*pass(?:word)?|verification\s*code|security\s*code|auth\s*code|pin|atm\s*pin|upi\s*pin|cvv(?:\s*number)?|password|bank\s*password|netbanking\s*password|login\s*password|passcode|secret\s*code|card\s*details|banking\s*credentials|6[- ]digit\s*code)\b|"
            r"\b(?:what\s*is|need|want|require|asking\s*for|must\s*have)\b[\w\s]{0,35}\b(?:your|the)?\s*(?:otp|one[- ]time\s*pass(?:word)?|verification\s*code|pin|cvv|password|passcode|credentials)\b|"
            r"\b(?:otp|password|pin|cvv)\b[\w\s]{0,25}\b(?:batao|bataiye|share\s*karo|do|dijiye|bhejo|sollunga|cheppandi|ivvandi|kudunga)\b|"
            r"\b(?:enter|type|provide)\s*(?:your\s*)?(?:upi\s*pin|atm\s*pin|mpin)\s*(?:to\s*receive|for\s*refund|for\s*cashback|to\s*get\s*money)\b|"
            r"\b(?:code\s*sent\s*to\s*your\s*(?:phone|mobile|number)\s*(?:tell|give|share|read|what\s*is))\b|"
            r"\b(?:share\s*your\s*bank\s*password|tell\s*me\s*the\s*otp|give\s*me\s*your\s*cvv)\b|"
            r"\b(?:ओटीपी|पासवर्ड|पिन)\s*(?:बताओ|दीजिए|दो|शेयर\s*करो|भेजो)\b"
        ),
    },

    # 2. PARCEL & CUSTOMS CONTRABAND EXTORTION (HIGH)
    {
        "category": "PARCEL_CUSTOMS_SCAM",
        "label": "Courier / Customs Contraband Claim",
        "severity": "HIGH",
        "weight": 0.45,
        "explanation": "The caller claims an intercepted courier parcel or FedEx/DHL package in the user's name contains illegal drugs or contraband.",
        "why_it_matters": "This courier extortion scheme is used to threaten victims with fake narcotics cases and coerce immediate clearance fee transfers.",
        "pattern": (
            r"\b(customs\s*(seizure|parcel|department|hold|calling|detained)|fedex\s*parcel|dhl\s*courier|"
            r"suspicious\s*parcel|parcel\s*(was\s*)?found|package\s*contains\s*illegal|"
            r"customs\s*has\s*detained|parcel\s*(containing|intercepted)|contraband|drugs\s*found|illegal\s*items|"
            r"mdma\s*found|passport\s*found\s*in\s*parcel|parcel\s*me\s*drugs|courier\s*pakda\s*gaya|"
            r"पार्सल|कस्टम्स|कूरियर|ड्रग्स)\b"
        ),
    },

    # 3. DIGITAL ARREST & LAW ENFORCEMENT EXTORTION (CRITICAL)
    {
        "category": "DIGITAL_ARREST_LEGAL_THREAT",
        "label": "Digital Arrest & Police Extortion Threat",
        "severity": "CRITICAL",
        "weight": 0.50,
        "explanation": "The caller threatens immediate arrest, criminal prosecution, police detention, or enforces a fake 'digital arrest'.",
        "why_it_matters": "There is no legal concept of 'digital arrest' via phone or video call in legitimate law enforcement. This is an extortion tactic designed to panic and isolate victims.",
        "pattern": (
            r"\b(digital\s*arrest|arrest\s*warrant|non[- ]bailable\s*warrant|fir\s*registered|court\s*summons|"
            r"legal\s*action|police\s*custody|asset\s*freeze|bank\s*account\s*seizure|criminal\s*charges|"
            r"money\s*laundering\s*case|narcotics\s*case|human\s*trafficking\s*case|involved\s*in\s*a\s*crime|"
            r"police\s*will\s*arrest|arrest\s*you|criminal\s*case|name\s*is\s*linked\s*to\s*a\s*crime|"
            r"do\s*not\s*disconnect|stay\s*on\s*the\s*line|"
            r"arrest\s*kar\s*lenge|jail\s*bhejenge|case\s*darj|digital\s*arrest|girftari|"
            r"arrest\s*chestaru|jail\s*ki\s*pampistamu|arrest\s*pannuvom|"
            r"डिजिटल\s*अरेस्ट|गिरफ्तारी|जेल|वारंट|मुकदमा|पुलिस\s*केस)\b"
        ),
    },

    # 4. GOVERNMENT & AUTHORITY IMPERSONATION (HIGH)
    {
        "category": "AUTHORITY_IMPERSONATION",
        "label": "Government / Police Impersonation",
        "severity": "HIGH",
        "weight": 0.45,
        "explanation": "The caller claims to represent law enforcement, police, CBI, ED, RBI, tax department, court, or government agency.",
        "why_it_matters": "Fraudsters routinely impersonate official agencies to create panic, authority bias, and discourage the victim from independently verifying claims.",
        "pattern": (
            r"\b(police\s*(officer|commissioner|inspector|station|thana|branch|department)|cbi\s*(officer|branch)?|ed\s*director|"
            r"this\s*is\s*(the\s*)?(police|cbi|rbi|cybercrime|cyber\s*cell|customs|court|crime\s*branch)|"
            r"crime\s*branch|income\s*tax\s*officer|customs\s*(officer|department)|rbi\s*(official|officer)?|cyber\s*crime|"
            r"cyber\s*cell|telecom\s*regulatory|dot\s*officer|trai\s*officer|high\s*court|supreme\s*court|"
            r"government\s*(officer|official|agency|investigation)|"
            r"police\s*thana|crime\s*branch|cbi|afsar|adhikari|kaavalthurai|adhigari|"
            r"पुलिस|सीबीआई|इनकम\s*टैक्स|अधिकारी|थाना|न्यायालय)\b"
        ),
    },

    # 5. FINANCIAL TRANSFER & PAYMENT PRESSURE (HIGH)
    {
        "category": "FINANCIAL_REQUEST",
        "label": "Financial Transfer / Payment Demand",
        "severity": "HIGH",
        "weight": 0.45,
        "explanation": "The caller instructs the recipient to transfer funds, send money, or make an immediate payment.",
        "why_it_matters": "Demanding urgent peer-to-peer or bank transfers under pressure is the primary mechanism of financial deception and telecommunications fraud.",
        "pattern": (
            r"\b(?:transfer|wire|send|pay|deposit|remit)\b[\w\s]{0,30}\b(?:money|funds|cash|amount|rupees|\d+|lakh|thousand|crore|penalty|fee|charge|deposit|balance|payment)\b|"
            r"\b(?:send\s*payment|move\s*funds|wire\s*transfer|urgent\s*payment|immediate\s*payment|security\s*deposit|penalty\s*amount|clearance\s*(?:fee|penalty))\b|"
            r"\b(?:send\s*money\s*to\s*this\s*account|transfer\s*to\s*this\s*account|pay\s*on\s*this\s*upi|transfer\s*urgently)\b|"
            r"\b(?:share|give|send|provide|tell)\s*(?:your\s*)?(?:bank\s*(?:account\s*)?details|account\s*details)\b|"
            r"\b(?:paise\s*(?:bhejo|transfer\s*karo|daalo|jama\s*karo)|khate\s*me\s*(?:daalo|bhejo)|rupaye\s*bhejo|dabbu\s*(?:pampandi|transfer)|panam\s*(?:anuppu|transfer))\b|"
            r"\b(?:पैसे\s*(?:भेजो|ट्रांसफर|डालो)|खाते\s*में|रुपये\s*भेजो|जमा\s*करो)\b"
        ),
    },

    # 6. BANKING & ACCOUNT SUSPENSION FRAUD (HIGH)
    {
        "category": "BANK_FRAUD_UNAUTHORIZED",
        "label": "Bank Account / KYC Deactivation Threat",
        "severity": "HIGH",
        "weight": 0.45,
        "explanation": "The caller claims an account, debit card, or banking facility will be blocked or suspended due to KYC expiration or suspicious activity.",
        "why_it_matters": "Attackers fabricate account suspension emergencies to panic victims into compromising their banking access or downloading malware.",
        "pattern": (
            r"\b(?:account|card|debit\s*card|credit\s*card|netbanking)\b[\w\s]{0,30}\b(?:blocked|suspended|freez(?:e|ed)|deactivated|closed|terminated|cancelled)\b|"
            r"\b(?:update\s*(?:your\s*)?kyc|kyc\s*(?:update|expire|pending|verification)|unauthorized\s*transaction|suspicious\s*activity\s*on\s*your\s*account)\b|"
            r"\b(?:verify\s*your\s*bank\s*account|account\s*band\s*ho\s*jayega|card\s*block|खाता\s*ब्लॉक|केवाईसी)\b"
        ),
    },


    # 7. SIM & TELECOM DEACTIVATION SCAM (HIGH)
    {
        "category": "SIM_TELECOM_SCAM",
        "label": "SIM / Telecom Deactivation Threat",
        "severity": "HIGH",
        "weight": 0.45,
        "explanation": "The caller claims the user's SIM card or phone number will be disconnected or deactivated within hours.",
        "why_it_matters": "Telecom deactivation scams are used to harvest personal ID documents, biometric credentials, or hijack SIM lines.",
        "pattern": (
            r"\b(sim\s*(will\s*be\s*)?(blocked|deactivated|disconnected|suspended)|"
            r"phone\s*number\s*(will\s*be\s*)?(disconnected|blocked|cancelled)|"
            r"telecom\s*department|verify\s*your\s*(telecom\s*)?identity|sim\s*verification|"
            r"sim\s*band\s*ho\s*jayega|number\s*kat\s*jayega|sim\s*block)\b"
        ),
    },

    # 8. INVESTMENT & TASK JOB FRAUD (HIGH)
    {
        "category": "INVESTMENT_JOB_SCAM",
        "label": "Investment / Guaranteed Returns Scam",
        "severity": "HIGH",
        "weight": 0.45,
        "explanation": "The caller promises guaranteed investment returns, doubling money, stock tips, or high-paying tasks requiring upfront deposits.",
        "why_it_matters": "Guaranteed-return and advance-fee schemes entice victims into making small deposits before stealing large cumulative sums.",
        "pattern": (
            r"\b(guaranteed\s*returns|double\s*your\s*money|invest\s*today|receive\s*guaranteed\s*returns|"
            r"crypto\s*investment|stock\s*trading\s*tips|limited\s*investment\s*opportunity|"
            r"part[- ]time\s*job|work\s*from\s*home\s*task|registration\s*fees|pay\s*registration\s*fees|"
            r"deposit\s*money\s*to\s*activate|pay\s*before\s*receiving|daily\s*earning\s*5000|"
            r"paise\s*double|ghar\s*baithe\s*kamai|task\s*karo|पैसे\s*डबल|टास्क)\b"
        ),
    },

    # 9. TECH SUPPORT & REMOTE ACCESS (HIGH)
    {
        "category": "TECH_SUPPORT_SCAM",
        "label": "Technical Support / Remote Access Scam",
        "severity": "HIGH",
        "weight": 0.45,
        "explanation": "The caller claims the user's computer or mobile device is infected or compromised, urging remote desktop installation.",
        "why_it_matters": "Remote desktop tools (AnyDesk, TeamViewer) give scammers full control over the victim's screen, keyboard, and banking sessions.",
        "pattern": (
            r"\b(anydesk|teamviewer|quicksupport|ultraviewer|rustdesk|remote\s*access|"
            r"computer\s*virus|windows\s*support|microsoft\s*support|device\s*(is\s*)?(infected|compromised|hacked)|"
            r"install\s*this\s*application|give\s*remote\s*access|system\s*has\s*been\s*compromised|"
            r"anydesk\s*download|app\s*install\s*karo|screen\s*share\s*karo|ऐप\s*डाउनलोड)\b"
        ),
    },

    # 10. BLACKMAIL & COERCIVE EXTORTION (CRITICAL)
    {
        "category": "BLACKMAIL_EXTORTION",
        "label": "Blackmail / Extortion Threat",
        "severity": "CRITICAL",
        "weight": 0.50,
        "explanation": "The caller threatens exposure of private information, video recordings, or severe consequences unless money is transferred immediately.",
        "why_it_matters": "Coercive extortion exploits fear and shame to force victims into compliance before they can consult trusted contacts or law enforcement.",
        "pattern": (
            r"\b(pay\s*(us\s*)?or\s*we\s*(will\s*)?expose|consequences\s*if\s*you\s*refuse|"
            r"leak\s*your\s*video|viral\s*kar\s*denge|blackmail|send\s*money\s*or\s*else|"
            r"serious\s*consequences|ruin\s*your\s*reputation|धमकी|ब्लैकमेल)\b"
        ),
    },

    # 11. FAMILY EMERGENCY / IMPERSONATION (HIGH)
    {
        "category": "FAMILY_EMERGENCY",
        "label": "Family Emergency / Relative Distress Claim",
        "severity": "HIGH",
        "weight": 0.45,
        "explanation": "The caller claims a family member or relative is in extreme danger, hospital, or police custody, demanding urgent funds.",
        "why_it_matters": "Pretending a loved one is in life-threatening distress or legal trouble induces panic and rushed financial wire transfers.",
        "pattern": (
            r"\b(relative\s*is\s*in\s*danger|family\s*emergency|son\s*is\s*in\s*hospital|"
            r"daughter\s*is\s*arrested|accident\s*ho\s*gaya|hospital\s*me\s*hai|"
            r"need\s*money\s*immediately\s*for\s*(treatment|bail|hospital)|"
            r"do\s*not\s*contact\s*anyone\s*else)\b"
        ),
    },

    # 12. URGENCY & TIME PRESSURE (MEDIUM)
    {
        "category": "URGENCY_PRESSURE",
        "label": "Urgency & Psychological Time Pressure",
        "severity": "MEDIUM",
        "weight": 0.20,
        "explanation": "The caller imposes artificial urgency, demanding action within minutes or issuing 'last warnings'.",
        "why_it_matters": "Urgent deadlines short-circuit logical reasoning, preventing victims from calmly verifying claims with official channels.",
        "pattern": (
            r"\b(urgent|urgently|immediately|right\s*now|asap|within\s*10\s*minutes|within\s*15\s*minutes|"
            r"last\s*warning|final\s*notice|time\s*is\s*running\s*out|"
            r"turant|jaldi|abhi\s*ke\s*abhi|fatafat|foran|ventane|tvaraga|ippude|udane|seekiram|ippove|"
            r"तुरंत|जल्दी|अभी|आपातकाल)\b"
        ),
    },

    # 13. SECRECY & ISOLATION COERCION (HIGH)
    {
        "category": "SECRECY_COERCION",
        "label": "Secrecy & Isolation Instruction",
        "severity": "HIGH",
        "weight": 0.30,
        "explanation": "The caller insists that the conversation remain secret and demands that the recipient stay on the line without contacting family or police.",
        "why_it_matters": "Isolation tactics prevent the victim from seeking second opinions or realizing the situation is a scam.",
        "pattern": (
            r"\b(do\s*not\s*tell\s*anyone|keep\s*this\s*secret|strictly\s*confidential|between\s*us|"
            r"do\s*not\s*disconnect|stay\s*on\s*the\s*line|do\s*not\s*call\s*(family|police|lawyer)|"
            r"line\s*mat\s*kaatna|kisi\s*ko\s*mat\s*batana|secret\s*rakhna|raaz\s*rakhna|"
            r"evariki\s*cheppavaddhu|rahasyam|call\s*cut\s*cheyoddu|"
            r"yaarukkum\s*sollaatheenga|ragasiyam|call\s*cut\s*pannatheenga|"
            r"किसी\s*को\s*मत\s*बताना|सीक्रेट|कॉल\s*मत\s*काटना)\b"
        ),
    },
]


def infer_scam_category(
    detected_indicators: list[DetectedContextIndicator],
    is_synthetic: bool = False,
    deepfake_prob: float = 0.0,
    transcript: str | None = None,
) -> tuple[str, str, str]:
    """
    Infers the most probable scam category, confidence level, and description
    based on the set of detected indicators, voice authenticity, and speech context.
    """
    word_count = len(transcript.strip().split()) if transcript else 0

    if not detected_indicators:
        if is_synthetic and deepfake_prob >= 0.70:
            return (
                "Synthetic / Cloned Voice Interaction",
                "MEDIUM",
                "Acoustic vocoder artifacts indicate AI-generated speech, though no explicit scam transcript language was identified. Note: A synthetic voice alone does not automatically constitute fraud.",
            )
        if word_count < 4:
            return (
                "Listening for speech...",
                "LOW",
                "Awaiting sufficient conversational speech for threat analysis.",
            )
        elif word_count <= 10:
            return (
                "Routine / Normal Call",
                "MEDIUM",
                "Brief speech sample evaluated. No telecommunication scam, extortion, or synthetic voice indicators detected.",
            )
        else:
            return (
                "Routine / Normal Call",
                "HIGH",
                "No high-confidence telecommunication scam, extortion, or synthetic voice indicators were detected.",
            )


    categories = {ind.category for ind in detected_indicators}
    word_count = len(transcript.strip().split()) if transcript else 10

    # 1. Customs / Contraband Parcel Scam (Takes priority if parcel cues present)
    if "PARCEL_CUSTOMS_SCAM" in categories:
        conf = "HIGH" if word_count >= 4 else "MEDIUM"
        return (
            "Customs / Courier Parcel Extortion Scam",
            conf,
            "The caller claims an intercepted package or contraband to demand clearance fees or impose extortion.",
        )

    # 2. Credential & OTP Theft
    if "CREDENTIAL_OTP" in categories:
        conf = "HIGH"
        return (
            "OTP & Credential Theft Attempt",
            conf,
            "The conversation directly solicits one-time passwords, netbanking pins, or verification credentials.",
        )

    # 3. Digital Arrest / Law Enforcement Extortion
    if "DIGITAL_ARREST_LEGAL_THREAT" in categories or (
        "AUTHORITY_IMPERSONATION" in categories and ("SECRECY_COERCION" in categories or "FINANCIAL_REQUEST" in categories)
    ):
        conf = "HIGH"
        return (
            "Digital Arrest / Authority Impersonation Scam",
            conf,
            "The caller claims official authority or threatens legal arrest/penalties to coerce compliance or financial transfers.",
        )

    # 4. Bank Account & KYC Suspension Fraud
    if "BANK_FRAUD_UNAUTHORIZED" in categories:
        conf = "HIGH" if word_count >= 4 else "MEDIUM"
        return (
            "Banking & Account KYC Fraud",
            conf,
            "The caller fabricates account suspension or unauthorized transaction claims to extract credentials or funds.",
        )

    # 5. Financial Transfer / Wire Scam
    if "FINANCIAL_REQUEST" in categories and ("URGENCY_PRESSURE" in categories or "AUTHORITY_IMPERSONATION" in categories or "SECRECY_COERCION" in categories):
        conf = "HIGH"
        return (
            "Financial Transfer & Payment Scam",
            conf,
            "High-pressure demands for urgent wire or money transfers detected under deceptive pretexts.",
        )

    # 6. Tech Support / Remote Access Scam
    if "TECH_SUPPORT_SCAM" in categories:
        conf = "HIGH"
        return (
            "Tech Support & Remote Access Scam",
            conf,
            "The caller claims computer infection or urges installation of remote desktop management software (AnyDesk, TeamViewer).",
        )

    # 7. Investment & Guaranteed Returns Scam
    if "INVESTMENT_JOB_SCAM" in categories:
        conf = "HIGH"
        return (
            "Investment & Advance Fee Scam",
            conf,
            "The caller offers unrealistic investment returns or part-time task compensation requiring upfront deposits.",
        )

    # 8. SIM / Telecom Deactivation Scam
    if "SIM_TELECOM_SCAM" in categories:
        conf = "HIGH"
        return (
            "SIM & Telecom Deactivation Scam",
            conf,
            "The caller threatens immediate phone line deactivation to harvest identity credentials.",
        )

    # 9. Blackmail / Extortion
    if "BLACKMAIL_EXTORTION" in categories:
        conf = "HIGH"
        return (
            "Blackmail & Coercive Extortion",
            conf,
            "The caller uses coercive threats and intimidation to demand money.",
        )

    # 10. Family Emergency Scam
    if "FAMILY_EMERGENCY" in categories:
        conf = "HIGH"
        return (
            "Family Emergency Impersonation Scam",
            conf,
            "The caller claims a relative is in emergency distress to elicit urgent funds.",
        )

    # 11. AI Voice Cloning Fraud
    if is_synthetic and deepfake_prob >= 0.60:
        return (
            "AI Voice Clone Impersonation",
            "HIGH",
            "A synthetic or cloned voice was detected in conjunction with conversational requests.",
        )

    # 12. Authority Impersonation alone
    if "AUTHORITY_IMPERSONATION" in categories:
        return (
            "Authority & Official Impersonation",
            "MEDIUM",
            "The caller claims official agency affiliation (police, CBI, customs, bank). Monitor for follow-up financial demands.",
        )

    # 13. Financial Request alone
    if "FINANCIAL_REQUEST" in categories:
        return (
            "Unverified Payment Request",
            "MEDIUM",
            "The conversation contains fund transfer or payment instructions without explicit extortion cues.",
        )

    # 14. General Social Engineering & Pressure
    if "SECRECY_COERCION" in categories or "URGENCY_PRESSURE" in categories:
        return (
            "Psychological Pressure & Urgency Tactics",
            "MEDIUM",
            "The caller utilizes artificial urgency, secrecy, or psychological pressure tactics.",
        )

    return (
        "Suspicious Call Pattern",
        "MEDIUM",
        "Conversational anomalies detected matching known fraud indicators.",
    )



def normalize_speech_text(text: str) -> str:
    if not text:
        return ""
    # Spaced acronyms (e.g. o t p, o.t.p, a t p)
    t = re.sub(r"\b[oO][\s.-]+[tT][\s.-]+[pP]\b", "otp", text)
    t = re.sub(r"\b[aA][\s.-]+[tT][\s.-]+[pP]\b", "otp", t)
    t = re.sub(r"\b[cC][\s.-]+[vV][\s.-]+[vV]\b", "cvv", t)
    t = re.sub(r"\b[pP][\s.-]+[iI][\s.-]+[nN]\b", "pin", t)
    t = re.sub(r"\bone[- ]time\s*pass(?:word)?\b", "otp", t, flags=re.IGNORECASE)

    # Contextual ATP -> OTP
    atp_context = re.compile(
        r"\b(tell|give|share|send|enter|provide|say|read|received?|input|sms|message|code|verify|verification|bank|account|security)\b[\w\s]{0,35}\b(atp)\b|\b(atp)\b[\w\s]{0,35}\b(tell|give|share|send|enter|provide|received?|code|sms|number|digits?|verification|immediately|now)\b",
        re.IGNORECASE,
    )
    if atp_context.search(t):
        t = re.sub(r"\b(atp)\b", "otp", t, flags=re.IGNORECASE)

    return t


def analyze_context_detailed(transcript: str | None) -> dict[str, Any]:
    """
    Analyzes transcript context across multiple threat dimensions and Indian multilingual patterns.
    """
    if not transcript or not transcript.strip():
        return {
            "context_risk": 0.0,
            "context_risk_score": 0,
            "risk_level": "Evaluating",
            "possible_scam_category": "Listening for speech...",
            "scam_category_confidence": "LOW",
            "scam_category_description": "Awaiting spoken audio from caller stream.",
            "indicators": [],
            "detected_indicators": [],
            "language": "unknown",
        }

    normalized = normalize_speech_text(transcript).lower().strip()
    word_count = len(normalized.split())
    score = 0.0
    detected_indicators: list[DetectedContextIndicator] = []
    indicator_labels: list[str] = []

    # Detect language script hints
    has_devanagari = bool(re.search(r"[\u0900-\u097F]", transcript))
    has_tamil = bool(re.search(r"[\u0B80-\u0BFF]", transcript))
    has_telugu = bool(re.search(r"[\u0C00-\u0C7F]", transcript))

    if has_devanagari:
        lang_detected = "Hindi (Devanagari)"
    elif has_tamil:
        lang_detected = "Tamil"
    elif has_telugu:
        lang_detected = "Telugu"
    elif any(word in normalized for word in ("paise", "bhejo", "turant", "jaldi", "mat", "batana", "khate", "thana", "police")):
        lang_detected = "Hinglish / Hindi (Roman)"
    elif any(word in normalized for word in ("dabbu", "pampandi", "ventane", "cheppandi")):
        lang_detected = "Telugu (Roman)"
    elif any(word in normalized for word in ("panam", "anuppu", "udane", "sollunga")):
        lang_detected = "Tamil (Roman)"
    else:
        lang_detected = "English"

    # Contextual intent filters:
    # 1. Defensive warning expressions (e.g. "do not share your OTP", "never give your password")
    defensive_pattern = re.compile(
        r"\b(?:do\s*not|don'?t|never|should\s*not|must\s*not|won'?t|will\s*not|cannot|can'?t|nobody\s*should)\s*(?:ever\s*)?(?:share|give|tell|disclose|send|provide|reveal|forward)\b[\w\s]{0,30}\b(?:otp|password|pin|cvv|code|detail|credential|secret)\b|\b(?:bank\s*(?:will\s*)?never\s*ask|nobody\s*should\s*ask|never\s*ask\s*for\s*otp|beware\s*of\s*scam|do\s*not\s*fall\s*for)\b|\b(?:kisi\s*ko\s*mat\s*(?:batana|dena)|mat\s*share\s*karna|mat\s*batao)\b.*\b(?:otp|password|pin|cvv)\b",
        re.IGNORECASE,
    )

    # 2. Passive receipt expressions (e.g. "I received an OTP for my login", "My bank sent me an OTP")
    passive_receipt_pattern = re.compile(
        r"\b(?:i\s*(?:have\s*)?(?:received|got|gotten|have)|sent\s*me|came\s*to\s*my|for\s*my\s*login)\s*(?:an\s*|a\s*)?(?:otp|message|sms|code|password\s*reset)\b|\b(?:my\s*bank\s*sent|received\s*an\s*otp|got\s*an\s*otp|waiting\s*for\s*(?:an\s*)?otp|otp\s*has\s*come|otp\s*aaya)\b",
        re.IGNORECASE,
    )

    text_for_cred = defensive_pattern.sub(" ", normalized)
    text_for_cred = passive_receipt_pattern.sub(" ", text_for_cred)

    for rule in INDICATOR_RULES:
        search_text = text_for_cred if rule["category"] == "CREDENTIAL_OTP" else normalized
        match = re.search(rule["pattern"], search_text, re.IGNORECASE)
        if match:
            matched_text = match.group(0)

            score += rule["weight"]
            indicator_labels.append(rule["label"])
            detected_indicators.append(
                DetectedContextIndicator(
                    category=rule["category"],
                    label=rule["label"],
                    severity=rule["severity"],
                    matched_cue=matched_text,
                    weight=rule["weight"],
                    explanation=rule.get("explanation"),
                    why_it_matters=rule.get("why_it_matters"),
                )
            )

    # 3. Trained NLP Scam Classifier Inference
    nlp_res = predict_scam_text(normalized)
    nlp_classification = nlp_res.get("classification", "GENUINE")
    nlp_scam_prob = float(nlp_res.get("scam_probability", 0.0))
    nlp_confidence = float(nlp_res.get("confidence", 0.5))

    # Progressive multi-indicator synergy rules
    categories_found = {item.category for item in detected_indicators}
    has_otp = "CREDENTIAL_OTP" in categories_found
    has_urgency = "URGENCY_PRESSURE" in categories_found
    has_finance = "FINANCIAL_REQUEST" in categories_found
    has_authority = "AUTHORITY_IMPERSONATION" in categories_found
    has_arrest = "DIGITAL_ARREST_LEGAL_THREAT" in categories_found
    has_blackmail = "BLACKMAIL_EXTORTION" in categories_found
    has_bank = "BANK_FRAUD_UNAUTHORIZED" in categories_found
    has_secrecy = "SECRECY_COERCION" in categories_found
    has_investment = "INVESTMENT_JOB_SCAM" in categories_found

    if not detected_indicators:
        if nlp_classification == "SCAM" and nlp_scam_prob >= 0.60:
            # Model identified fraud cues (advance fee, lottery, job upfront fee, fake grant)
            score = max(score, nlp_scam_prob * 0.88)
            detected_indicators.append(
                DetectedContextIndicator(
                    category="NLP_SCAM_PREDICTION",
                    label="AI Scam Intent Detected",
                    severity="HIGH" if nlp_scam_prob < 0.85 else "CRITICAL",
                    matched_cue="Trained NLP Classifier Pattern Match",
                    weight=0.50,
                    explanation=f"Trained NLP model classified spoken intent as telecommunication deception ({round(nlp_scam_prob * 100)}% confidence).",
                    why_it_matters="Spoken vocabulary matches known financial fraud and social engineering vectors.",
                )
            )
            indicator_labels.append("AI Scam Intent Detected")
        else:
            score = 0.0
    else:
        # If NLP model confirms SCAM with high probability, elevate baseline
        if nlp_classification == "SCAM":
            score = max(score, nlp_scam_prob * 0.70)

        # Isolated Urgency stays in Guarded / Moderate (25-35)
        if categories_found == {"URGENCY_PRESSURE"}:
            score = min(max(score, 0.28), 0.35)
        elif has_arrest:
            score = max(score, 0.90 if (has_finance or has_urgency or has_secrecy) else 0.80)
        elif has_blackmail:
            score = max(score, 0.88)
        elif has_otp:
            # Single OTP query without corroboration starts at 70 (High); escalates to Critical with urgency/finance
            if has_urgency or has_finance or has_authority or has_bank or has_secrecy:
                score = max(score, 0.88)
            else:
                score = max(score, 0.70)
        elif has_authority and (has_finance or has_secrecy):
            score = max(score, 0.82)
        elif has_bank and (has_urgency or has_finance):
            score = max(score, 0.72)
        elif has_investment:
            score = max(score, 0.70)
        elif has_finance and has_urgency:
            score = max(score, 0.65)
        elif has_finance or has_authority or has_bank:
            score = max(score, 0.50)

    # If NLP model strongly confirms GENUINE and no critical indicators, suppress false positives
    if nlp_classification == "GENUINE" and nlp_confidence >= 0.85 and not (has_otp or has_arrest or has_blackmail):
        if not (has_finance and has_authority):
            score = min(score, 0.24)

    final_risk = min(round(score, 3), 1.0)
    final_score_100 = round(final_risk * 100)

    if final_score_100 >= 75:
        risk_level = "CRITICAL"
    elif final_score_100 >= 50:
        risk_level = "HIGH"
    elif final_score_100 >= 25:
        risk_level = "MODERATE"
    elif word_count < 4 and not detected_indicators:
        risk_level = "Evaluating"
    else:
        risk_level = "LOW"

    category_name, confidence_level, category_desc = infer_scam_category(detected_indicators, transcript=transcript)

    return {
        "context_risk": final_risk,
        "context_risk_score": final_score_100,
        "risk_level": risk_level,
        "classification": nlp_classification,
        "confidence": nlp_confidence,
        "scam_probability": nlp_scam_prob,
        "nlp_model_status": nlp_res.get("model_status", "trained_nlp_pipeline"),
        "possible_scam_category": category_name,
        "scam_category_confidence": confidence_level,
        "scam_category_description": category_desc,
        "indicators": indicator_labels,
        "detected_indicators": detected_indicators,
        "language": lang_detected,
    }


def analyze_context(transcript: str | None) -> tuple[float, list[str]]:
    """
    Backward-compatible entry point returning (context_risk, indicators).
    """
    res = analyze_context_detailed(transcript)
    return res["context_risk"], res["indicators"]

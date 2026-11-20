
import re
import json
from groq import Groq

from app.config import GROQ_API_KEY, LLM_MODEL


def extract_with_rules(enquiry, name=None, email=None, company=None):
    text = enquiry.lower()

    services = {
        "AI Automation": ["automation", "ai agent", "chatbot"],
        "Software Development": ["website", "software", "web app", "saas"],
        "Cloud Services": ["aws", "azure", "cloud"],
        "Digital Marketing": ["seo", "marketing", "advertising", "crm"],
        "AI Voice Agents": ["voice agent", "voice bot"],
    }

    matched_services = [
        service
        for service, keywords in services.items()
        if any(keyword in text for keyword in keywords)
    ]

    requested_service = (
        ", ".join(matched_services)
        if matched_services
        else "Not specified"
    )

    industry_options = [
        "healthcare", "finance", "education",
        "e-commerce", "retail", "technology"
    ]

    industry = next(
        (item for item in industry_options if item in text),
        None
    )

    budget = None

    match = re.search(
        r"(?:₹|rs\.?\s*)([\d,]+)\s*(lakh|lakhs|k)?",
        text
    )

    if match:
        budget = float(match.group(1).replace(",", ""))

        if match.group(2):
            unit = match.group(2).lower()
            if unit.startswith("lakh"):
                budget *= 100000
            elif unit == "k":
                budget *= 1000

    timeline_match = re.search(
        r"(\d+\s*(?:days?|weeks?|months?))",
        text
    )

    timeline = (
        timeline_match.group(1)
        if timeline_match else None
    )

    requirements = []

    for item in [
        "CRM integration",
        "payment integration",
        "dashboard",
        "analytics",
        "WhatsApp integration",
        "mobile application",
    ]:
        if item.lower() in text:
            requirements.append(item)

    intent = (
        "high"
        if any(word in text for word in [
            "ready to proceed",
            "looking to build",
            "want to start",
            "launch",
            "urgently"
        ])
        else "medium"
    )

    missing = []

    if budget is None:
        missing.append("budget")

    if timeline is None:
        missing.append("timeline")

    if requested_service == "Not specified":
        missing.append("service requirements")

    return {
        "name": name,
        "email": email,
        "company": company,
        "industry": industry,
        "requested_service": requested_service,
        "budget_inr": budget,
        "timeline": timeline,
        "requirements": requirements,
        "intent": intent,
        "missing_information": missing,
    }


def extract_with_llm(enquiry, name=None, email=None, company=None):
    client = Groq(api_key=GROQ_API_KEY)

    prompt = f"""
You are a business lead intelligence assistant.

Extract structured information from the customer enquiry.

Rules:
1. Never invent missing information.
2. Return null for unknown budget or timeline.
3. Identify requested services accurately.
4. Identify explicit customer requirements.
5. Classify intent as low, medium or high.
6. List missing information.

Return valid JSON with these fields:
industry, requested_service, budget_inr,
timeline, requirements, intent, missing_information.

Customer enquiry:
{enquiry}
"""

    response = client.chat.completions.create(
        model=LLM_MODEL,
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    data = json.loads(
        response.choices[0].message.content
    )

    data.update({
        "name": name,
        "email": email,
        "company": company
    })

    return data


def calculate_lead_score(profile):
    score = 15

    budget = profile.get("budget_inr")

    # Budget qualification
    if budget is not None:
        if budget >= 200000:
            score += 25
        elif budget >= 50000:
            score += 15
        else:
            score += 5

    # Timeline urgency
    if profile.get("timeline"):
        score += 10

    # Buying intent
    intent = profile.get("intent")

    if intent == "high":
        score += 20
    elif intent == "medium":
        score += 10

    # Service requirement
    if profile.get("requested_service") != "Not specified":
        score += 10

    # Contact availability
    if profile.get("email"):
        score += 5

    score = min(score, 100)

    if score >= 75:
        priority = "High"
        action = "Schedule a discovery call"

    elif score >= 50:
        priority = "Medium"
        action = "Send clarification email"

    else:
        priority = "Low"
        action = "Request additional information"

    return score, priority, action


def generate_followup(profile):
    missing = profile.get("missing_information", [])

    questions = ""

    if missing:
        questions = (
            "\nCould you please share your "
            + ", ".join(missing)
            + "?"
        )

    return f"""
Subject: Follow-up regarding {profile['requested_service']}

Hello {profile.get('name') or 'there'},

Thank you for contacting us.

We would be happy to discuss your requirements
regarding {profile['requested_service']}.

{questions}

Would you be available for a short discovery call?

Best regards,
Cynbit Team
"""


def analyze_lead(enquiry, name=None, email=None, company=None):
    method = "rule_based"

    profile = extract_with_rules(
        enquiry, name, email, company
    )

    if GROQ_API_KEY:
        try:
            profile = extract_with_llm(
                enquiry, name, email, company
            )
            method = "groq_llm"

        except Exception:
            # Fallback if LLM is unavailable
            method = "rule_based_fallback"

    score, priority, action = calculate_lead_score(profile)

    profile.update({
        "priority_score": score,
        "priority": priority,
        "recommended_action": action,
        "followup_email": generate_followup(profile),
        "extraction_method": method
    })

    return profile

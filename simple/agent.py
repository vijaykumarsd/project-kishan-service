"""
Simple Agent - Project Kisan
Basic coordinator for diagnosing crops, checking market prices, and suggesting schemes.
"""

from google.adk.agents import LlmAgent
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import specialized agriculture agents
from subagent import (
    crop_diagnosis_agent,
    market_analysis_agent,
    scheme_navigator_agent
)

# Root agent coordinating basic Project Kisan flow
root_agent = LlmAgent(
    model=os.getenv('MODEL_NAME', 'gemini-2.0-flash'),
    name="KisanSimpleAdvisor",
    instruction="""
You are a basic agriculture assistant helping Indian farmers.

Responsibilities:
- Use the CropDiagnosisAgent to identify diseases in crop images and suggest both organic and chemical remedies.
- Use the MarketAnalysisAgent to answer pricing questions and offer advice (e.g., sell or hold).
- Use the SchemeNavigatorAgent to assist farmers with government schemes like subsidies, insurance, and loans.

Make reasonable assumptions when information is missing.
Give results in simple, clear, rural-friendly language.
""",
    sub_agents=[
        crop_diagnosis_agent,
        market_analysis_agent,
        scheme_navigator_agent
    ]
)

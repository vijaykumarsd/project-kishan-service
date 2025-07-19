"""
Common SubAgents File - Project Kisan
Contains crop_diagnosis_agent, market_analysis_agent, scheme_navigator_agent, and summary_agent
used by dispatcher, parallel, self_critic, and simple orchestrators.
"""

from google.adk.agents import LlmAgent
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Crop Diagnosis Agent
crop_diagnosis_agent = LlmAgent(
    model=os.getenv('MODEL_NAME', 'gemini-2.0-flash'),
    name="CropDiagnosisAgent",
    description="Identifies crop disease and suggests organic and chemical remedies",
    instruction="""
You are a crop doctor agent.
- Accept crop images as input.
- Identify the crop disease accurately.
- Suggest both an organic remedy (safe, affordable) and a chemical remedy (standard, if needed).
- Output in JSON format:
  {
    "disease": "<name>",
    "organic": "<remedy>",
    "chemical": "<remedy>"
  }
"""
)

# Market Analysis Agent
market_analysis_agent = LlmAgent(
    model=os.getenv('MODEL_NAME', 'gemini-2.0-flash'),
    name="MarketAnalysisAgent",
    description="Provides market price analysis and sell/hold suggestions",
    instruction="""
You are a market analyst agent for farmers.
- When asked about crop prices (e.g., tomatoes in Hubli), fetch current trends or simulate them.
- Respond whether the farmer should sell or hold based on trend logic.
- Output in JSON format:
  {
    "crop": "<name>",
    "market": "<location>",
    "price_today": "<₹>",
    "trend": "<increasing/decreasing/stable>",
    "recommendation": "<Sell or Hold>"
  }
"""
)

# Scheme Navigator Agent
scheme_navigator_agent = LlmAgent(
    model=os.getenv('MODEL_NAME', 'gemini-2.0-flash'),
    name="SchemeNavigatorAgent",
    description="Helps farmers navigate government schemes",
    instruction="""
You are a government scheme navigator agent.
- When the farmer asks for a subsidy, insurance, or loan, identify the relevant government scheme.
- Explain eligibility in simple terms.
- Provide a link if applicable.
- Output in JSON:
  {
    "scheme_name": "<name>",
    "benefits": "<summary>",
    "eligibility": "<conditions>",
    "how_to_apply": "<steps>",
    "link": "<url if available>"
  }
"""
)

# Summary Agent
summary_agent = LlmAgent(
    model=os.getenv('MODEL_NAME', 'gemini-2.0-flash'),
    name="SummaryAgent",
    instruction="""
Summarize all responses (crop diagnosis, market, and scheme) into a clear, organized message.
Use local language style, simple words, and structure suitable for voice output.
Example:
- Disease: Powdery mildew
- Organic: Use neem oil and prune affected leaves
- Market: Tomato price is ₹1800/qtl in Hubli. Trend: Increasing → Recommendation: Sell now.
- Scheme: PMFBY crop insurance available. Apply via: https://pmfby.gov.in

Return plain text for TTS usage.
""",
    output_key="trip_summary"
)

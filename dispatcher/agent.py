"""
Dispatcher Agent
Routes farmer's multimodal queries to the appropriate agricultural sub-agents.
"""

import os
from dotenv import load_dotenv
from google.adk.agents import LlmAgent
from google.adk.tools import agent_tool

# Load environment variables
load_dotenv()

# Import specialized sub-agents from the shared subagent.py
from subagent import (
    crop_diagnosis_agent,
    market_analysis_agent,
    scheme_navigator_agent,
    summary_agent
)

# Convert each sub-agent into a callable tool
crop_tool = agent_tool.AgentTool(agent=crop_diagnosis_agent)
market_tool = agent_tool.AgentTool(agent=market_analysis_agent)
scheme_tool = agent_tool.AgentTool(agent=scheme_navigator_agent)
summary_tool = agent_tool.AgentTool(agent=summary_agent)

# Define the root dispatcher agent
root_agent = LlmAgent(
    model=os.getenv('MODEL_NAME', 'gemini-2.0-flash'),
    name="KisanHelper",
    instruction="""
You are a multilingual agricultural assistant designed to support small-scale Indian farmers.

You can:
- Analyze crop issues from images using the CropDiagnosisAgent.
- Provide real-time market advice using the MarketAnalysisAgent.
- Guide through subsidy/government schemes using SchemeNavigatorAgent.
- Use SummaryAgent to compile a clear, spoken/written result.

Workflow:
1. Detect if image is provided → Use CropDiagnosisAgent.
2. If question is about market prices, trends, or advice → Use MarketAnalysisAgent.
3. If query relates to subsidy, scheme, tractor loan, etc. → Use SchemeNavigatorAgent.
4. Always compile the final answer clearly using SummaryAgent.

Assume missing details when unclear. Prefer short, local-language friendly responses with clear action points.

Return your response in a way that’s friendly to farmers with limited literacy, using simple words and clarity.
""",
    tools=[
        crop_tool,
        market_tool,
        scheme_tool,
        summary_tool
    ]
)

# Example query: "Please check this tomato leaf photo and suggest an organic remedy.
# Also tell me if I should sell tomatoes today in Mandya and how to apply for a crop insurance scheme."

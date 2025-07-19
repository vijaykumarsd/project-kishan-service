"""
Parallel Agent - Project Kisan
Runs market and scheme advisors in parallel for efficiency.
"""

import os
from dotenv import load_dotenv
from google.adk.agents import ParallelAgent, SequentialAgent
from subagent import (
    crop_diagnosis_agent,
    market_analysis_agent,
    scheme_navigator_agent,
    summary_agent
)

# Load environment variables
load_dotenv()

# Step 1: Parallel planning (market + scheme)
agri_parallel = ParallelAgent(
    name="ParallelMarketSchemePlanner",
    sub_agents=[market_analysis_agent, scheme_navigator_agent],
    description="Fetch market trend and scheme information in parallel."
)

# Step 2: Complete sequential flow
root_agent = SequentialAgent(
    name="KisanParallelWorkflow",
    description="Orchestrates crop diagnosis, market pricing, and scheme guidance in parallel followed by a summary.",
    sub_agents=[
        crop_diagnosis_agent,    # Analyze crop image first (optional image upload)
        agri_parallel,           # Market price + Scheme info concurrently
        summary_agent            # Summarize into clear, farmer-friendly output
    ]
)

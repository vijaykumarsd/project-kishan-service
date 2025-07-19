"""
Self Critic Agent - Project Kisan
Provides quality assurance for agricultural advice output.
"""

from google.genai.types import Content, Part
from typing import AsyncGenerator
from google.adk.agents import BaseAgent, LlmAgent, SequentialAgent, ParallelAgent
from google.adk.events import Event
from google.adk.agents.invocation_context import InvocationContext
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import project-specific agents
from subagent import (
    crop_diagnosis_agent,
    market_analysis_agent,
    scheme_navigator_agent,
    summary_agent
)

# Step 1: Parallel agent to analyze market and scheme in parallel
agri_parallel = ParallelAgent(
    name="AgriParallelAnalysis",
    sub_agents=[market_analysis_agent, scheme_navigator_agent],
    description="Runs market analysis and scheme navigator in parallel"
)

# Step 2: Self-review agent to assess quality of summary
kisan_summary_reviewer = LlmAgent(
    model=os.getenv('MODEL_NAME', 'gemini-2.0-flash'),
    name="KisanSummaryReviewer",
    instruction="""
Review the final agricultural advice provided in {trip_summary}.
- Confirm if it includes crop diagnosis (if applicable), current market status, and relevant government schemes.
- Ensure clarity for rural users, simplicity of remedies, and safety of suggestions.
- If all requirements are fulfilled and text is easy to understand, return 'pass'. Otherwise return 'fail'.
""",
    output_key="review_status"
)

# Step 3: Validation logic to gatekeep output
class ValidateKisanSummary(BaseAgent):
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        status = ctx.session.state.get("review_status")
        summary = ctx.session.state.get("trip_summary")  # Output from summary_agent
        if status == "pass":
            yield Event(author=self.name, content=Content(parts=[
                Part(text=f"✅ Final validated output:\n\n{summary}")
            ]))
        else:
            yield Event(author=self.name, content=Content(parts=[
                Part(text="❌ The summary did not pass quality review. Please improve the structure or completeness.")
            ]))

validate_summary_agent = ValidateKisanSummary(
    name="ValidateKisanSummary",
    description="Validates the Kisan summary review status and responds accordingly."
)

# Final root workflow for Self-Critic Kisan Agent
root_agent = SequentialAgent(
    name="KisanSelfCriticWorkflow",
    description="Orchestrates a robust multi-step flow: diagnosis → parallel analysis → summarization → review → validation.",
    sub_agents=[
        crop_diagnosis_agent,         # Optional: can be skipped if no image
        agri_parallel,                # Run market + scheme in parallel
        summary_agent,                # Compile final advice
        kisan_summary_reviewer,      # Review output for completeness and clarity
        validate_summary_agent        # Pass/fail decision
    ]
)

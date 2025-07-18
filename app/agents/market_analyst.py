from adk.llms.vertexai import VertexAILLM
from adk.core.agent import Agent

instruction = """You are a market analyst helping farmers make the best decisions about when and where to sell their crops. Based on current market prices, historical trends, and location-specific data, advise whether the farmer should sell now or wait. Provide clear, simple guidance using market reasoning, and mention price trends when possible."""

llm = VertexAILLM(
    project_id="your-gcp-project-id",
    location="us-central1",
    model_name="gemini-1.5-pro-preview-0409"
)

agent = Agent(
    llm=llm,
    system_instruction=instruction
)

def handle_query(query: str):
    return agent.run(query)

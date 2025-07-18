from adk.llms.vertexai import VertexAILLM
from adk.core.agent import Agent

instruction = """You are a government scheme expert helping farmers find and understand subsidies, loans, and benefits they are eligible for. When a farmer asks for help, identify the most relevant government schemes based on their needs. Explain eligibility clearly, list required documents, and guide them on how to apply online or offline."""

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

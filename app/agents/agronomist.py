from adk.core.agent import Agent
from adk.llms.vertexai import VertexAILLM

llm = VertexAILLM(
    project_id="your-gcp-project-id",
    location="us-central1",
    model_name="gemini-1.5-pro-preview-0409"
)
agent = Agent(
    llm=llm,
    system_instruction="""You are an expert agronomist helping farmers understand plant diseases. When a farmer describes a crop issue or shares an image, analyze the symptoms carefully. Explain the likely disease in simple terms and provide clear steps to treat it using both organic and chemical methods. Ensure that your response is actionable, safe for the crop, and locally practical for small-scale farmers."""
)

def handle_query(query: str):
    return agent.run(query)

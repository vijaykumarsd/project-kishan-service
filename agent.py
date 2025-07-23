# agent.py
import os
import uuid
import asyncio
from dotenv import load_dotenv, find_dotenv
import vertexai
import inspect

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

from vertexai.preview.reasoning_engines import AdkApp
from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.tools import FunctionTool

print("DEBUG: Inspecting FunctionTool.__init__ signature:")
try:
    signature = inspect.signature(FunctionTool.__init__)
    print(f"DEBUG: FunctionTool.__init__ signature: {signature}")
except Exception as e:
    print(f"ERROR: Could not get FunctionTool.__init__ signature: {e}")

from google.genai import types as genai_types

# Load .env variables
dotenv_path = find_dotenv()
if dotenv_path:
    load_dotenv(dotenv_path)
    print(f"DEBUG: Loaded .env from {dotenv_path}")
else:
    print("ERROR: .env file not found.")

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
MODEL_NAME = os.getenv("MODEL_NAME", "gemini-1.5-pro-preview-0409")
CREDENTIALS_PATH_ENV = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

if not PROJECT_ID:
    raise ValueError("Missing GOOGLE_CLOUD_PROJECT")
if not CREDENTIALS_PATH_ENV:
    raise ValueError("Missing GOOGLE_APPLICATION_CREDENTIALS")

vertexai.init(project=PROJECT_ID, location=LOCATION)

# ---------------------- Agent Definitions ----------------------

crop_diagnosis_agent = LlmAgent(
    model=MODEL_NAME,
    name="CropDiagnosisAgent",
    description="Diagnoses crop disease and remedies based on a textual description of symptoms.", # Clarified description
    instruction="""
    You are a highly skilled crop doctor agent.
    Your task is to analyze the provided textual description of crop symptoms and provide a diagnosis and remedies.
    Output your diagnosis and remedies as a JSON object.
    Output JSON:
    {
      "disease": "<name>",
      "organic_remedy": "<remedy>",
      "chemical_remedy": "<remedy>",
      "observed_symptoms_from_description": "<detailed description of symptoms based on the input text, e.g., 'Yellow spots with dark centers on leaves, indicating early blight.'>"
    }
    If you cannot identify a specific disease, state that, but still describe the symptoms based on the input text.
    """
)

market_analysis_agent = LlmAgent(
    model=MODEL_NAME,
    name="MarketAnalysisAgent",
    description="Analyzes market and suggests Sell/Hold.",
    instruction="""
    You are a market analyst.
    Output JSON:
    {
      "crop": "<name>",
      "market": "<location>",
      "price_today": "<₹>",
      "trend": "<increasing/decreasing/stable>",
      "recommendation": "<Sell or Hold>"
    }
    """
)

scheme_navigator_agent = LlmAgent(
    model=MODEL_NAME,
    name="SchemeNavigatorAgent",
    description="Helps with government schemes.",
    instruction="""
    Output JSON:
    {
      "scheme_name": "<name>",
      "benefits": "<summary>",
      "eligibility": "<conditions>",
      "how_to_apply": "<steps>",
      "link": "<url>"
    }
    """
)

summary_agent = LlmAgent(
    model=MODEL_NAME,
    name="SummaryAgent",
    description="Summarizes data for farmers in plain text.",
    instruction="""
    You get multiple JSON inputs and summarize clearly.
    Output only plain text.
    """
)

# ---------------------- Shared Session Service for Internal Runners ----------------------
_internal_session_service = InMemorySessionService()

# ---------------------- Async Tool Wrapper Helper Function ----------------------
# This helper remains the same as it needs to accept multimodal content to run internal agents.
async def run_agent_and_get_text(agent: LlmAgent, input_content: genai_types.Content):
    """Helper to run an LlmAgent and extract its final text response."""
    print(f"DEBUG: Calling internal agent '{agent.name}' with input_content: '{input_content}'")

    internal_runner = Runner(
        app_name=f"{agent.name}App",
        agent=agent,
        session_service=_internal_session_service
    )

    session_id = f"tool_session_{uuid.uuid4()}"

    try:
        await _internal_session_service.create_session(
            app_name=f"{agent.name}App",
            user_id="tool_user",
            session_id=session_id
        )
        print(f"DEBUG: Created session '{session_id}' for internal runner '{agent.name}App'.")

        print(f"DEBUG: Input to {agent.name} through its Runner: {input_content}")

        final_response_text = f"No final text response from {agent.name}."

        async def get_internal_agent_events():
            print(f"DEBUG: Running internal agent {agent.name} via its Runner in a thread...")
            results_list = await asyncio.to_thread(
                lambda: list(internal_runner.run(
                    user_id="tool_user",
                    session_id=session_id,
                    new_message=input_content
                ))
            )
            print(f"DEBUG: Collected {len(results_list)} events from internal agent {agent.name} in thread.")
            for event in results_list:
                yield event

        async for event in get_internal_agent_events():
            print(f"DEBUG (Internal Agent Event from {agent.name}): Type: {type(event)}, is_final_response: {getattr(event, 'is_final_response', False)}")
            content = getattr(event, 'content', None)
            if content:
                print(f"DEBUG (Internal Agent Content from {agent.name}): {content}")
                for part in content.parts:
                    if getattr(part, 'text', None):
                        print(f"   DEBUG (Tool Response from {agent.name}): TEXT: {part.text}")
                        if getattr(event, 'is_final_response', False):
                            final_response_text = part.text
                            break
                    if getattr(part, 'function_call', None):
                        print(f"   DEBUG (Tool Response from {agent.name}): FUNCTION CALL: {part.function_call.name}({part.function_call.args})")
                    if getattr(part, 'error', None):
                        print(f"   ERROR (Tool Response from {agent.name}): ERROR PART: {part.error}")
                        final_response_text = f"Error from {agent.name}: {part.error.message}"
                        break

            if getattr(event, 'is_final_response', False) and final_response_text != f"No final text response from {agent.name}.":
                break

        return final_response_text

    except Exception as e:
        print(f"ERROR: Exception during internal agent '{agent.name}' tool call: {e}")
        import traceback
        traceback.print_exc()
        return f"Error processing request with {agent.name}: {str(e)}"

# ---------------------- Tool Wrapper Functions ----------------------
# These functions should now accept simple string arguments for automatic function calling.

async def crop_diagnosis_tool(query: str) -> str: # REVERTED to string query
    """
    Diagnose crop disease and suggest organic and chemical remedies based on a textual description.
    Args:
        query (str): A detailed textual description of the crop symptoms.
    Returns:
        str: JSON string with disease, organic_remedy, chemical_remedy, observed_symptoms_from_description.
    """
    # Create Content from string query for this tool
    input_content = genai_types.Content(role="user", parts=[genai_types.Part(text=query)])
    return await run_agent_and_get_text(crop_diagnosis_agent, input_content)

async def market_analysis_tool(query: str) -> str:
    """
    Analyze market prices and provide sell/hold suggestions for crops.
    Args:
        query (str): A query about crop prices (e.g., "tomatoes in Hubli").
    Returns:
        str: JSON string with crop, market, price_today, trend, recommendation.
    """
    input_content = genai_types.Content(role="user", parts=[genai_types.Part(text=query)])
    return await run_agent_and_get_text(market_analysis_agent, input_content)

async def scheme_navigator_tool(query: str) -> str:
    """
    Help farmers navigate government schemes, eligibility, and application links.
    Args:
        query (str): A query about government schemes (e.g., "subsidy for rice farmers").
    Returns:
        str: JSON string with scheme_name, benefits, eligibility, how_to_apply, link.
    """
    input_content = genai_types.Content(role="user", parts=[genai_types.Part(text=query)])
    return await run_agent_and_get_text(scheme_navigator_agent, input_content)

async def summarize_output_tool(json_data: str) -> str:
    """
    Summarize raw JSON data from other agents into a clear, organized, plain text message.
    Args:
        json_data (str): The JSON string output from another agent.
    Returns:
        str: Plain text summary suitable for voice output.
    """
    input_content = genai_types.Content(role="user", parts=[genai_types.Part(text=json_data)])
    return await run_agent_and_get_text(summary_agent, input_content)

# ---------------------- Sequential Agent Definition (Optional) ----------------------
step1_diagnosis_agent = LlmAgent(
    model=MODEL_NAME,
    name="Step1_Diagnose",
    instruction="Diagnose crop and output JSON.",
    output_key="diagnosis_json"
)

step2_market_agent = LlmAgent(
    model=MODEL_NAME,
    name="Step2_Market",
    instruction="Based on {diagnosis_json}, do market analysis. Output JSON.",
    output_key="market_json"
)

step3_summarize_agent = LlmAgent(
    model=MODEL_NAME,
    name="Step3_Summarize",
    instruction="Summarize {diagnosis_json} and {market_json} in plain text."
)

pipeline_agent = SequentialAgent(
    name="CropMarketPipelineAgent",
    sub_agents=[step1_diagnosis_agent, step2_market_agent, step3_summarize_agent]
)

async def crop_market_pipeline_tool(query: str) -> str:
    """
    Runs a sequential pipeline for crop diagnosis and market analysis, then summarizes the combined result.
    Args:
        query (str): The initial query for diagnosis and market analysis.
    Returns:
        str: A summarized plain text result from the pipeline.
    """
    pipeline_runner = Runner(
        app_name=f"{pipeline_agent.name}App",
        agent=pipeline_agent,
        session_service=_internal_session_service
    )

    pipeline_session_id = f"pipeline_session_{uuid.uuid4()}"
    try:
        await _internal_session_service.create_session(
            app_name=f"{pipeline_agent.name}App",
            user_id="pipeline_user",
            session_id=pipeline_session_id
        )
        print(f"DEBUG: Created session '{pipeline_session_id}' for pipeline runner '{pipeline_agent.name}App'.")

        final_pipeline_response_text = "No response from pipeline."

        async def get_pipeline_events():
            print(f"DEBUG: Running pipeline agent {pipeline_agent.name} via its Runner in a thread...")
            results_list = await asyncio.to_thread(
                lambda: list(pipeline_runner.run(
                    user_id="pipeline_user",
                    session_id=pipeline_session_id,
                    new_message=genai_types.Content(role="user", parts=[genai_types.Part(text=query)])
                ))
            )
            print(f"DEBUG: Collected {len(results_list)} events from pipeline agent {pipeline_agent.name} in thread.")
            for event in results_list:
                yield event

        async for event in get_pipeline_events():
            print(f"DEBUG (Pipeline Event from {pipeline_agent.name}): Type: {type(event)}, is_final_response: {getattr(event, 'is_final_response', False)}")
            content = getattr(event, 'content', None)
            if content:
                print(f"DEBUG (Pipeline Content from {pipeline_agent.name}): {content}")
                for part in content.parts:
                    if getattr(part, 'text', None):
                        print(f"   DEBUG (Pipeline Tool Response from {pipeline_agent.name}): TEXT: {part.text}")
                        if getattr(event, 'is_final_response', False):
                            final_pipeline_response_text = part.text
                            break
                    if getattr(part, 'function_call', None):
                        print(f"   DEBUG (Pipeline Tool Response from {pipeline_agent.name}): FUNCTION CALL: {part.function_call.name}({part.function_call.args})")
                    if getattr(part, 'error', None):
                        print(f"   ERROR (Pipeline Tool Response from {pipeline_agent.name}): ERROR PART: {part.error}")
                        final_pipeline_response_text = f"Error from {pipeline_agent.name}: {part.error.message}"
                        break

            if getattr(event, 'is_final_response', False) and final_pipeline_response_text != "No response from pipeline.":
                break

        return final_pipeline_response_text

    except Exception as e:
        print(f"ERROR: Error in pipeline agent '{pipeline_agent.name}' tool call: {e}")
        import traceback
        traceback.print_exc()
        return f"Error processing request with {pipeline_agent.name}: {str(e)}"

# ---------------------- Orchestrator Agent Definition ----------------------

kisan_orchestrator_agent = LlmAgent(
    model=MODEL_NAME,
    name="KisanOrchestrator",
    instruction="""
    You are an AI assistant designed to help farmers with crop health, market insights, and government schemes.
    You have access to specialized tools.

    **Instructions for Tool Use:**
    - Always summarize any JSON output from 'crop_diagnosis_tool', 'market_analysis_tool', or 'scheme_navigator_tool' using the 'summarize_output_tool' before giving the final response.

    **Image and Text Handling:**
    - When the user provides input, first analyze ALL parts of the input, including any text and images.
    - If the user provides an IMAGE (either with or without a text query):
        - Your primary task is to identify crop symptoms from the image.
        - **Critically: You must generate a detailed textual description of the symptoms you observe in the image.**
        - Then, call the `crop_diagnosis_tool` using this *generated textual description* as the `query` argument.
        - After receiving the JSON diagnosis from `crop_diagnosis_tool`, you MUST use `summarize_output_tool` to present it in a farmer-friendly, plain text format.
    - If the user provides only a TEXT query (no image):
        - Route it to the most appropriate tool:
            - Use `crop_diagnosis_tool` if the query is about crop symptoms or disease (passing the original text query).
            - Use `market_analysis_tool` if the query is about crop prices, market trends, or sell/hold recommendations.
            - Use `scheme_navigator_tool` if the query is about government schemes.
            - Use `summarize_output_tool` if you receive JSON data that needs summarization.

    **Important Considerations:**
    - Do NOT attempt to use the 'crop_market_pipeline_tool' directly at this time due to known framework limitations. If a query requires both diagnosis and market analysis, you must decide to call each tool individually and then summarize their combined output.
    - Be concise and directly answer the farmer's question.
    """,
    tools=[
        FunctionTool(crop_diagnosis_tool),
        FunctionTool(market_analysis_tool),
        FunctionTool(scheme_navigator_tool),
        FunctionTool(summarize_output_tool),
        FunctionTool(crop_market_pipeline_tool), # UNCOMMENT IF YOU WANT TO TEST THE PIPELINE TOOL
    ],
)

kisan_orchestrated_app = AdkApp(agent=kisan_orchestrator_agent)
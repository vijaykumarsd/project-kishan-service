# project-kishan-service
project-kishan-service
#  project-kishan-service

## Kisan: Agri Assistant using Multi-Agent AI (Gemini + ADK)

A powerful AI-driven agricultural assistant designed to help farmers and agri-analysts make smarter decisions using **Google's Agent Development Kit (ADK)** and **Gemini LLMs**. The system uses a **multi-agent architecture**, each with its own instruction kit and responsibility.

---

##  Core Features

- **Multi-Agent System**:
  - **Agronomist Agent**: Provides crop suggestions and diagnoses plant diseases.
  - **Market Analyst Agent**: Offers real-time pricing insights and demand predictions.
  - **Scheme Navigator Agent**: Helps farmers understand and apply for government schemes.

- Built using:
  - Google’s **Agent Development Kit (ADK)**
  - **Gemini LLM**
  - **Python (FastAPI backend)**

---

##  Project Structure


project-kishan-service/
│
├── app/
│   ├── main.py                   # FastAPI app entry point
│   ├── agents/                   # Contains sub-agent logic
│   │   ├── agronomist.py
│   │   ├── market_analyst.py
│   │   └── scheme_navigator.py
│   ├── routes/                   # API routes
│   └── models/                   # Data schemas
│
├── agri_agentic_ai/
│   ├── agent_runner.py          # Multi-agent controller
│   ├── main.py
│   └── tools/                   # Tooling used by agents
│       ├── agronomist_tool.py
│       ├── market_tool.py
│       └── scheme_tool.py
│
├── requirements.txt             # Dependencies
└── README.md                    # Project documentation

## Getting Started
## Prerequisites
Python 3.9+
Access to Gemini API via Google ADK
(Optional) Virtual Environment

## Installation
git clone https://github.com/vijaykumarsd/project-kishan-service.git
cd project-kishan-service>/
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt

## Run the App
uvicorn app.main:app --reload

## Access the API
Open your browser and go to:
http://localhost:8000/docs — FastAPI Swagger UI.

## Agents & Instruction Kits
Each agent is initialized with its own Gemini LLM model and prompt instructions via ADK:
Agent            	Purpose                                     
Agronomist Agent	Analyze soil, crop health, and provide tips 
Market Analyst	    Analyze trends and pricing 
Scheme Navigator	Recommend government schemes

## API Endpoints
Route        	Description                 
`/diagnose/`	Uses Agronomist agent    
`/market/` 	Uses Market Analyst agent
`/schemes/`	Uses Scheme Navigator agent



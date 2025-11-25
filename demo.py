import os
from langchain.chat_models import init_chat_model
from langchain.agents import create_agent
from langchain.tools import tool
from langchain.agents.middleware import dynamic_prompt, ModelRequest
from langchain.agents.structured_output import ToolStrategy
from pydantic import BaseModel

os.environ["GOOGLE_API_KEY"] = "AIzaSyDpjqa902tXL7MOtc0G2TJneXLR3TQmKkA"


@tool
def search(query: str) -> str:
    """Search for information."""
    return f"Results for: {query}"


class ContactInfo(BaseModel):
    name: str
    email: str
    phone: str


model = init_chat_model("google_genai:gemini-2.5-flash-lite")

agent = create_agent(model, tools=[search], response_format=ToolStrategy(ContactInfo))

result = agent.invoke(
    {
        "messages": [
            {
                "role": "user",
                "content": "Extract contact info from: John Doe, john@example.com, (555) 123-4567",
            }
        ]
    }
)

print(f"==============\n{result["structured_response"]}")

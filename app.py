import os
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
from dotenv import load_dotenv
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from azure.ai.agents.models import ListSortOrder

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv("FLASK_SECRET_KEY", "defaultsecret")
socketio = SocketIO(app, cors_allowed_origins="*")

# Validate required environment variables
endpoint = os.getenv("AZURE_PROJECT_ENDPOINT")
agent_id = os.getenv("AZURE_AGENT_ID")
if not endpoint or not agent_id:
    raise ValueError("AZURE_PROJECT_ENDPOINT and AZURE_AGENT_ID must be set in .env")

project = AIProjectClient(credential=DefaultAzureCredential(), endpoint=endpoint)
agent = project.agents.get_agent(agent_id)

@app.route("/")
def index():
    return render_template("index.html")

@socketio.on("user_message")
def handle_user_message(data):
    user_input = data.get("message", "")
    thread = project.agents.threads.create()
    project.agents.messages.create(thread_id=thread.id, role="user", content=user_input)
    run = project.agents.runs.create_and_process(thread_id=thread.id, agent_id=agent.id)

    while run.status not in ["completed", "failed"]:
        run = project.agents.runs.get(run.id)

    if run.status == "failed":
        emit("agent_response", {"role": "system", "content": f"Run failed: {run.last_error}"})
    else:
        messages = project.agents.messages.list(thread_id=thread.id, order=ListSortOrder.ASCENDING)
        for msg in messages:
            if msg.text_messages:
                emit("agent_response", {"role": msg.role, "content": msg.text_messages[-1].text.value})

    # Suggested prompts (placeholder logic)
    suggestions = []
    if "jira" in user_input.lower():
        suggestions = ["Create Jira Bug", "Check Jira Task Status", "Assign Jira Issue"]
    elif "servicenow" in user_input.lower():
        suggestions = ["Report Incident", "Check Ticket Status", "Request Access"]
    elif "confluence" in user_input.lower():
        suggestions = ["Search Knowledge Base", "Find Architecture Guidelines", "View Project Wiki"]
    else:
        suggestions = ["Create Jira Bug", "Report Incident", "Search Knowledge Base"]

    emit("suggested_prompts", {"prompts": suggestions})

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)

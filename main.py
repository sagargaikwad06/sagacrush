from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import chat

app = FastAPI(title="SagaCrush AI Chatbot", version="1.0.0")

# ----- CORS Setup (Production Domains Only) -----
origins = [
    "https://www.sagacrush.com",
    "https://sagacrush.com",
     "http://127.0.0.1:8000"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----- Request / Response Models -----
class ChatRequest(BaseModel):
    message: str
    mode: str = "general"
    session_id: str = None

class ChatResponse(BaseModel):
    reply: str
    session_id: str

class SessionRequest(BaseModel):
    session_id: str = None

# ----- Chat Endpoint -----
@app.post("/chat", response_model=ChatResponse, summary="Send a message to SagaCrush AI")
async def chat_api(payload: ChatRequest):
    reply, session_id = await chat.generate_reply(payload.message, payload.mode, payload.session_id)
    return {"reply": reply, "session_id": session_id}

# ----- New Chat Endpoint -----
@app.post("/new_chat", summary="Create a new chat session")
def new_chat():
    session_id = chat.new_session()
    return {"session_id": session_id, "message": "New chat session created."}

# ----- Clear Chat Endpoint -----
@app.post("/clear_chat", summary="Clear current chat messages but keep user facts")
def clear_chat(payload: SessionRequest):
    if not payload.session_id:
        return {"error": "session_id is required"}
    chat.clear_session_messages(payload.session_id)
    return {"session_id": payload.session_id, "message": "Chat history cleared, facts preserved."}

# ----- Delete Chat Endpoint -----
@app.post("/delete_chat", summary="Delete chat session and all data")
def delete_chat(payload: SessionRequest):
    if not payload.session_id:
        return {"error": "session_id is required"}
    chat.delete_session(payload.session_id)
    return {"session_id": payload.session_id, "message": "Chat session deleted."}


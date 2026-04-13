import os
import json
import re
from typing import Literal

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, END

from agent.state import AgentState, IntentType
from agent.rag_pipeline import KB_CONTEXT
from tools.lead_capture import mock_lead_capture

def get_llm():
    return ChatGroq(model="llama-3.1-8b-instant", temperature=0.3)

SYSTEM_PROMPT = f"""You are an intelligent sales assistant for AutoStream, \
an AI-powered video editing SaaS for content creators.

Your goals:
1. Greet users warmly and answer product / pricing questions accurately.
2. Use ONLY the knowledge base below to answer product questions. Do NOT invent features or prices.
3. When a user shows strong buying intent (e.g., "I want to sign up", "I'd like to try the Pro plan", \
"how do I get started"), shift into lead-qualification mode.
4. Collect the user's name, email, and creator platform ONE FIELD AT A TIME — do not ask for all three at once.
5. Once all three are collected, confirm and thank the user. The backend will handle the rest.

Always be concise, friendly, and helpful. Never make up information.

─────────────────────────────────────────
KNOWLEDGE BASE
─────────────────────────────────────────
{KB_CONTEXT}
─────────────────────────────────────────
"""

INTENT_CLASSIFIER_PROMPT = """You are an intent classifier for a SaaS sales chatbot.

Classify the user's latest message into EXACTLY ONE of these intents:
- greeting         : casual hello, how are you, small talk
- product_inquiry  : questions about features, pricing, plans, policies, trials
- high_intent      : clear buying signal — user wants to sign up, start a trial, \
                     upgrade, purchase, or try a specific plan
- unknown          : anything else / off-topic

Respond with ONLY the intent label, nothing else.
"""


#  Node 1 Classify intent 
def classify_intent(state: AgentState) -> AgentState:
    """Determine the intent of the most recent user message."""
    llm = get_llm()

    last_human = next(
        (m for m in reversed(state["messages"]) if isinstance(m, HumanMessage)),
        None,
    )
    if last_human is None:
        return {**state, "intent": "unknown"}

    response = llm.invoke(
        [
            SystemMessage(content=INTENT_CLASSIFIER_PROMPT),
            HumanMessage(content=last_human.content),
        ]
    )
    raw = response.content.strip().lower()

    valid: list[IntentType] = ["greeting", "product_inquiry", "high_intent", "unknown"]
    intent: IntentType = raw if raw in valid else "unknown"

    return {**state, "intent": intent}


#  Node 2 Generate response 
def respond(state: AgentState) -> AgentState:
    """
    Generate the agent's reply.

    Behaviour matrix
    ─────────────────
    • lead already captured          → thank user, no more collection
    • waiting_for is set             → extract the expected field from last message
    • intent == high_intent          → start lead collection (ask for name)
    • intent == greeting/inquiry     → normal KB-grounded reply
    """
    llm = get_llm()
    lead_info = dict(state.get("lead_info") or {})
    waiting_for = state.get("waiting_for")
    lead_captured = state.get("lead_captured", False)

    
    if lead_captured:
        reply = (
            "You're all set! 🎉 Our team will be in touch shortly. "
            "Is there anything else I can help you with?"
        )
        return {
            **state,
            "messages": [AIMessage(content=reply)],
        }

    last_human_msg = next(
        (m.content for m in reversed(state["messages"]) if isinstance(m, HumanMessage)),
        "",
    )

    
    if waiting_for:
        lead_info[waiting_for] = last_human_msg.strip()

        # Determine next missing field
        next_field = _next_missing_field(lead_info)

        if next_field:
            reply = _ask_for_field(next_field)
            return {
                **state,
                "lead_info": lead_info,
                "waiting_for": next_field,
                "messages": [AIMessage(content=reply)],
            }
        else:
            # All three collected — signal ready for capture
            reply = (
                f"Perfect! Just to confirm:\n"
                f"• Name: {lead_info['name']}\n"
                f"• Email: {lead_info['email']}\n"
                f"• Platform: {lead_info['platform']}\n\n"
                "I'm registering your interest now — hold on a second! ✅"
            )
            return {
                **state,
                "lead_info": lead_info,
                "waiting_for": None,
                "messages": [AIMessage(content=reply)],
            }

    
    if state.get("intent") == "high_intent":
        reply = (
            "That's awesome — let's get you started with AutoStream! 🚀\n\n"
            "I just need a few quick details. What's your full name?"
        )
        return {
            **state,
            "lead_info": lead_info,
            "waiting_for": "name",
            "messages": [AIMessage(content=reply)],
        }

    messages_for_llm = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
    response = llm.invoke(messages_for_llm)

    return {
        **state,
        "messages": [AIMessage(content=response.content)],
    }


# Node 3 Capture lead 
def capture_lead(state: AgentState) -> AgentState:
    """
    Fire the mock_lead_capture tool.
    This node is only reached when all three lead fields are present.
    """
    info = state["lead_info"]
    result = mock_lead_capture(
        name=info["name"],
        email=info["email"],
        platform=info["platform"],
    )

    confirmation = (
        f"🎉 You're officially on our list, {info['name']}! "
        "We'll send a welcome email to "
        f"{info['email']} within the next few minutes. "
        "Welcome to AutoStream! 🎬"
    )

    return {
        **state,
        "lead_captured": True,
        "messages": [AIMessage(content=confirmation)],
    }


# ── Routing helpers ────────────────────────────────────────────────────────────
def _next_missing_field(lead_info: dict) -> str | None:
    for field in ("name", "email", "platform"):
        if not lead_info.get(field):
            return field
    return None


def _ask_for_field(field: str) -> str:
    prompts = {
        "name": "What's your full name?",
        "email": "Great! And what's your email address?",
        "platform": (
            "Almost there! Which platform do you primarily create content on? "
            "(e.g., YouTube, Instagram, TikTok, Facebook…)"
        ),
    }
    return prompts[field]


def _should_capture(state: AgentState) -> Literal["capture_lead", "end"]:
    """Route to capture_lead only when all three fields are filled and lead not yet captured."""
    if state.get("lead_captured"):
        return "end"
    info = state.get("lead_info") or {}
    if (
        info.get("name")
        and info.get("email")
        and info.get("platform")
        and state.get("waiting_for") is None
    ):
        return "capture_lead"
    return "end"


# Build the graph 
def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("classify_intent", classify_intent)
    graph.add_node("respond", respond)
    graph.add_node("capture_lead", capture_lead)

    graph.set_entry_point("classify_intent")
    graph.add_edge("classify_intent", "respond")
    graph.add_conditional_edges(
        "respond",
        _should_capture,
        {
            "capture_lead": "capture_lead",
            "end": END,
        },
    )
    graph.add_edge("capture_lead", END)

    return graph.compile()


# Singleton compiled graph
agent_graph = build_graph()

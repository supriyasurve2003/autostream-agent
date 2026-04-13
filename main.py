import os
from langchain_core.messages import HumanMessage
from dotenv import load_dotenv
load_dotenv()
from agent.graph import agent_graph
from agent.state import AgentState


def print_banner():
    print("\n" + "=" * 60)
    print("  🎬  AutoStream AI Assistant  (powered by LangGraph)")
    print("=" * 60)
    print("  Type 'quit' or 'exit' to end the session.")
    print("  Type 'reset' to start a fresh conversation.")
    print("=" * 60 + "\n")


def initial_state() -> AgentState:
    return {
        "messages": [],
        "intent": "unknown",
        "lead_info": {},
        "lead_captured": False,
        "waiting_for": None,
    }


def run_chat():
    print_banner()

    state = initial_state()

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\nGoodbye! 👋")
            break

        if not user_input:
            continue

        if user_input.lower() in ("quit", "exit"):
            print("\nThanks for chatting with AutoStream! Goodbye 👋\n")
            break

        if user_input.lower() == "reset":
            state = initial_state()
            print("\n[Conversation reset]\n")
            continue

        state["messages"] = state["messages"] + [HumanMessage(content=user_input)]

        state = agent_graph.invoke(state)

        
        last_ai = next(
            (m for m in reversed(state["messages"])
             if hasattr(m, "type") and m.type == "ai"),
            None,
        )
        if last_ai:
            print(f"\nAgent: {last_ai.content}\n")


if __name__ == "__main__":
    
    if not os.environ.get("GROQ_API_KEY"):

       print("\n❌  GROQ_API_KEY is not set!\n")
    else:
       run_chat()

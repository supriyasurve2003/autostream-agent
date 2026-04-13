# 🎬 AutoStream AI Agent

A **LangGraph-powered conversational AI agent** that acts as a sales assistant for AutoStream — a fictional SaaS platform providing automated video editing tools for content creators.

Built as part of the ServiceHive / Inflx ML Intern assignment.

---

## 📁 Project Structure

```
autostream-agent/
├── agent/
│   ├── __init__.py
│   ├── graph.py          # LangGraph nodes, edges, and routing logic
│   ├── rag_pipeline.py   # Knowledge base loader & context builder
│   └── state.py          # Shared AgentState TypedDict
├── knowledge_base/
│   └── autostream_kb.json  # Local KB (pricing, policies, FAQs)
├── tools/
│   ├── __init__.py
│   └── lead_capture.py   # Mock CRM lead capture tool
├── main.py               # CLI entry point
├── requirements.txt
└── README.md
```

---

## 🚀 How to Run Locally

### 1. Clone the repository

```bash
git clone https://github.com/<your-username>/autostream-agent.git
cd autostream-agent
```

### 2. Create and activate a virtual environment

```bash
python -m venv myvenv

# Windows
myvenv\Scripts\activate

# macOS / Linux
source myvenv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set your API key (You can use other LLM also)

Get a free Groq API key at 👉 [console.groq.com](https://console.groq.com) — no credit card required.

Create a `.env` file in the project root:

```
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxxxxx
```

Or set it directly in the terminal:

```bash
# Windows
$env:GROQ_API_KEY="gsk_xxxxxxxxxxxxxxxxxxxxxxxx"

# macOS / Linux
export GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxxxxx
```

### 5. Run the agent

```bash
python main.py
```

You will see an interactive CLI prompt. Type messages to chat with the agent.

```
You: Hi there!
Agent: Hey! 👋 Welcome to AutoStream...

You: What are your pricing plans?
Agent: Great question! We have two plans...

You: I want to sign up for the Pro plan for my YouTube channel.
Agent: Awesome — let's get you started! What's your full name?
```

---

## 🏗️ Architecture Explanation (~200 words)

### Why LangGraph?

LangGraph was chosen over plain LangChain chains or AutoGen because it provides **explicit, inspectable state management** through a typed `AgentState` object. Each conversation turn flows through a directed graph of nodes, making the control logic easy to reason about, test, and extend.

### How the Graph Works

The agent graph has three nodes:

1. **`classify_intent`** — A lightweight LLM call categorises the user's latest message as `greeting`, `product_inquiry`, `high_intent`, or `unknown`. This is kept as a separate, focused prompt to avoid contaminating the main response prompt with classification logic.

2. **`respond`** — The main response node. It branches internally based on the current state:
   - **Normal conversation**: the full knowledge base is injected as system context (RAG), and the LLM answers grounded in that context only.
   - **Lead collection in progress**: the agent extracts the expected field (name → email → platform) from the user's reply and asks for the next missing piece — one field at a time to feel natural.
   - **High-intent detected**: transitions state into lead-collection mode.

3. **`capture_lead`** — Fires only via a conditional edge after all three lead fields are confirmed. This strict routing **prevents premature tool execution**.

State (`messages`, `intent`, `lead_info`, `waiting_for`, `lead_captured`) persists across every turn in the same Python process, giving the agent full conversational memory for 5–10+ turns.

---

## 📲 WhatsApp Deployment with Webhooks

To deploy this agent on WhatsApp, you would use the **WhatsApp Business Cloud API** (Meta) with an **inbound webhook**:

### Architecture

```
User on WhatsApp
      │
      ▼
Meta WhatsApp Business API
      │  (HTTP POST to your server on each incoming message)
      ▼
FastAPI / Flask Webhook Server   ←── verifies Meta webhook token
      │
      ├── Loads per-user AgentState from Redis / DynamoDB
      │         (key = WhatsApp phone number)
      │
      ├── Appends HumanMessage → runs agent_graph.invoke(state)
      │
      ├── Saves updated state back to Redis / DynamoDB
      │
      └── POSTs reply text back to Meta Send Message API
```

### Key steps

1. **Register a webhook URL** in the Meta Developer Portal. Meta will send a `GET` verification request with a challenge token — your server must echo it back.
2. **Handle `POST` events**: each incoming WhatsApp message arrives as a JSON payload. Extract `from` (phone number) and `text.body`.
3. **Persist state per user**: store `AgentState` (serialised as JSON) in Redis keyed by phone number so each user has their own independent conversation thread.
4. **Reply via API**: after invoking the graph, send the AI response using `POST https://graph.facebook.com/v18.0/<PHONE_NUMBER_ID>/messages`.
5. **Secrets**: store `WHATSAPP_TOKEN`, `GROQ_API_KEY`, and `VERIFY_TOKEN` as environment variables.

---

## ✅ Capabilities Checklist

| Feature | Status |
|---|---|
| Intent classification (greeting / inquiry / high-intent) | ✅ |
| RAG from local JSON knowledge base | ✅ |
| Stateful multi-turn memory (LangGraph state) | ✅ |
| Incremental lead field collection (name → email → platform) | ✅ |
| Tool fires only after all 3 fields collected | ✅ |
| `mock_lead_capture()` tool execution | ✅ |

---

## 🔑 Environment Variables

| Variable | Required | Description |
|---|---|---|
| `GROQ_API_KEY` | ✅ | Free LLM API key from console.groq.com |

---

## 📌 Notes

- The LLM used is **LLaMA 3.1 8B Instant** via Groq — completely free with 14,400 requests/day.
- The knowledge base (`autostream_kb.json`) is injected as text into the system prompt on every turn. For a larger KB, swap this for a **ChromaDB / FAISS vector store** with embedding-based retrieval.
- The agent runs entirely locally — no external services except the Groq API.

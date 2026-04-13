import json
from pathlib import Path


KB_PATH = Path(__file__).parent.parent / "knowledge_base" / "autostream_kb.json"


def load_knowledge_base() -> dict:
    """Load the knowledge base JSON file."""
    with open(KB_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def build_kb_context() -> str:
    """
    Convert the entire knowledge base into a concise text block
    that can be injected into the system prompt.
    """
    kb = load_knowledge_base()
    lines = []

    lines.append(f"## Company: {kb['company']}")
    lines.append(f"{kb['description']}\n")

    lines.append("## Pricing Plans")
    for plan in kb["plans"]:
        lines.append(f"\n### {plan['name']} — ${plan['price_monthly']}/month")
        for feature in plan["features"]:
            lines.append(f"  - {feature}")

    lines.append("\n## Policies")
    for policy in kb["policies"]:
        lines.append(f"\n**{policy['topic']}:** {policy['details']}")

    lines.append("\n## FAQs")
    for faq in kb["faqs"]:
        lines.append(f"\nQ: {faq['question']}")
        lines.append(f"A: {faq['answer']}")

    return "\n".join(lines)

KB_CONTEXT: str = build_kb_context()


if __name__ == "__main__":
    print(KB_CONTEXT)


from typing import Annotated, List, Literal, Optional
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage
import operator


# Intent labels 
IntentType = Literal["greeting", "product_inquiry", "high_intent", "unknown"]



class LeadInfo(TypedDict, total=False):
    name: Optional[str]
    email: Optional[str]
    platform: Optional[str]



class AgentState(TypedDict):
    
    messages: Annotated[List[BaseMessage], operator.add]

    intent: IntentType

    lead_info: LeadInfo

    lead_captured: bool

    waiting_for: Optional[str]

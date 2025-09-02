from typing import List, Union, Dict
from langchain_core.messages.ai import AIMessageChunk
from langchain_core.messages.tool import ToolMessage

def content_to_text(content: Union[str, List[Dict[str, str]], AIMessageChunk]) -> str:
    if content is None:
        return ""
    
    if isinstance(content, str):
        return content
    elif isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict):
                if block.get("type") == "text":
                    parts.append(block.get("text", ""))
                continue

            btype = getattr(block, "type", None)
            if btype == "text":
                parts.append(getattr(block, "text", "") or "")

        return "".join(parts)
    elif isinstance(content, AIMessageChunk):
        return content.text()
    else:
         print(content)
    
    return ""

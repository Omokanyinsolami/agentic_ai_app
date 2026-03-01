from typing_extensions import TypedDict, Literal
from langgraph.graph import StateGraph, START, END

class MyState(TypedDict):
    value: int
    target: int

def increment(state: MyState) -> dict:
    return {"value": state["value"] + 1}

def should_continue(state: MyState) -> Literal["increment", END]:
    return "increment" if state["value"] < state["target"] else END

builder = StateGraph(MyState)
builder.add_node("increment", increment)

builder.add_edge(START, "increment")                      # entrypoint
builder.add_conditional_edges("increment", should_continue) # loop or end

graph = builder.compile()

result = graph.invoke({"value": 0, "target": 5})
print(f"LangGraph result: {result['value']}")
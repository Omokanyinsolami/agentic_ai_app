# Minimal CrewAI Example

from crewai import Agent, Task, Crew
from crewai.tools import tool



# Define the tool using the @tool decorator as required by CrewAI
@tool
def example_tool() -> str:
    """A simple tool that says hello."""
    return "Hello from CrewAI!"



agent = Agent(
    name="TestAgent",
    role="Greeter",
    goal="Say hello to the world.",
    backstory="A friendly agent that greets everyone.",
    tools=[example_tool]
)

task = Task(description="Say hello", agent=agent)
crew = Crew(tasks=[task])

results = crew.run()
print(f"CrewAI result: {results}")

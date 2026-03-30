# Minimal AutoGen Example (pyautogen 0.10+)
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.ui import Console
from autogen_core import CancellationToken
import asyncio

async def main():
    agent = AssistantAgent(name="assistant", model_client=None)
    print("AutoGen agent created successfully!")
    print(f"Agent name: {agent.name}")

if __name__ == "__main__":
    asyncio.run(main())

# Minimal AutoGen Example
from autogen import AssistantAgent, UserProxyAgent


assistant = AssistantAgent(name="assistant")
user = UserProxyAgent(name="user", human_input_mode="NEVER", code_execution_config={"use_docker": False})

user.initiate_chat(assistant, message="Hello, AutoGen!")

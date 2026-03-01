from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from dotenv import load_dotenv

load_dotenv()

from langgraph_agent import agent_workflow

app = Flask(__name__)
# Allow CORS from any origin for deployment flexibility
CORS(app, origins=os.getenv('CORS_ORIGINS', '*').split(','))

@app.route('/api/tasks', methods=['GET'])
def get_tasks():
	user_id = request.args.get('user_id')
	result = agent_workflow(f"show_tasks: user_id={user_id}")
	# Try to parse lines into structured data
	lines = result['messages'][-1].content.split('\n')
	tasks = []
	for line in lines:
		if line.startswith('-'):
			match = __import__('re').match(r"- \[(\d+)\] (.+?) \| status=(.+?) \| priority=(\d+) \| due=(.+?) \|", line)
			if match:
				tasks.append({
					'id': int(match.group(1)),
					'title': match.group(2),
					'status': match.group(3),
					'priority': int(match.group(4)),
					'deadline': match.group(5)
				})
	return jsonify(tasks)

@app.route('/api/tasks', methods=['POST'])
def add_task():
	data = request.json
	payload = f"add_task: {data['user_id']}, \"{data['title']}\", \"{data['description']}\", {data['deadline']}, {data['priority']}, {data['status']}"
	result = agent_workflow(payload)
	return jsonify({'message': result['messages'][-1].content})

@app.route('/api/users', methods=['GET'])
def get_users():
	result = agent_workflow("list_users:")
	lines = result['messages'][-1].content.split('\n')
	users = []
	for line in lines:
		if line.startswith('-'):
			match = __import__('re').match(r"- \[(\d+)\] (.+?) \|", line)
			if match:
				users.append({
					'id': int(match.group(1)),
					'name': match.group(2)
				})
	return jsonify(users)

@app.route('/api/users', methods=['POST'])
def create_user():
	data = request.json
	payload = f'create_user: "{data["name"]}", "{data["email"]}", "{data.get("program", "")}"'
	result = agent_workflow(payload)
	return jsonify({'message': result['messages'][-1].content})

@app.route('/api/reminders', methods=['POST'])
def send_reminder():
	data = request.json
	payload = f"reminders: user_id={data['user_id']}; days={data.get('days', 3)}; send_email=true"
	result = agent_workflow(payload)
	return jsonify({'message': result['messages'][-1].content})

if __name__ == "__main__":
	port = int(os.getenv('PORT', 5000))
	debug = os.getenv('FLASK_DEBUG', 'true').lower() == 'true'
	app.run(host='0.0.0.0', port=port, debug=debug)
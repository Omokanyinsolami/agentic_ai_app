import React, { useEffect, useState } from 'react';
import API_URL from './config';
import './App.css';

function App() {
  const [tasks, setTasks] = useState([]);
  const [users, setUsers] = useState([]);
  const [selectedUser, setSelectedUser] = useState('');
  const [newTask, setNewTask] = useState({ title: '', description: '', deadline: '', priority: 1, status: 'pending' });
  const [reminderMsg, setReminderMsg] = useState('');
  const [newUser, setNewUser] = useState({ name: '', email: '', program: '' });
  const [userMsg, setUserMsg] = useState('');
  const [taskMsg, setTaskMsg] = useState('');
  const [loading, setLoading] = useState(false);

  const fetchUsers = () => {
    fetch(`${API_URL}/api/users`)
      .then(res => res.json())
      .then(data => {
        setUsers(Array.isArray(data) ? data : []);
      })
      .catch(err => console.error('Error fetching users:', err));
  };

  useEffect(() => {
    fetchUsers();
  }, []);

  const fetchTasks = (userId) => {
    if (!userId) return;
    fetch(`${API_URL}/api/tasks?user_id=${userId}`)
      .then(res => res.json())
      .then(data => {
        setTasks(Array.isArray(data) ? data : []);
      })
      .catch(err => console.error('Error fetching tasks:', err));
  };

  const handleUserSelect = (e) => {
    setSelectedUser(e.target.value);
    fetchTasks(e.target.value);
  };

  const handleTaskInput = (e) => {
    setNewTask({ ...newTask, [e.target.name]: e.target.value });
  };

  const handleUserInput = (e) => {
    setNewUser({ ...newUser, [e.target.name]: e.target.value });
  };

  const handleAddUser = () => {
    if (!newUser.name || !newUser.email) {
      setUserMsg('Name and email are required');
      return;
    }
    setLoading(true);
    fetch(`${API_URL}/api/users`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(newUser)
    })
      .then(res => res.json())
      .then(data => {
        setUserMsg(data.message || 'User created!');
        setNewUser({ name: '', email: '', program: '' });
        fetchUsers();
      })
      .catch(err => setUserMsg('Error creating user'))
      .finally(() => setLoading(false));
  };

  const handleAddTask = () => {
    if (!selectedUser) {
      setTaskMsg('Please select a user first');
      return;
    }
    if (!newTask.title) {
      setTaskMsg('Title is required');
      return;
    }
    setLoading(true);
    fetch(`${API_URL}/api/tasks`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ...newTask, user_id: selectedUser })
    })
      .then(res => res.json())
      .then(data => {
        setTaskMsg(data.message || 'Task added!');
        setNewTask({ title: '', description: '', deadline: '', priority: 1, status: 'pending' });
        fetchTasks(selectedUser);
      })
      .catch(err => setTaskMsg('Error adding task'))
      .finally(() => setLoading(false));
  };

  const handleSendReminder = () => {
    if (!selectedUser) {
      setReminderMsg('Please select a user first');
      return;
    }
    setLoading(true);
    fetch(`${API_URL}/api/reminders`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: selectedUser, days: 5 })
    })
      .then(res => res.json())
      .then(msg => setReminderMsg(msg.message))
      .catch(err => setReminderMsg('Error sending reminder'))
      .finally(() => setLoading(false));
  };

  const getStatusClass = (status) => {
    const statusMap = {
      'pending': 'status-pending',
      'in_progress': 'status-in_progress',
      'done': 'status-done'
    };
    return statusMap[status] || 'status-pending';
  };

  return (
    <div className="app-container">
      <header className="app-header">
        <h1>📚 Academic Task Manager</h1>
        <p>Organize your academic life with intelligent task management</p>
      </header>

      {/* Create User Section */}
      <div className="card">
        <h2><span className="icon">👤</span> Create New User</h2>
        <div className="form-row">
          <input 
            name="name" 
            placeholder="Full Name" 
            value={newUser.name} 
            onChange={handleUserInput} 
          />
          <input 
            name="email" 
            placeholder="Email Address" 
            value={newUser.email} 
            onChange={handleUserInput} 
          />
          <input 
            name="program" 
            placeholder="Academic Program (optional)" 
            value={newUser.program} 
            onChange={handleUserInput} 
          />
        </div>
        <button className="btn btn-primary" onClick={handleAddUser} disabled={loading}>
          {loading ? <span className="spinner"></span> : '➕'} Create User
        </button>
        {userMsg && (
          <div className={`message ${userMsg.includes('Error') ? 'message-error' : 'message-success'}`}>
            {userMsg}
          </div>
        )}
      </div>

      {/* Select User */}
      <div className="user-select-container">
        <label>Select Active User</label>
        <select value={selectedUser} onChange={handleUserSelect}>
          <option value="">-- Choose a User --</option>
          {users.map(u => <option key={u.id} value={u.id}>{u.name}</option>)}
        </select>
        {users.length === 0 && (
          <p className="hint">No users found. Create one above to get started!</p>
        )}
      </div>

      {/* Tasks List */}
      <div className="card">
        <h2><span className="icon">📋</span> Your Tasks</h2>
        {tasks.length === 0 ? (
          <div className="empty-state">
            <div className="icon">📭</div>
            <p>{selectedUser ? 'No tasks found. Add your first task below!' : 'Select a user to view their tasks'}</p>
          </div>
        ) : (
          <ul className="task-list">
            {tasks.map(t => (
              <li key={t.id} className="task-item">
                <div>
                  <div className="task-title">{t.title}</div>
                  <div className="task-meta">
                    <span>📅 {t.deadline || 'No deadline'}</span>
                    <span className={`status-badge ${getStatusClass(t.status)}`}>{t.status}</span>
                  </div>
                </div>
                <div className={`priority priority-${t.priority}`}>{t.priority}</div>
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Add Task Section */}
      <div className="card">
        <h2><span className="icon">✏️</span> Add New Task</h2>
        <div className="form-row">
          <input 
            name="title" 
            placeholder="Task Title" 
            value={newTask.title} 
            onChange={handleTaskInput} 
          />
          <input 
            name="description" 
            placeholder="Description" 
            value={newTask.description} 
            onChange={handleTaskInput} 
          />
        </div>
        <div className="form-row">
          <input 
            name="deadline" 
            type="date"
            placeholder="Deadline" 
            value={newTask.deadline} 
            onChange={handleTaskInput} 
          />
          <select name="priority" value={newTask.priority} onChange={handleTaskInput}>
            <option value="1">Priority 1 (Highest)</option>
            <option value="2">Priority 2</option>
            <option value="3">Priority 3</option>
            <option value="4">Priority 4</option>
            <option value="5">Priority 5 (Lowest)</option>
          </select>
          <select name="status" value={newTask.status} onChange={handleTaskInput}>
            <option value="pending">Pending</option>
            <option value="in_progress">In Progress</option>
            <option value="done">Done</option>
          </select>
        </div>
        <button className="btn btn-success" onClick={handleAddTask} disabled={loading || !selectedUser}>
          {loading ? <span className="spinner"></span> : '➕'} Add Task
        </button>
        {taskMsg && (
          <div className={`message ${taskMsg.includes('Error') ? 'message-error' : 'message-success'}`}>
            {taskMsg}
          </div>
        )}
      </div>

      {/* Reminder Section */}
      <div className="card">
        <h2><span className="icon">🔔</span> Send Reminder</h2>
        <p style={{ marginBottom: '16px', color: '#718096' }}>
          Send an email reminder for tasks due in the next 5 days
        </p>
        <button className="btn btn-warning" onClick={handleSendReminder} disabled={loading || !selectedUser}>
          {loading ? <span className="spinner"></span> : '📧'} Send Reminder Email
        </button>
        {reminderMsg && (
          <div className="message message-info">{reminderMsg}</div>
        )}
      </div>
    </div>
  );
}

export default App;

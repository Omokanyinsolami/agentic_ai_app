import React, { useEffect, useState, useCallback, useMemo } from 'react';
import { 
  User, Plus, Mail, Calendar, CheckCircle, Clock, AlertCircle, 
  Bell, Send, ListTodo, GraduationCap, Trash2, RefreshCw,
  AlertTriangle, CheckCheck, Loader2, LogIn, LogOut, Key, Lock,
  MessageCircle, Bot, Zap, Edit2, X, Save, CalendarDays, Play,
  Undo2, Filter, ArrowUpDown, Wifi, WifiOff
} from 'lucide-react';
import { Icon } from '@iconify/react';
import API_URL from './config';
import { userSchema, taskSchema, validateForm, formatName } from './validation';
import './App.css';

function App() {
  // State
  const [activeTab, setActiveTab] = useState('account');
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [loginEmail, setLoginEmail] = useState('');
  const [loginPassword, setLoginPassword] = useState('');
  const [loginError, setLoginError] = useState('');
  const [tasks, setTasks] = useState([]);
  const [selectedUser, setSelectedUser] = useState('');
  const [selectedUserData, setSelectedUserData] = useState(null);
  const [newTask, setNewTask] = useState({ title: '', description: '', deadline: '', priority: 'medium', status: 'pending' });
  const [reminderMsg, setReminderMsg] = useState('');
  const [newUser, setNewUser] = useState({ name: '', email: '', program: '', password: '' });
  const [userMsg, setUserMsg] = useState('');
  const [taskMsg, setTaskMsg] = useState('');
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState({});
  const [reminderDays, setReminderDays] = useState(7);
  const [showCreateAccount, setShowCreateAccount] = useState(false);
  
  // Chat state
  const [chatMessages, setChatMessages] = useState([]);
  const [chatInput, setChatInput] = useState('');
  const [chatLoading, setChatLoading] = useState(false);
  
  // Conflicts state
  const [conflicts, setConflicts] = useState([]);
  
  // Edit task state
  const [editingTask, setEditingTask] = useState(null);
  const [editTaskData, setEditTaskData] = useState({ title: '', description: '', deadline: '', priority: 'medium', status: 'pending' });

  // Schedule state - Agentic AI Scheduling Feature
  const [schedule, setSchedule] = useState([]);
  const [availability, setAvailability] = useState([]);
  const [scheduleLoading, setScheduleLoading] = useState(false);
  const [scheduleMsg, setScheduleMsg] = useState('');
  const [newAvailability, setNewAvailability] = useState({ day_of_week: 0, start_time: '09:00', end_time: '12:00', location: '' });
  const [scheduleReasoning, setScheduleReasoning] = useState('');
  const [authToken, setAuthToken] = useState('');
  const [sessionExpiresAt, setSessionExpiresAt] = useState('');
  const [deletedTasks, setDeletedTasks] = useState([]);
  const [showDeletedTasks, setShowDeletedTasks] = useState(false);
  const [taskView, setTaskView] = useState({
    status: 'all',
    priority: 'all',
    search: '',
    sortBy: 'deadline',
    sortOrder: 'asc',
  });
  const [isOffline, setIsOffline] = useState(!navigator.onLine);
  const [offlineQueueCount, setOfflineQueueCount] = useState(() => {
    const existingQueue = localStorage.getItem('academicTaskOfflineQueue');
    if (!existingQueue) return 0;
    try {
      const parsed = JSON.parse(existingQueue);
      return Array.isArray(parsed) ? parsed.length : 0;
    } catch (err) {
      return 0;
    }
  });
  const [syncMsg, setSyncMsg] = useState('');
  const [taskCreationStartedAt, setTaskCreationStartedAt] = useState(null);
  const [avgTaskCreationSeconds, setAvgTaskCreationSeconds] = useState(() => {
    const raw = localStorage.getItem('taskCreationDurationsSec');
    if (!raw) return null;
    try {
      const parsed = JSON.parse(raw);
      if (!Array.isArray(parsed) || parsed.length === 0) return null;
      const avg = parsed.reduce((sum, value) => sum + Number(value || 0), 0) / parsed.length;
      return Number.isFinite(avg) ? avg : null;
    } catch (err) {
      return null;
    }
  });

  const visibleTasks = useMemo(() => tasks, [tasks]);
  const SESSION_STORAGE_KEY = 'academicTaskSession';
  const OFFLINE_QUEUE_KEY = 'academicTaskOfflineQueue';

  const performLocalLogout = useCallback((reason = '') => {
    setIsLoggedIn(false);
    setSelectedUser('');
    setSelectedUserData(null);
    setTasks([]);
    setDeletedTasks([]);
    setConflicts([]);
    setAvailability([]);
    setSchedule([]);
    setAuthToken('');
    setSessionExpiresAt('');
    localStorage.removeItem('academicTaskUser');
    localStorage.removeItem(SESSION_STORAGE_KEY);
    setActiveTab('account');
    if (reason) {
      setLoginError(reason);
    }
  }, []);

  const persistSession = useCallback((userData, token, expiresAt) => {
    const normalizedUser = { ...userData, id: userData.id.toString() };
    setSelectedUser(normalizedUser.id);
    setSelectedUserData(userData);
    setIsLoggedIn(true);
    setAuthToken(token || '');
    setSessionExpiresAt(expiresAt || '');
    localStorage.setItem('academicTaskUser', JSON.stringify(userData));
    localStorage.setItem(
      SESSION_STORAGE_KEY,
      JSON.stringify({ user: userData, token, expires_at: expiresAt })
    );
    setActiveTab('tasks');
  }, []);

  const queueOfflineAction = useCallback((endpoint, method, body) => {
    let queue = [];
    try {
      queue = JSON.parse(localStorage.getItem(OFFLINE_QUEUE_KEY) || '[]');
      if (!Array.isArray(queue)) {
        queue = [];
      }
    } catch (err) {
      queue = [];
    }

    queue.push({
      id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
      endpoint,
      method,
      body: body || null,
      queued_at: new Date().toISOString(),
    });

    localStorage.setItem(OFFLINE_QUEUE_KEY, JSON.stringify(queue));
    setOfflineQueueCount(queue.length);
    setSyncMsg('You are offline. Changes were queued and will sync automatically.');
  }, []);

  const apiRequest = useCallback(
    async (endpoint, options = {}, queueable = false) => {
      const method = (options.method || 'GET').toUpperCase();
      const canQueue = queueable && method !== 'GET';

      if (!navigator.onLine && canQueue) {
        queueOfflineAction(endpoint, method, options.body || null);
        return { queued: true };
      }

      const headers = {
        ...(options.headers || {}),
      };

      if (method !== 'GET' && !headers['Content-Type']) {
        headers['Content-Type'] = 'application/json';
      }

      if (authToken) {
        headers.Authorization = `Bearer ${authToken}`;
      }

      try {
        const response = await fetch(`${API_URL}${endpoint}`, {
          ...options,
          method,
          headers,
        });

        let data = {};
        try {
          data = await response.json();
        } catch (err) {
          data = {};
        }

        if (response.status === 401) {
          performLocalLogout('Session expired. Please sign in again.');
          throw new Error(data.error || 'Session expired');
        }

        if (!response.ok) {
          throw new Error(data.error || `Request failed (${response.status})`);
        }

        return data;
      } catch (err) {
        const networkLikeError = err instanceof TypeError || !navigator.onLine;
        if (canQueue && networkLikeError) {
          queueOfflineAction(endpoint, method, options.body || null);
          return { queued: true };
        }
        throw err;
      }
    },
    [authToken, performLocalLogout, queueOfflineAction]
  );

  const fetchTasks = useCallback(async () => {
    if (!selectedUser || !authToken) return;

    const params = new URLSearchParams();
    if (taskView.status !== 'all') params.set('status', taskView.status);
    if (taskView.priority !== 'all') params.set('priority', taskView.priority);
    if (taskView.search.trim()) params.set('search', taskView.search.trim());
    params.set('sort_by', taskView.sortBy);
    params.set('sort_order', taskView.sortOrder);

    const endpoint = `/api/tasks?${params.toString()}`;
    const cacheKey = `academicTaskCache:tasks:${selectedUser}:${params.toString()}`;

    try {
      const data = await apiRequest(endpoint);
      const normalized = Array.isArray(data) ? data : [];
      setTasks(normalized);
      localStorage.setItem(cacheKey, JSON.stringify(normalized));
    } catch (err) {
      const cached = localStorage.getItem(cacheKey);
      if (cached) {
        try {
          setTasks(JSON.parse(cached));
          setTaskMsg('Offline mode: showing cached tasks.');
        } catch (parseErr) {
          setTasks([]);
        }
      }
    }
  }, [apiRequest, authToken, selectedUser, taskView]);

  const fetchDeletedTasks = useCallback(async () => {
    if (!selectedUser || !authToken) return;

    const cacheKey = `academicTaskCache:deleted:${selectedUser}`;
    try {
      const data = await apiRequest('/api/tasks/deleted');
      const normalized = Array.isArray(data) ? data : [];
      setDeletedTasks(normalized);
      localStorage.setItem(cacheKey, JSON.stringify(normalized));
    } catch (err) {
      const cached = localStorage.getItem(cacheKey);
      if (cached) {
        try {
          setDeletedTasks(JSON.parse(cached));
        } catch (parseErr) {
          setDeletedTasks([]);
        }
      }
    }
  }, [apiRequest, authToken, selectedUser]);

  const fetchConflicts = useCallback(async () => {
    if (!selectedUser || !authToken) return;

    const cacheKey = `academicTaskCache:conflicts:${selectedUser}`;
    try {
      const data = await apiRequest('/api/tasks/conflicts');
      const normalized = data.conflicts || [];
      setConflicts(normalized);
      localStorage.setItem(cacheKey, JSON.stringify(normalized));
    } catch (err) {
      const cached = localStorage.getItem(cacheKey);
      if (cached) {
        try {
          setConflicts(JSON.parse(cached));
        } catch (parseErr) {
          setConflicts([]);
        }
      }
    }
  }, [apiRequest, authToken, selectedUser]);

  const fetchAvailability = useCallback(async () => {
    if (!selectedUser || !authToken) return;

    const cacheKey = `academicTaskCache:availability:${selectedUser}`;
    try {
      const data = await apiRequest('/api/availability');
      const normalized = Array.isArray(data) ? data : [];
      setAvailability(normalized);
      localStorage.setItem(cacheKey, JSON.stringify(normalized));
    } catch (err) {
      const cached = localStorage.getItem(cacheKey);
      if (cached) {
        try {
          setAvailability(JSON.parse(cached));
          setScheduleMsg('Offline mode: showing cached availability.');
        } catch (parseErr) {
          setAvailability([]);
        }
      }
    }
  }, [apiRequest, authToken, selectedUser]);

  const fetchSchedule = useCallback(async () => {
    if (!selectedUser || !authToken) return;

    const cacheKey = `academicTaskCache:schedule:${selectedUser}`;
    try {
      const data = await apiRequest('/api/schedule');
      const normalized = Array.isArray(data) ? data : [];
      setSchedule(normalized);
      localStorage.setItem(cacheKey, JSON.stringify(normalized));
    } catch (err) {
      const cached = localStorage.getItem(cacheKey);
      if (cached) {
        try {
          setSchedule(JSON.parse(cached));
          setScheduleMsg('Offline mode: showing cached schedule.');
        } catch (parseErr) {
          setSchedule([]);
        }
      }
    }
  }, [apiRequest, authToken, selectedUser]);

  const processOfflineQueue = useCallback(async () => {
    if (!authToken || !navigator.onLine) return;

    let queue = [];
    try {
      queue = JSON.parse(localStorage.getItem(OFFLINE_QUEUE_KEY) || '[]');
      if (!Array.isArray(queue) || queue.length === 0) {
        setOfflineQueueCount(0);
        return;
      }
    } catch (err) {
      setOfflineQueueCount(0);
      return;
    }

    const remaining = [];
    let synced = 0;

    for (const item of queue) {
      try {
        const response = await fetch(`${API_URL}${item.endpoint}`, {
          method: item.method,
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${authToken}`,
          },
          body: item.body,
        });

        if (response.status === 401) {
          performLocalLogout('Session expired before queued updates could sync.');
          return;
        }

        if (!response.ok) {
          throw new Error(`Sync failed for ${item.endpoint}`);
        }

        synced += 1;
      } catch (err) {
        remaining.push(item);
      }
    }

    localStorage.setItem(OFFLINE_QUEUE_KEY, JSON.stringify(remaining));
    setOfflineQueueCount(remaining.length);

    if (synced > 0) {
      setSyncMsg(`Synced ${synced} queued change(s).`);
      await Promise.all([
        fetchTasks(),
        fetchDeletedTasks(),
        fetchConflicts(),
        fetchAvailability(),
        fetchSchedule(),
      ]);
      await apiRequest(
        '/api/schedule/adapt',
        {
          method: 'POST',
          body: JSON.stringify({ trigger: 'offline_sync' }),
        },
        false
      ).catch(() => {});
    }
  }, [apiRequest, authToken, fetchAvailability, fetchConflicts, fetchDeletedTasks, fetchSchedule, fetchTasks, performLocalLogout]);

  const triggerAutoAdaptation = useCallback(async (trigger) => {
    if (!isLoggedIn) return;

    try {
      const data = await apiRequest(
        '/api/schedule/adapt',
        {
          method: 'POST',
          body: JSON.stringify({ trigger }),
        },
        true
      );

      if (data?.queued) {
        setScheduleMsg('Adaptation queued for sync when you are online.');
        return;
      }

      fetchSchedule();
    } catch (err) {
      console.error('Adaptation trigger failed:', err);
    }
  }, [apiRequest, fetchSchedule, isLoggedIn]);

  // Check for stored session
  useEffect(() => {
    const storedSession = localStorage.getItem(SESSION_STORAGE_KEY);
    if (!storedSession) {
      localStorage.removeItem('academicTaskUser');
      return;
    }

    try {
      const parsed = JSON.parse(storedSession);
      const userData = parsed.user;
      const token = parsed.token;
      const expiresAt = parsed.expires_at;

      if (!userData || !token || !expiresAt) {
        performLocalLogout();
        return;
      }

      if (new Date(expiresAt).getTime() <= Date.now()) {
        performLocalLogout('Stored session expired. Please sign in again.');
        return;
      }

      setSelectedUser(userData.id.toString());
      setSelectedUserData(userData);
      setIsLoggedIn(true);
      setAuthToken(token);
      setSessionExpiresAt(expiresAt);
      setActiveTab('tasks');
    } catch (err) {
      performLocalLogout();
    }
  }, [performLocalLogout]);

  useEffect(() => {
    if (!authToken || !sessionExpiresAt) return;

    const expiryMs = new Date(sessionExpiresAt).getTime() - Date.now();
    if (expiryMs <= 0) {
      performLocalLogout('Session expired. Please sign in again.');
      return;
    }

    const timer = setTimeout(() => {
      performLocalLogout('Session expired. Please sign in again.');
    }, expiryMs);

    return () => clearTimeout(timer);
  }, [authToken, sessionExpiresAt, performLocalLogout]);

  useEffect(() => {
    const onOnline = () => {
      setIsOffline(false);
      processOfflineQueue();
    };
    const onOffline = () => setIsOffline(true);

    window.addEventListener('online', onOnline);
    window.addEventListener('offline', onOffline);

    return () => {
      window.removeEventListener('online', onOnline);
      window.removeEventListener('offline', onOffline);
    };
  }, [processOfflineQueue]);

  useEffect(() => {
    if (process.env.NODE_ENV !== 'production' || !('serviceWorker' in navigator)) return undefined;

    const onSwMessage = (event) => {
      if (event.data?.type === 'SYNC_OFFLINE_QUEUE') {
        processOfflineQueue();
      }
    };

    navigator.serviceWorker.addEventListener('message', onSwMessage);
    return () => navigator.serviceWorker.removeEventListener('message', onSwMessage);
  }, [processOfflineQueue]);

  useEffect(() => {
    if (!selectedUser || !authToken) return;

    fetchTasks();
    fetchDeletedTasks();
    fetchConflicts();
  }, [authToken, fetchConflicts, fetchDeletedTasks, fetchTasks, selectedUser]);

  useEffect(() => {
    if (!selectedUser || !authToken) return;

    fetchAvailability();
    fetchSchedule();
  }, [authToken, fetchAvailability, fetchSchedule, selectedUser]);

  useEffect(() => {
    if (authToken && !isOffline && offlineQueueCount > 0) {
      processOfflineQueue();
    }
  }, [authToken, isOffline, offlineQueueCount, processOfflineQueue]);

  // Generate AI Schedule
  const handleGenerateSchedule = async () => {
    if (!selectedUser) return;

    setScheduleLoading(true);
    setScheduleMsg('');
    setScheduleReasoning('');

    try {
      const data = await apiRequest('/api/schedule/generate', {
        method: 'POST',
        body: JSON.stringify({ days_ahead: 7 }),
      });

      if (data.error) {
        setScheduleMsg(data.error);
      } else {
        setSchedule(data.schedule || []);
        setScheduleReasoning(data.reasoning || '');
        setScheduleMsg(data.success ? 'Schedule generated successfully!' : 'Schedule generation had issues.');
        if (data.warnings && data.warnings.length > 0) {
          setScheduleMsg((prev) => prev + ' ' + data.warnings.join(' '));
        }
      }
    } catch (err) {
      setScheduleMsg(err.message || 'Error generating schedule');
    } finally {
      setScheduleLoading(false);
    }
  };

  // Add availability slot
  const handleAddAvailability = async () => {
    if (!selectedUser) return;

    try {
      const data = await apiRequest(
        '/api/availability',
        {
          method: 'POST',
          body: JSON.stringify(newAvailability),
        },
        true
      );

      if (data?.queued) {
        setScheduleMsg('Offline mode: availability change queued for sync.');
        return;
      }

      if (data.error) {
        setScheduleMsg(data.error);
      } else {
        setScheduleMsg('Availability slot added!');
        fetchAvailability();
        setNewAvailability({ day_of_week: 0, start_time: '09:00', end_time: '12:00', location: '' });
        triggerAutoAdaptation('availability_added_ui');
      }
    } catch (err) {
      setScheduleMsg(err.message || 'Error adding availability');
    }
  };

  // Delete availability slot
  const handleDeleteAvailability = async (slotId) => {
    try {
      const data = await apiRequest(
        `/api/availability/${slotId}`,
        { method: 'DELETE' },
        true
      );

      if (data?.queued) {
        setScheduleMsg('Offline mode: availability deletion queued for sync.');
        return;
      }

      if (!data.error) {
        fetchAvailability();
        setScheduleMsg('Availability slot removed');
        triggerAutoAdaptation('availability_deleted_ui');
      }
    } catch (err) {
      console.error('Error deleting availability:', err);
    }
  };

  // Handle chat message
  const handleChat = async () => {
    if (!chatInput.trim() || chatLoading) return;

    const userMessage = chatInput.trim();
    setChatMessages((prev) => [...prev, { role: 'user', content: userMessage }]);
    setChatInput('');
    setChatLoading(true);

    try {
      const data = await apiRequest('/api/chat', {
        method: 'POST',
        body: JSON.stringify({ message: userMessage }),
      });

      if (data.error) {
        setChatMessages((prev) => [...prev, { role: 'assistant', content: `Error: ${data.error}` }]);
      } else {
        setChatMessages((prev) => [...prev, { role: 'assistant', content: data.response }]);
        fetchTasks();
        fetchDeletedTasks();
        fetchConflicts();
      }
    } catch (err) {
      setChatMessages((prev) => [...prev, { role: 'assistant', content: err.message || 'Error connecting to server' }]);
    } finally {
      setChatLoading(false);
    }
  };

  // Login by email and password
  const handleLogin = async () => {
    if (!loginEmail.trim()) {
      setLoginError('Please enter your email address');
      return;
    }
    if (!loginPassword) {
      setLoginError('Please enter your password');
      return;
    }

    setLoading(true);
    setLoginError('');

    try {
      const response = await fetch(`${API_URL}/api/users/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: loginEmail.trim().toLowerCase(), password: loginPassword }),
      });
      const data = await response.json();

      if (!response.ok || data.error) {
        setLoginError(data.error || 'Login failed');
      } else if (data.user && data.token && data.expires_at) {
        persistSession(data.user, data.token, data.expires_at);
        setLoginEmail('');
        setLoginPassword('');
      } else {
        setLoginError('Invalid login response from server');
      }
    } catch (err) {
      setLoginError('Error connecting to server');
    } finally {
      setLoading(false);
    }
  };

  // Logout
  const handleLogout = async () => {
    try {
      if (authToken) {
        await fetch(`${API_URL}/api/users/logout`, {
          method: 'POST',
          headers: { Authorization: `Bearer ${authToken}` },
        });
      }
    } catch (err) {
      // ignore network errors during logout
    } finally {
      performLocalLogout();
    }
  };

  const recordTaskCreationDuration = useCallback(() => {
    if (!taskCreationStartedAt) return;

    const seconds = (Date.now() - taskCreationStartedAt) / 1000;
    let durations = [];
    try {
      durations = JSON.parse(localStorage.getItem('taskCreationDurationsSec') || '[]');
      if (!Array.isArray(durations)) durations = [];
    } catch (err) {
      durations = [];
    }

    durations.push(seconds);
    const capped = durations.slice(-30);
    localStorage.setItem('taskCreationDurationsSec', JSON.stringify(capped));
    const avg = capped.reduce((sum, value) => sum + Number(value || 0), 0) / capped.length;
    setAvgTaskCreationSeconds(Number.isFinite(avg) ? avg : null);
    setTaskCreationStartedAt(null);
  }, [taskCreationStartedAt]);

  const handleTaskInput = (e) => {
    const { name, value } = e.target;
    if (!taskCreationStartedAt && value.trim()) {
      setTaskCreationStartedAt(Date.now());
    }
    setNewTask((prev) => ({ ...prev, [name]: value }));
    if (errors[name]) {
      setErrors((prev) => ({ ...prev, [name]: null }));
    }
  };

  const handleUserInput = (e) => {
    const { name, value } = e.target;
    setNewUser((prev) => ({ ...prev, [name]: value }));
    if (errors[name]) {
      setErrors((prev) => ({ ...prev, [name]: null }));
    }
  };

  const handleAddUser = async () => {
    if (!newUser.password || newUser.password.length < 6) {
      setErrors((prev) => ({ ...prev, password: 'Password must be at least 6 characters' }));
      setUserMsg('Please fix the validation errors');
      return;
    }

    const validation = validateForm(userSchema, newUser);
    if (!validation.success) {
      setErrors(validation.errors);
      setUserMsg('Please fix the validation errors');
      return;
    }

    setLoading(true);
    setErrors({});

    const formattedUser = {
      ...newUser,
      name: formatName(newUser.name),
    };

    try {
      const response = await fetch(`${API_URL}/api/users`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formattedUser),
      });
      const data = await response.json();

      if (!response.ok || data.error) {
        setUserMsg(data.error || 'Error creating account');
      } else {
        setUserMsg(data.message || 'Account created successfully! You can now login.');
        setNewUser({ name: '', email: '', program: '', password: '' });
        setShowCreateAccount(false);

        if (data.user && data.token && data.expires_at) {
          persistSession(data.user, data.token, data.expires_at);
        }
      }
    } catch (err) {
      setUserMsg('Error creating account');
    } finally {
      setLoading(false);
    }
  };

  const handleAddTask = async () => {
    if (!isLoggedIn) {
      setTaskMsg('Please login first');
      return;
    }

    const validation = validateForm(taskSchema, newTask);
    if (!validation.success) {
      setErrors(validation.errors);
      setTaskMsg('Please fix the validation errors');
      return;
    }

    setLoading(true);
    setErrors({});

    try {
      const data = await apiRequest(
        '/api/tasks',
        {
          method: 'POST',
          body: JSON.stringify(newTask),
        },
        true
      );

      if (data?.queued) {
        setTaskMsg('Offline mode: task creation queued for sync.');
        return;
      }

      if (data.error) {
        setTaskMsg(data.error);
      } else {
        setTaskMsg(data.message || 'Task added successfully!');
        setNewTask({ title: '', description: '', deadline: '', priority: 'medium', status: 'pending' });
        recordTaskCreationDuration();
        fetchTasks();
        fetchConflicts();
        triggerAutoAdaptation('task_created_ui');
      }
    } catch (err) {
      setTaskMsg(err.message || 'Error adding task');
    } finally {
      setLoading(false);
    }
  };

  const handleSendReminder = async () => {
    if (!isLoggedIn) {
      setReminderMsg('Please login first');
      return;
    }

    setLoading(true);
    try {
      const msg = await apiRequest('/api/reminders', {
        method: 'POST',
        body: JSON.stringify({ days: reminderDays }),
      });
      setReminderMsg(msg.message || 'Reminder sent!');
    } catch (err) {
      setReminderMsg(err.message || 'Error sending reminder');
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteTask = async (taskId) => {
    if (!window.confirm('Are you sure you want to delete this task?')) return;

    try {
      const data = await apiRequest(`/api/tasks/${taskId}`, { method: 'DELETE' }, true);
      if (data?.queued) {
        setTaskMsg('Offline mode: task deletion queued for sync.');
        return;
      }

      fetchTasks();
      fetchDeletedTasks();
      fetchConflicts();
      setTaskMsg('Task deleted successfully');
      triggerAutoAdaptation('task_deleted_ui');
    } catch (err) {
      setTaskMsg(err.message || 'Error deleting task');
    }
  };

  const handleRestoreTask = async (taskId) => {
    try {
      const data = await apiRequest(`/api/tasks/${taskId}/restore`, { method: 'POST' }, true);
      if (data?.queued) {
        setTaskMsg('Offline mode: task restore queued for sync.');
        return;
      }

      fetchTasks();
      fetchDeletedTasks();
      fetchConflicts();
      setTaskMsg('Task restored successfully');
      triggerAutoAdaptation('task_restored_ui');
    } catch (err) {
      setTaskMsg(err.message || 'Error restoring task');
    }
  };

  const handleEditTask = (task) => {
    setEditingTask(task.id);
    setEditTaskData({
      title: task.title || '',
      description: task.description || '',
      deadline: task.deadline || '',
      priority: task.priority || 'medium',
      status: task.status || 'pending',
    });
  };

  const handleCancelEdit = () => {
    setEditingTask(null);
    setEditTaskData({ title: '', description: '', deadline: '', priority: 'medium', status: 'pending' });
  };

  const handleUpdateTask = async () => {
    if (!editingTask) return;

    setLoading(true);
    try {
      const data = await apiRequest(
        `/api/tasks/${editingTask}`,
        {
          method: 'PUT',
          body: JSON.stringify(editTaskData),
        },
        true
      );

      if (data?.queued) {
        setTaskMsg('Offline mode: task update queued for sync.');
        handleCancelEdit();
        return;
      }

      if (data.error) {
        setTaskMsg(data.error);
      } else {
        setTaskMsg('Task updated successfully!');
        fetchTasks();
        fetchConflicts();
        handleCancelEdit();
        triggerAutoAdaptation('task_updated_ui');
      }
    } catch (err) {
      setTaskMsg(err.message || 'Error updating task');
    } finally {
      setLoading(false);
    }
  };

  const handleQuickStatusUpdate = async (taskId, newStatus) => {
    try {
      const data = await apiRequest(
        `/api/tasks/${taskId}`,
        {
          method: 'PUT',
          body: JSON.stringify({ status: newStatus }),
        },
        true
      );

      if (data?.queued) {
        setTaskMsg('Offline mode: status update queued for sync.');
        return;
      }

      if (!data.error) {
        fetchTasks();
        fetchConflicts();
        setTaskMsg(`Task marked as ${newStatus.replace('_', ' ')}`);
        triggerAutoAdaptation('task_status_updated_ui');
      }
    } catch (err) {
      console.error('Error updating status:', err);
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'completed':
      case 'done':
        return <CheckCircle className="status-icon completed" />;
      case 'in_progress':
        return <Clock className="status-icon in-progress" />;
      default:
        return <AlertCircle className="status-icon pending" />;
    }
  };

  const getPriorityClass = (priority) => {
    if (typeof priority === 'number') {
      if (priority <= 2) return 'high';
      if (priority <= 3) return 'medium';
      return 'low';
    }
    return priority || 'medium';
  };
  const tabs = [
    { id: 'account', label: isLoggedIn ? 'My Account' : 'Login', icon: isLoggedIn ? <User size={18} /> : <LogIn size={18} /> },
    { id: 'tasks', label: 'Tasks', icon: <ListTodo size={18} />, requiresLogin: true },
    { id: 'schedule', label: 'AI Schedule', icon: <CalendarDays size={18} />, requiresLogin: true },
    { id: 'chat', label: 'AI Chat', icon: <MessageCircle size={18} />, requiresLogin: true },
    { id: 'reminders', label: 'Reminders', icon: <Bell size={18} />, requiresLogin: true }
  ];

  return (
    <div className="app-wrapper">
      <header className="app-header">
        <div className="header-content">
          <div className="logo-section">
            <Icon icon="mdi:school" className="logo-icon" />
            <div>
              <h1>Academic Task Manager</h1>
              <p>Intelligent task management powered by Agentic AI</p>
            </div>
          </div>
          {isLoggedIn && selectedUserData && (
            <div className="active-user-section">
              <div className="active-user-badge">
                <User size={16} />
                <span>{selectedUserData.name}</span>
              </div>
              <div className={`connection-badge ${isOffline ? 'offline' : 'online'}`}>
                {isOffline ? <WifiOff size={14} /> : <Wifi size={14} />}
                <span>{isOffline ? 'Offline' : 'Online'}</span>
              </div>
              {offlineQueueCount > 0 && (
                <div className="queue-badge">
                  <RefreshCw size={12} />
                  <span>{offlineQueueCount} queued</span>
                </div>
              )}
              <button className="btn btn-logout" onClick={handleLogout}>
                <LogOut size={16} />
                Logout
              </button>
            </div>
          )}
        </div>
      </header>

      <nav className="tab-navigation">
        {tabs.map(tab => (
          <button
            key={tab.id}
            className={`tab-button ${activeTab === tab.id ? 'active' : ''} ${tab.requiresLogin && !isLoggedIn ? 'disabled' : ''}`}
            onClick={() => {
              if (tab.requiresLogin && !isLoggedIn) {
                setActiveTab('account');
                setLoginError('Please login first to access ' + tab.label);
              } else {
                setActiveTab(tab.id);
              }
            }}
          >
            {tab.icon}
            <span>{tab.label}</span>
          </button>
        ))}
      </nav>

      <main className="main-content full-height">
        {syncMsg && (
          <div className={`message ${isOffline ? 'warning' : 'success'}`}>
            <RefreshCw size={14} />
            {syncMsg}
          </div>
        )}
        {activeTab === 'account' && (
          <div className="tab-content account-content">
            {!isLoggedIn ? (
              <div className="auth-container">
                {!showCreateAccount ? (
                  <div className="auth-panel login-panel">
                    <div className="auth-header">
                      <Key size={48} className="auth-icon" />
                      <h2>Welcome Back</h2>
                      <p>Sign in with your email to access your tasks</p>
                    </div>
                    
                    <div className="auth-body">
                      <div className="form-group">
                        <label>
                          <Mail size={16} />
                          Email Address
                        </label>
                        <input
                          type="email"
                          placeholder="Enter your email address"
                          value={loginEmail}
                          onChange={(e) => setLoginEmail(e.target.value)}
                          className={loginError ? 'error' : ''}
                        />
                      </div>

                      <div className="form-group">
                        <label>
                          <Lock size={16} />
                          Password
                        </label>
                        <input
                          type="password"
                          placeholder="Enter your password"
                          value={loginPassword}
                          onChange={(e) => setLoginPassword(e.target.value)}
                          onKeyPress={(e) => e.key === 'Enter' && handleLogin()}
                          className={loginError ? 'error' : ''}
                        />
                        {loginError && <span className="error-text">{loginError}</span>}
                      </div>

                      <button 
                        className="btn btn-primary btn-full btn-large" 
                        onClick={handleLogin}
                        disabled={loading}
                      >
                        {loading ? <Loader2 className="spin" size={20} /> : <LogIn size={20} />}
                        Sign In
                      </button>

                      <div className="auth-divider">
                        <span>or</span>
                      </div>

                      <button 
                        className="btn btn-secondary btn-full"
                        onClick={() => setShowCreateAccount(true)}
                      >
                        <Plus size={18} />
                        Create New Account
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="auth-panel create-panel">
                    <div className="auth-header">
                      <GraduationCap size={48} className="auth-icon" />
                      <h2>Create Account</h2>
                      <p>Set up your academic task management profile</p>
                    </div>

                    <div className="auth-body">
                      <div className="form-group">
                        <label>
                          <User size={16} />
                          Full Name <span className="required">*</span>
                        </label>
                        <input
                          name="name"
                          placeholder="e.g., John Smith"
                          value={newUser.name}
                          onChange={handleUserInput}
                          className={errors.name ? 'error' : ''}
                        />
                        {errors.name && <span className="error-text">{errors.name}</span>}
                        <span className="hint">First name followed by last name</span>
                      </div>

                      <div className="form-group">
                        <label>
                          <Mail size={16} />
                          Email Address <span className="required">*</span>
                        </label>
                        <input
                          name="email"
                          type="email"
                          placeholder="e.g., john.smith@gmail.com"
                          value={newUser.email}
                          onChange={handleUserInput}
                          className={errors.email ? 'error' : ''}
                        />
                        {errors.email && <span className="error-text">{errors.email}</span>}
                        <span className="hint">Use Gmail, Yahoo, Outlook, or educational email</span>
                      </div>

                      <div className="form-group">
                        <label>
                          <GraduationCap size={16} />
                          Academic Program
                        </label>
                        <input
                          name="program"
                          placeholder="e.g., MSc Computer Science"
                          value={newUser.program}
                          onChange={handleUserInput}
                        />
                      </div>

                      <div className="form-group">
                        <label>
                          <Lock size={16} />
                          Password <span className="required">*</span>
                        </label>
                        <input
                          name="password"
                          type="password"
                          placeholder="At least 6 characters"
                          value={newUser.password}
                          onChange={handleUserInput}
                          className={errors.password ? 'error' : ''}
                        />
                        {errors.password && <span className="error-text">{errors.password}</span>}
                        <span className="hint">Password must be at least 6 characters</span>
                      </div>

                      <button 
                        className="btn btn-primary btn-full btn-large" 
                        onClick={handleAddUser}
                        disabled={loading}
                      >
                        {loading ? <Loader2 className="spin" size={20} /> : <CheckCircle size={20} />}
                        Create Account
                      </button>

                      {userMsg && (
                        <div className={`message ${userMsg.includes('Error') || userMsg.includes('fix') ? 'error' : 'success'}`}>
                          {userMsg.includes('Error') ? <AlertTriangle size={16} /> : <CheckCheck size={16} />}
                          {userMsg}
                        </div>
                      )}

                      <button 
                        className="btn btn-text btn-full"
                        onClick={() => {
                          setShowCreateAccount(false);
                          setNewUser({ name: '', email: '', program: '', password: '' });
                          setErrors({});
                          setUserMsg('');
                        }}
                      >
                        Back to Login
                      </button>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="account-dashboard">
                <div className="profile-section">
                  <div className="profile-card">
                    <div className="profile-avatar">
                      <User size={64} />
                    </div>
                    <div className="profile-info">
                      <h2>{selectedUserData?.name}</h2>
                      <p className="profile-email">
                        <Mail size={16} />
                        {selectedUserData?.email}
                      </p>
                      {selectedUserData?.program && (
                        <p className="profile-program">
                          <GraduationCap size={16} />
                          {selectedUserData?.program}
                        </p>
                      )}
                    </div>
                  </div>

                  <div className="stats-grid">
                    <div className="stat-card">
                      <ListTodo size={32} />
                      <div className="stat-number">{tasks.length}</div>
                      <div className="stat-label">Total Tasks</div>
                    </div>
                    <div className="stat-card">
                      <CheckCircle size={32} />
                      <div className="stat-number">{tasks.filter(t => t.status === 'completed' || t.status === 'done').length}</div>
                      <div className="stat-label">Completed</div>
                    </div>
                    <div className="stat-card">
                      <Clock size={32} />
                      <div className="stat-number">{tasks.filter(t => t.status === 'in_progress').length}</div>
                      <div className="stat-label">In Progress</div>
                    </div>
                    <div className="stat-card">
                      <AlertCircle size={32} />
                      <div className="stat-number">{tasks.filter(t => t.status === 'pending' || !t.status).length}</div>
                      <div className="stat-label">Pending</div>
                    </div>
                  </div>
                </div>

                <div className="quick-actions">
                  <h3>Quick Actions</h3>
                  <div className="action-buttons">
                    <button className="btn btn-primary" onClick={() => setActiveTab('tasks')}>
                      <Plus size={18} />
                      Add New Task
                    </button>
                    <button className="btn btn-secondary" onClick={() => setActiveTab('reminders')}>
                      <Bell size={18} />
                      Send Reminder
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === 'tasks' && (
          <div className="tab-content">
            {!isLoggedIn ? (
              <div className="alert-banner">
                <AlertCircle size={20} />
                <span>Please login to manage your tasks</span>
                <button className="btn btn-small" onClick={() => setActiveTab('account')}>
                  Go to Login
                </button>
              </div>
            ) : (
              <div className="split-layout tasks-layout">
                <div className="panel">
                  <div className="panel-header">
                    <Plus size={20} />
                    <h2>Add New Task</h2>
                  </div>
                  <div className="panel-body">
                    <div className="form-group">
                      <label>
                        <Icon icon="mdi:format-title" />
                        Task Title <span className="required">*</span>
                      </label>
                      <input
                        name="title"
                        placeholder="e.g., Complete Chapter 3 Review"
                        value={newTask.title}
                        onChange={handleTaskInput}
                        className={errors.title ? 'error' : ''}
                      />
                      {errors.title && <span className="error-text">{errors.title}</span>}
                    </div>

                    <div className="form-group">
                      <label>
                        <Icon icon="mdi:text" />
                        Description
                      </label>
                      <textarea
                        name="description"
                        placeholder="Add task details..."
                        value={newTask.description}
                        onChange={handleTaskInput}
                        rows={3}
                      />
                    </div>

                    <div className="form-row">
                      <div className="form-group">
                        <label>
                          <Calendar size={16} />
                          Deadline
                        </label>
                        <input
                          name="deadline"
                          type="date"
                          value={newTask.deadline}
                          onChange={handleTaskInput}
                          min={new Date().toISOString().split('T')[0]}
                          className={errors.deadline ? 'error' : ''}
                        />
                        {errors.deadline && <span className="error-text">{errors.deadline}</span>}
                      </div>

                      <div className="form-group">
                        <label>
                          <Icon icon="mdi:flag" />
                          Priority
                        </label>
                        <select 
                          name="priority" 
                          value={newTask.priority} 
                          onChange={handleTaskInput}
                        >
                          <option value="high">High</option>
                          <option value="medium">Medium</option>
                          <option value="low">Low</option>
                        </select>
                      </div>
                    </div>

                    <div className="form-group">
                      <label>
                        <Icon icon="mdi:progress-check" />
                        Status
                      </label>
                      <select 
                        name="status" 
                        value={newTask.status} 
                        onChange={handleTaskInput}
                      >
                        <option value="pending">Pending</option>
                        <option value="in_progress">In Progress</option>
                        <option value="completed">Completed</option>
                      </select>
                    </div>

                    <button 
                      className="btn btn-success btn-full" 
                      onClick={handleAddTask} 
                      disabled={loading}
                    >
                      {loading ? <Loader2 className="spin" size={18} /> : <Plus size={18} />}
                      Add Task
                    </button>

                    {avgTaskCreationSeconds !== null && (
                      <p className="ux-metric">
                        Avg task creation time: {avgTaskCreationSeconds.toFixed(1)}s
                      </p>
                    )}

                    {taskMsg && (
                      <div className={`message ${taskMsg.includes('Error') || taskMsg.includes('fix') ? 'error' : 'success'}`}>
                        {taskMsg.includes('Error') ? <AlertTriangle size={16} /> : <CheckCheck size={16} />}
                        {taskMsg}
                      </div>
                    )}
                  </div>
                </div>

                <div className="panel">
                  <div className="panel-header">
                    <ListTodo size={20} />
                    <h2>Tasks for {selectedUserData?.name || 'User'}</h2>
                    <span className="badge">{visibleTasks.length}</span>
                    <button
                      className="btn-icon"
                      onClick={() => {
                        fetchTasks();
                        fetchDeletedTasks();
                        fetchConflicts();
                      }}
                      title="Refresh tasks"
                    >
                      <RefreshCw size={16} />
                    </button>
                    <button
                      className="btn-icon"
                      onClick={() => setShowDeletedTasks((prev) => !prev)}
                      title="Show deleted tasks"
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>
                  <div className="panel-body">
                    <div className="task-filters">
                      <div className="filter-field">
                        <label>
                          <Filter size={14} />
                          Search
                        </label>
                        <input
                          type="text"
                          placeholder="Search title or description"
                          value={taskView.search}
                          onChange={(e) => setTaskView((prev) => ({ ...prev, search: e.target.value }))}
                        />
                      </div>
                      <div className="filter-field">
                        <label>Status</label>
                        <select
                          value={taskView.status}
                          onChange={(e) => setTaskView((prev) => ({ ...prev, status: e.target.value }))}
                        >
                          <option value="all">All</option>
                          <option value="pending">Pending</option>
                          <option value="in_progress">In Progress</option>
                          <option value="completed">Completed</option>
                        </select>
                      </div>
                      <div className="filter-field">
                        <label>Priority</label>
                        <select
                          value={taskView.priority}
                          onChange={(e) => setTaskView((prev) => ({ ...prev, priority: e.target.value }))}
                        >
                          <option value="all">All</option>
                          <option value="high">High</option>
                          <option value="medium">Medium</option>
                          <option value="low">Low</option>
                        </select>
                      </div>
                      <div className="filter-field">
                        <label>
                          <ArrowUpDown size={14} />
                          Sort By
                        </label>
                        <select
                          value={taskView.sortBy}
                          onChange={(e) => setTaskView((prev) => ({ ...prev, sortBy: e.target.value }))}
                        >
                          <option value="deadline">Deadline</option>
                          <option value="priority">Priority</option>
                          <option value="created_at">Created</option>
                          <option value="title">Title</option>
                          <option value="status">Status</option>
                        </select>
                      </div>
                      <div className="filter-field">
                        <label>Order</label>
                        <select
                          value={taskView.sortOrder}
                          onChange={(e) => setTaskView((prev) => ({ ...prev, sortOrder: e.target.value }))}
                        >
                          <option value="asc">Ascending</option>
                          <option value="desc">Descending</option>
                        </select>
                      </div>
                    </div>

                    {visibleTasks.length === 0 ? (
                      <div className="empty-state">
                        <Icon icon="mdi:clipboard-text-outline" className="empty-icon" />
                        <p>No tasks match your current filters</p>
                        <span>Adjust filters or create a new task</span>
                      </div>
                    ) : (
                      <div className="task-list">
                        {visibleTasks.map(task => (
                          <div key={task.id} className={`task-card ${editingTask === task.id ? 'editing' : ''}`}>
                            {editingTask === task.id ? (
                              // Edit mode
                              <div className="task-edit-form">
                                <div className="edit-form-header">
                                  <h4>Edit Task</h4>
                                  <button className="btn-icon" onClick={handleCancelEdit} title="Cancel">
                                    <X size={16} />
                                  </button>
                                </div>
                                <div className="edit-form-body">
                                  <div className="form-group">
                                    <label>Title</label>
                                    <input
                                      type="text"
                                      className="input"
                                      value={editTaskData.title}
                                      onChange={(e) => setEditTaskData(prev => ({ ...prev, title: e.target.value }))}
                                    />
                                  </div>
                                  <div className="form-group">
                                    <label>Description</label>
                                    <textarea
                                      className="input"
                                      value={editTaskData.description}
                                      onChange={(e) => setEditTaskData(prev => ({ ...prev, description: e.target.value }))}
                                    />
                                  </div>
                                  <div className="form-row">
                                    <div className="form-group">
                                      <label>Deadline</label>
                                      <input
                                        type="date"
                                        className="input"
                                        value={editTaskData.deadline}
                                        onChange={(e) => setEditTaskData(prev => ({ ...prev, deadline: e.target.value }))}
                                      />
                                    </div>
                                    <div className="form-group">
                                      <label>Priority</label>
                                      <select
                                        className="input"
                                        value={editTaskData.priority}
                                        onChange={(e) => setEditTaskData(prev => ({ ...prev, priority: e.target.value }))}
                                      >
                                        <option value="high">High</option>
                                        <option value="medium">Medium</option>
                                        <option value="low">Low</option>
                                      </select>
                                    </div>
                                    <div className="form-group">
                                      <label>Status</label>
                                      <select
                                        className="input"
                                        value={editTaskData.status}
                                        onChange={(e) => setEditTaskData(prev => ({ ...prev, status: e.target.value }))}
                                      >
                                        <option value="pending">Pending</option>
                                        <option value="in_progress">In Progress</option>
                                        <option value="completed">Completed</option>
                                      </select>
                                    </div>
                                  </div>
                                </div>
                                <div className="edit-form-actions">
                                  <button className="btn btn-secondary" onClick={handleCancelEdit}>
                                    Cancel
                                  </button>
                                  <button className="btn btn-primary" onClick={handleUpdateTask} disabled={loading}>
                                    {loading ? <Loader2 size={16} className="spin" /> : <Save size={16} />}
                                    Save Changes
                                  </button>
                                </div>
                              </div>
                            ) : (
                              // View mode
                              <>
                                <div className="task-status" onClick={() => handleQuickStatusUpdate(task.id, task.status === 'completed' ? 'pending' : 'completed')} title="Click to toggle status">
                                  {getStatusIcon(task.status)}
                                </div>
                                <div className="task-content">
                                  <div className="task-title">{task.title}</div>
                                  {task.description && (
                                    <div className="task-description">{task.description}</div>
                                  )}
                                  <div className="task-meta">
                                    {task.deadline && (
                                      <span className="meta-item">
                                        <Calendar size={14} />
                                        {task.deadline}
                                      </span>
                                    )}
                                    <span className={`priority-badge ${getPriorityClass(task.priority)}`}>
                                      {task.priority?.charAt(0).toUpperCase() + task.priority?.slice(1)}
                                    </span>
                                    <span className={`status-badge ${task.status}`}>
                                      {task.status?.replace('_', ' ')}
                                    </span>
                                  </div>
                                </div>
                                <div className="task-actions">
                                  <button 
                                    className="btn-icon" 
                                    onClick={() => handleEditTask(task)}
                                    title="Edit task"
                                  >
                                    <Edit2 size={16} />
                                  </button>
                                  <button 
                                    className="btn-icon success" 
                                    onClick={() => handleQuickStatusUpdate(task.id, 'completed')}
                                    title="Mark as completed"
                                    disabled={task.status === 'completed'}
                                  >
                                    <CheckCheck size={16} />
                                  </button>
                                  <button 
                                    className="btn-icon danger" 
                                    onClick={() => handleDeleteTask(task.id)}
                                    title="Delete task"
                                  >
                                    <Trash2 size={16} />
                                  </button>
                                </div>
                              </>
                            )}
                          </div>
                        ))}
                      </div>
                    )}

                    {showDeletedTasks && (
                      <div className="deleted-section">
                        <div className="deleted-header">
                          <Trash2 size={16} />
                          <h3>Deleted Tasks</h3>
                          <span className="badge">{deletedTasks.length}</span>
                        </div>
                        {deletedTasks.length === 0 ? (
                          <p className="empty-message">No deleted tasks available for recovery.</p>
                        ) : (
                          <div className="deleted-list">
                            {deletedTasks.map((task) => (
                              <div key={task.id} className="deleted-item">
                                <div className="deleted-content">
                                  <strong>{task.title}</strong>
                                  {task.deadline && <span>Due: {task.deadline}</span>}
                                </div>
                                <button
                                  className="btn btn-secondary"
                                  onClick={() => handleRestoreTask(task.id)}
                                  title="Restore task"
                                >
                                  <Undo2 size={14} />
                                  Restore
                                </button>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === 'reminders' && (
          <div className="tab-content">
            {!isLoggedIn ? (
              <div className="alert-banner">
                <AlertCircle size={20} />
                <span>Please login to send reminders</span>
                <button className="btn btn-small" onClick={() => setActiveTab('account')}>
                  Go to Login
                </button>
              </div>
            ) : (
              <div className="centered-panel">
                <div className="panel reminder-panel">
                  <div className="panel-header">
                    <Bell size={20} />
                    <h2>Send Task Reminder</h2>
                  </div>
                  <div className="panel-body">
                    <div className="reminder-info">
                      <Icon icon="mdi:email-fast-outline" className="reminder-icon" />
                      <div>
                        <h3>Email Reminder for {selectedUserData?.name}</h3>
                        <p>Send an email notification about upcoming task deadlines</p>
                      </div>
                    </div>

                    <div className="form-group">
                      <label>
                        <Calendar size={16} />
                        Reminder Period
                      </label>
                      <select 
                        value={reminderDays} 
                        onChange={(e) => setReminderDays(parseInt(e.target.value))}
                      >
                        <option value={1}>Tasks due in 1 day</option>
                        <option value={3}>Tasks due in 3 days</option>
                        <option value={5}>Tasks due in 5 days</option>
                        <option value={7}>Tasks due in 7 days</option>
                        <option value={14}>Tasks due in 14 days</option>
                        <option value={30}>Tasks due in 30 days</option>
                      </select>
                    </div>

                    <div className="recipient-info">
                      <Mail size={16} />
                      <span>Sending to: <strong>{selectedUserData?.email}</strong></span>
                    </div>

                    <button 
                      className="btn btn-warning btn-full" 
                      onClick={handleSendReminder} 
                      disabled={loading}
                    >
                      {loading ? <Loader2 className="spin" size={18} /> : <Send size={18} />}
                      Send Reminder Email
                    </button>

                    {reminderMsg && (
                      <div className={`message ${reminderMsg.includes('Error') ? 'error' : 'success'}`}>
                        {reminderMsg.includes('Error') ? <AlertTriangle size={16} /> : <CheckCheck size={16} />}
                        {reminderMsg}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === 'schedule' && (
          <div className="tab-content">
            {!isLoggedIn ? (
              <div className="alert-banner">
                <AlertCircle size={20} />
                <span>Please login to use AI Schedule</span>
                <button className="btn btn-small" onClick={() => setActiveTab('account')}>
                  Go to Login
                </button>
              </div>
            ) : (
              <div className="schedule-layout">
                {/* Availability Section */}
                <div className="section-card availability-section">
                  <div className="section-header">
                    <Clock size={24} />
                    <div>
                      <h2>Your Availability</h2>
                      <p>Set when you can study each week</p>
                    </div>
                  </div>
                  
                  <div className="section-body">
                    {/* Add availability form */}
                    <div className="availability-form">
                      <div className="form-row">
                        <div className="form-group">
                          <label>Day</label>
                          <select 
                            value={newAvailability.day_of_week}
                            onChange={(e) => setNewAvailability({...newAvailability, day_of_week: parseInt(e.target.value)})}
                          >
                            <option value={0}>Monday</option>
                            <option value={1}>Tuesday</option>
                            <option value={2}>Wednesday</option>
                            <option value={3}>Thursday</option>
                            <option value={4}>Friday</option>
                            <option value={5}>Saturday</option>
                            <option value={6}>Sunday</option>
                          </select>
                        </div>
                        <div className="form-group">
                          <label>From</label>
                          <input 
                            type="time" 
                            value={newAvailability.start_time}
                            onChange={(e) => setNewAvailability({...newAvailability, start_time: e.target.value})}
                          />
                        </div>
                        <div className="form-group">
                          <label>To</label>
                          <input 
                            type="time" 
                            value={newAvailability.end_time}
                            onChange={(e) => setNewAvailability({...newAvailability, end_time: e.target.value})}
                          />
                        </div>
                        <div className="form-group">
                          <label>Location</label>
                          <input 
                            type="text" 
                            placeholder="e.g., Library"
                            value={newAvailability.location}
                            onChange={(e) => setNewAvailability({...newAvailability, location: e.target.value})}
                          />
                        </div>
                        <button className="btn btn-primary" onClick={handleAddAvailability}>
                          <Plus size={16} /> Add
                        </button>
                      </div>
                    </div>
                    
                    {/* Current availability slots */}
                    <div className="availability-list">
                      {availability.length === 0 ? (
                        <p className="empty-message">No availability set yet. Add your study times above.</p>
                      ) : (
                        availability.map((slot) => (
                          <div key={slot.id} className="availability-slot">
                            <span className="day">{slot.day_name}</span>
                            <span className="time">{slot.start_time} - {slot.end_time}</span>
                            <span className="location">{slot.location || 'No location'}</span>
                            <button 
                              className="btn btn-icon btn-danger-subtle"
                              onClick={() => handleDeleteAvailability(slot.id)}
                            >
                              <Trash2 size={14} />
                            </button>
                          </div>
                        ))
                      )}
                    </div>
                  </div>
                </div>

                {/* Generated Schedule Section */}
                <div className="section-card schedule-section">
                  <div className="section-header">
                    <Bot size={24} />
                    <div>
                      <h2>AI-Generated Schedule</h2>
                      <p>Your tasks optimally placed in your available time</p>
                    </div>
                    <button 
                      className="btn btn-primary btn-generate"
                      onClick={handleGenerateSchedule}
                      disabled={scheduleLoading}
                    >
                      {scheduleLoading ? (
                        <><Loader2 className="spin" size={16} /> Generating...</>
                      ) : (
                        <><Play size={16} /> Generate Schedule</>
                      )}
                    </button>
                  </div>

                  {scheduleMsg && (
                    <div className={`message ${scheduleMsg.includes('Error') || scheduleMsg.includes('issue') ? 'warning' : 'success'}`}>
                      {scheduleMsg.includes('Error') ? <AlertTriangle size={16} /> : <CheckCheck size={16} />}
                      {scheduleMsg}
                    </div>
                  )}

                  {scheduleReasoning && (
                    <div className="ai-reasoning">
                      <Bot size={16} />
                      <p><strong>AI Reasoning:</strong> {scheduleReasoning}</p>
                    </div>
                  )}

                  <div className="section-body">
                    {schedule.length === 0 ? (
                      <div className="empty-schedule">
                        <CalendarDays size={48} />
                        <p>No schedule generated yet.</p>
                        <p className="hint">Add your availability above, then click "Generate Schedule" to let the AI create an optimal study plan.</p>
                      </div>
                    ) : (
                      <div className="schedule-grid">
                        {/* Group schedule by date */}
                        {Object.entries(
                          schedule.reduce((acc, slot) => {
                            const date = slot.date;
                            if (!acc[date]) acc[date] = [];
                            acc[date].push(slot);
                            return acc;
                          }, {})
                        ).map(([date, slots]) => (
                          <div key={date} className="schedule-day">
                            <div className="day-header">
                              <Calendar size={16} />
                              <span>{new Date(date + 'T00:00:00').toLocaleDateString('en-US', { weekday: 'long', month: 'short', day: 'numeric' })}</span>
                            </div>
                            <div className="day-slots">
                              {slots.map((slot) => (
                                <div key={slot.id} className="schedule-slot">
                                  <div className="slot-time">
                                    <Clock size={14} />
                                    {slot.start_time} - {slot.end_time}
                                  </div>
                                  <div className="slot-task">
                                    <ListTodo size={14} />
                                    {slot.task_title}
                                  </div>
                                  {slot.reasoning && (
                                    <div className="slot-reasoning">
                                      <Bot size={12} />
                                      <span>{slot.reasoning}</span>
                                    </div>
                                  )}
                                </div>
                              ))}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === 'chat' && (
          <div className="tab-content">
            {!isLoggedIn ? (
              <div className="alert-banner">
                <AlertCircle size={20} />
                <span>Please login to use AI Chat</span>
                <button className="btn btn-small" onClick={() => setActiveTab('account')}>
                  Go to Login
                </button>
              </div>
            ) : (
              <div className="chat-layout">
                <div className="chat-container">
                  <div className="chat-header">
                    <Bot size={24} />
                    <div>
                      <h2>AI Task Assistant</h2>
                      <p>Ask me anything about your tasks using natural language</p>
                    </div>
                  </div>
                  
                  <div className="chat-messages">
                    {chatMessages.length === 0 && (
                      <div className="chat-welcome">
                        <Bot size={48} className="welcome-icon" />
                        <h3>Welcome to AI Chat!</h3>
                        <p>You can ask me to:</p>
                        <ul>
                          <li><Zap size={14} /> "Show all my tasks"</li>
                          <li><Zap size={14} /> "Add a task to finish dissertation by next week"</li>
                          <li><Zap size={14} /> "What tasks are due soon?"</li>
                          <li><Zap size={14} /> "List high priority tasks"</li>
                          <li><Zap size={14} /> "help" - Show all available commands</li>
                        </ul>
                      </div>
                    )}
                    
                    {chatMessages.map((msg, idx) => (
                      <div key={idx} className={`chat-message ${msg.role}`}>
                        <div className="message-avatar">
                          {msg.role === 'user' ? <User size={20} /> : <Bot size={20} />}
                        </div>
                        <div className="message-content">
                          <pre>{msg.content}</pre>
                        </div>
                      </div>
                    ))}
                    
                    {chatLoading && (
                      <div className="chat-message assistant">
                        <div className="message-avatar">
                          <Bot size={20} />
                        </div>
                        <div className="message-content">
                          <Loader2 className="spin" size={20} />
                        </div>
                      </div>
                    )}
                  </div>
                  
                  <div className="chat-input-area">
                    <input
                      type="text"
                      placeholder="Type your message... (e.g., 'show my tasks', 'add task...')"
                      value={chatInput}
                      onChange={(e) => setChatInput(e.target.value)}
                      onKeyPress={(e) => e.key === 'Enter' && handleChat()}
                      disabled={chatLoading}
                    />
                    <button 
                      className="btn btn-primary" 
                      onClick={handleChat}
                      disabled={chatLoading || !chatInput.trim()}
                    >
                      {chatLoading ? <Loader2 className="spin" size={18} /> : <Send size={18} />}
                    </button>
                  </div>
                </div>
                
                {conflicts.length > 0 && (
                  <div className="conflicts-panel">
                    <div className="panel-header">
                      <AlertTriangle size={20} />
                      <h2>Schedule Conflicts</h2>
                      <span className="badge">{conflicts.length}</span>
                    </div>
                    <div className="panel-body">
                      {conflicts.map((conflict, idx) => (
                        <div key={idx} className={`conflict-item ${conflict.type}`}>
                          <div className="conflict-icon">
                            {conflict.type === 'urgent' ? <Clock size={18} /> : 
                             conflict.type === 'overload' ? <AlertCircle size={18} /> :
                             <AlertTriangle size={18} />}
                          </div>
                          <div className="conflict-info">
                            <div className="conflict-message">{conflict.message}</div>
                            <div className="conflict-date">{conflict.date}</div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </main>

      <footer className="app-footer">
        <p>
          <Icon icon="mdi:robot-outline" style={{ verticalAlign: 'middle', marginRight: '8px' }} />
          Powered by LangGraph Agentic AI | Academic Task Manager v1.0
        </p>
      </footer>
    </div>
  );
}

export default App;


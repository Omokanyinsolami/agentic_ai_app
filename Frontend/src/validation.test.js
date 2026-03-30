import {
  userSchema,
  taskSchema,
  reminderSchema,
  validateForm,
  formatName,
} from './validation';

describe('validation helpers', () => {
  test('accepts a valid user payload', () => {
    const payload = {
      name: 'John Smith',
      email: 'john.smith@gmail.com',
      program: 'MSc Computer Science',
    };
    const result = validateForm(userSchema, payload);
    expect(result.success).toBe(true);
    expect(result.errors).toEqual({});
  });

  test('rejects invalid name format', () => {
    const payload = {
      name: 'john smith',
      email: 'john.smith@gmail.com',
      program: 'MSc Computer Science',
    };
    const result = validateForm(userSchema, payload);
    expect(result.success).toBe(false);
    expect(result.errors.name).toMatch(/full name/i);
  });

  test('rejects unsupported email domains', () => {
    const payload = {
      name: 'John Smith',
      email: 'john@unknown-domain.dev',
      program: 'MSc Computer Science',
    };
    const result = validateForm(userSchema, payload);
    expect(result.success).toBe(false);
    expect(result.errors.email).toMatch(/valid email provider/i);
  });

  test('formats mixed-case names consistently', () => {
    expect(formatName('   jOhN   sMiTh  ')).toBe('John Smith');
  });
});

describe('task schema edge cases', () => {
  test('accepts a minimal valid task', () => {
    const payload = {
      title: 'Write dissertation chapter',
      description: '',
      deadline: '',
      priority: 'medium',
      status: 'pending',
    };
    const result = validateForm(taskSchema, payload);
    expect(result.success).toBe(true);
  });

  test('rejects past deadlines', () => {
    const payload = {
      title: 'Write dissertation chapter',
      description: '',
      deadline: '2000-01-01',
      priority: 'medium',
      status: 'pending',
    };
    const result = validateForm(taskSchema, payload);
    expect(result.success).toBe(false);
    expect(result.errors.deadline).toMatch(/future date/i);
  });

  test('rejects invalid priority enums', () => {
    const payload = {
      title: 'Write dissertation chapter',
      description: '',
      deadline: '',
      priority: 'urgent',
      status: 'pending',
    };
    const result = validateForm(taskSchema, payload);
    expect(result.success).toBe(false);
    expect(result.errors.priority).toMatch(/expected one of|priority/i);
  });
});

describe('reminder schema edge cases', () => {
  test('accepts valid reminder input', () => {
    const parsed = reminderSchema.safeParse({ userId: 1, days: 7 });
    expect(parsed.success).toBe(true);
  });

  test('rejects invalid reminder day ranges', () => {
    const parsed = reminderSchema.safeParse({ userId: 1, days: 400 });
    expect(parsed.success).toBe(false);
  });
});

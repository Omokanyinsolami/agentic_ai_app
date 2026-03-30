import { z } from 'zod';

// Email validation - supports common email providers
const emailProviders = [
  'gmail.com',
  'yahoo.com',
  'outlook.com',
  'hotmail.com',
  'icloud.com',
  'mail.com',
  'protonmail.com',
  'aol.com',
  'zoho.com',
  'yandex.com',
  'gmx.com',
  'live.com',
  'msn.com',
  'edu', // Educational domains
  'ac.uk', // UK academic
  'edu.ng', // Nigerian educational
];

const isValidEmailDomain = (email) => {
  const domain = email.split('@')[1]?.toLowerCase();
  if (!domain) return false;
  
  // Check exact match or if ends with educational domains
  return emailProviders.some(provider => 
    domain === provider || 
    domain.endsWith(`.${provider}`) ||
    domain.endsWith('.edu') ||
    domain.endsWith('.ac.uk')
  );
};

// Name validation - must be "FirstName LastName" format
const isValidFullName = (name) => {
  const trimmed = name.trim();
  const parts = trimmed.split(/\s+/);
  
  // Must have at least first and last name
  if (parts.length < 2) return false;
  
  // Each part must start with uppercase and be at least 2 characters
  return parts.every(part => 
    part.length >= 2 && 
    /^[A-Z][a-z]+$/.test(part)
  );
};

// User Schema
export const userSchema = z.object({
  name: z
    .string()
    .min(5, 'Full name must be at least 5 characters')
    .max(100, 'Full name must be less than 100 characters')
    .refine(isValidFullName, {
      message: 'Enter full name as "FirstName LastName" (e.g., John Smith). Each name must start with uppercase.',
    }),
  email: z
    .string()
    .email('Invalid email format')
    .refine(isValidEmailDomain, {
      message: 'Please use a valid email provider (gmail.com, yahoo.com, outlook.com, educational domains, etc.)',
    }),
  program: z
    .string()
    .min(2, 'Academic program must be at least 2 characters')
    .max(200, 'Academic program must be less than 200 characters')
    .optional()
    .or(z.literal('')),
});

// Task Schema
export const taskSchema = z.object({
  title: z
    .string()
    .min(3, 'Task title must be at least 3 characters')
    .max(200, 'Task title must be less than 200 characters'),
  description: z
    .string()
    .max(1000, 'Description must be less than 1000 characters')
    .optional()
    .or(z.literal('')),
  deadline: z
    .string()
    .refine((val) => {
      if (!val) return true; // Optional
      const date = new Date(val);
      const today = new Date();
      today.setHours(0, 0, 0, 0);
      return date >= today;
    }, {
      message: 'Deadline must be today or a future date',
    })
    .optional()
    .or(z.literal('')),
  priority: z
    .enum(['low', 'medium', 'high'], {
      errorMap: () => ({ message: 'Priority must be low, medium, or high' }),
    })
    .optional()
    .default('medium'),
  status: z
    .enum(['pending', 'in_progress', 'completed'], {
      errorMap: () => ({ message: 'Status must be pending, in_progress, or completed' }),
    })
    .optional()
    .default('pending'),
});

// Reminder Schema
export const reminderSchema = z.object({
  userId: z
    .number()
    .positive('Please select a valid user')
    .or(z.string().min(1, 'Please select a user')),
  days: z
    .number()
    .min(1, 'Days must be at least 1')
    .max(365, 'Days must be less than 365')
    .optional()
    .default(7),
});

// Helper function to validate and get errors
export const validateForm = (schema, data) => {
  try {
    schema.parse(data);
    return { success: true, errors: {} };
  } catch (error) {
    if (error instanceof z.ZodError) {
      const errors = {};
      const issues = error.issues || error.errors || [];
      issues.forEach((err) => {
        const path = err.path.join('.');
        errors[path] = err.message;
      });
      return { success: false, errors };
    }
    return { success: false, errors: { _form: 'Validation failed' } };
  }
};

// Helper to format name properly
export const formatName = (name) => {
  return name
    .trim()
    .split(/\s+/)
    .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(' ');
};

# Users App

This Django app manages users and AI code generation in the Purplex platform.

## Models
- `UserProfile`: Extends the Django User model with additional fields

## Features
- Authentication integration with Firebase
- AI-powered code generation using OpenAI
- User profile management

## API Endpoints
- `/api/generate/`: Generate multiple code implementations from a prompt

## Configuration
The OpenAI API key should be set as an environment variable:
```
export OPENAI_API_KEY=your_api_key_here
```
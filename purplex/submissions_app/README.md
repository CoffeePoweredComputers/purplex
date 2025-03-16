# Submissions App

This Django app handles code submissions and testing functionality in the Purplex platform.

## Models
- `PromptSubmission`: Records user submissions with scores and timestamps

## Features
- Test code submissions against problem test cases
- Record and track user submissions
- Provide feedback on code correctness

## API Endpoints
- `/api/test/`: Test code against problem test cases
- `/api/submit_code/`: Submit code solutions for problems
# Problems App

This Django app manages coding problems and problem sets in the Purplex platform.

## Models
- `Problem`: Represents coding problems with title, description, solution, and test cases
- `ProblemSet`: Collections of related problems grouped together

## Features
- List and retrieve problems and problem sets
- Load problems and problem sets from file system
- Display problem details to students

## Management Commands
- `load_problems`: Loads problems from the file system into the database
- `load_problemsets`: Loads problem sets from the file system into the database
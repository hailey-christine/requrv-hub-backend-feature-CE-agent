# ReQurv AI FastAPI Repository

## Overview
This repository contains the source code for the ReQurv AI application, built using FastAPI and managed with the UV package manager.

## Prerequisites
- Python 3.9 or higher
- UV package manager

## Installation

### Step 1: Install UV Package Manager
If you haven't installed the UV package manager yet, you can do so by following the instructions on the [official UV website](https://uvpm.dev/docs/installation).

### Step 2: Install Dependencies
Navigate to the root directory of the repository and run the following command to install the required dependencies:
```bash
uv sync
```

## Running the Application

### Step 1: Run the Application
Use the UV package manager to run the application:
```bash
uv run fastapi dev main.py
```

#### For production
Use the UV package manager to run the application:
```bash
uv run fastapi run main.py
```

The application will be accessible at `http://127.0.0.1:8000`.

## PRISMA
Prisma is used as the ORM for this project.
To run the migrations, use the following command:
```bash
make migrate-dev
```
to open the studio to test the database:
```bash
make studio
```


## Additional Resources
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [UV Package Manager Documentation](https://uvpm.dev/docs/)

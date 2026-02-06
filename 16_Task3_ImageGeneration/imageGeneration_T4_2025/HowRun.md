# How to Run the Project

## 1. Create and Activate Virtual Environment

### Windows
```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
.venv\Scripts\activate
```

### Linux/MacOS
```bash
# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate
```

## 2. Install Required Packages

```bash
# Install required packages
pip install python-dotenv openai
```

## 3. Set Up Environment Variables

1. Make sure you have a `.env` file in the project directory
2. The `.env` file should contain your OpenAI API key:
```
OPENAI_API_KEY=your_api_key_here
```

## 4. Run the Script

```bash
# Run the main script
python openAI.py
```

## 5. Deactivate Virtual Environment (When Done)

```bash
deactivate
```

## Notes
- Make sure you have Python 3.7 or higher installed
- Keep your `.env` file secure and never commit it to version control
- The virtual environment should be activated every time you work on the project


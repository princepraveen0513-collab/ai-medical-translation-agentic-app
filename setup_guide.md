# 🩺 AI Multilingual Medical Interpreter — Setup Guide

Welcome!  
This guide will help you install and run the **AI Multilingual Medical Interpreter**, an agentic RAG-based system that translates medical conversations between Hindi and English with cultural and clinical awareness.

This setup guide is written for **external users** who want to run the project locally.

---

## ✅ 1. Prerequisites

Before you begin, ensure you have:

- **Python 3.10 or higher**
- **pip** (Python package manager)
- **Git**
- An **OpenAI API Key**
- A **Pinecone API Key** (for vector search)

Optional (but recommended):

- A virtual environment tool (`venv` or `conda`)

---

## 📥 2. Clone the Repository

Use Git to download the project:

```bash
git clone https://github.com/<your-username>/ai-medical-translation-agentic-app.git
cd ai-medical-translation-agentic-app

```

## 📦 3. Set Up a Virtual Environment (Recommended)

Creating an isolated environment prevents dependency conflicts.

**Create:**

```bash
python -m venv .venv
```

**Activate:**

**Windows (PowerShell):**

```bash
.venv\Scripts\Activate.ps1
```

**macOS/Linux:**

```bash
source .venv/bin/activate
```

## 📚 4. Install Dependencies

Install all required Python libraries:

```bash
pip install -r requirements.txt
```

## 🔐 5. Configure Environment Variables

The project uses environment variables for API keys.

Copy the example file:

```bash
cp .env.example .env
```

Open `.env` and fill in your own keys:

```ini
OPENAI_API_KEY=your_openai_api_key
PINECONE_API_KEY=your_pinecone_api_key
PINECONE_ENVIRONMENT=gcp-starter   # or the environment provided in your Pinecone dashboard
PINECONE_INDEX_NAME=medical_cultural_rag
```

**🔎 Why is this needed?**
The system relies on OpenAI for translation + reasoning, and Pinecone for semantic retrieval.

## 🧠 6. (Optional) Initialize the Vector Database

If you want full RAG functionality, run the database setup script:

```bash
python setup_db.py
```

This will:

- Preprocess medical + cultural text data
- Generate embeddings
- Upload them to your Pinecone index

If you skip this step, translations will still work, but without the enhanced medical/cultural context.

## ▶️ 7. Run the Application

Start the Streamlit web interface:

```bash
streamlit run app/ui_app.py
```

Streamlit will open a browser window automatically.
If not, visit:

```arduino
http://localhost:8501
```

## 🖥️ 8. Using the Application

1. **Register or Login** through the authentication screen.
2. Select your role:
   - **Doctor (English)**
   - **Patient (Hindi)**
3. Type a message in your panel and click **Send**.
4. The system will automatically:
   - Check for unsafe content
   - Mask PII
   - Retrieve relevant medical/cultural context
   - Produce a natural, clinically meaningful translation
5. Click **Generate Summary** to create a structured clinical note.

---

## 🛠️ 9. Troubleshooting

### ❗ “ModuleNotFoundError”

Make sure your virtual environment is activated.

### ❗ “Streamlit not found”

Install manually:

```bash
pip install streamlit
```

### ❗ Pinecone Authentication Errors

Verify:

- Your API key is correct
- Your environment matches Pinecone’s dashboard
- The index name matches `.env`

### ❗ OpenAI key invalid

Check your usage limits or regenerate your key from the OpenAI dashboard.

## 🤝 Support

If you're an external user running into issues, please open an Issue on the GitHub repository.

Thanks for exploring the AI Multilingual Medical Interpreter!
Your feedback helps us improve accessibility, safety, and medical accuracy.

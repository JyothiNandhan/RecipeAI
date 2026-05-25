# RecipeAI (RAG Recipe App)

RecipeAI is a full-stack Retrieval-Augmented Generation (RAG) application that provides personalized recipe recommendations based on the ingredients you have on hand, your dietary preferences, the current time of day, and your local weather.

It uses a local vector database to retrieve semantically matching recipes from a curated dataset, and then uses a Large Language Model (Llama 3.1 70B via the UF NaviGator API) to synthesize the context and generate a final recommendation with an explanation of why it fits.

## Architecture

The project consists of two main parts:
1. **Backend**: FastAPI, ChromaDB, SentenceTransformers (PyTorch), and Llama 3.1 70B.
2. **Frontend**: Angular 17.

### Flow of Data
1. User enters ingredients, location, and other preferences in the UI.
2. The Angular frontend sends an HTTP POST request to the `/recommend` FastAPI endpoint.
3. The backend fetches the local weather for the given location and determines the time of day to establish the "context".
4. The backend constructs a natural language query based on the user's input.
5. The query is converted into a vector embedding using `SentenceTransformer` (`all-MiniLM-L6-v2`).
6. The vector is used to query the local `ChromaDB` instance, retrieving the most semantically similar recipes.
7. A strict filtering logic is applied:
   - Recipes without any overlapping ingredients are discarded.
   - Recipes that require main proteins not selected by the user are discarded, *unless* a base staple (like bread or pasta) was selected.
   - Surviving candidates are re-ranked based on ingredient overlap count.
8. The top results, along with the weather/time context, are bundled into a prompt.
9. The prompt is sent to **Llama 3.1 70B** to select the absolute best matches and generate reasoning for each choice in a structured JSON format.
10. The results are parsed, validated, and returned to the Angular frontend for display.

## Project Structure

```
RAG_RECIPE/
├── backend/                  ← Python backend
│   ├── chroma_db/            ← Local ChromaDB vector database
│   ├── logs/traces/          ← Saved request traces for observability
│   ├── venv/                 ← Python virtual environment
│   ├── ingest.py             ← Script to embed and load recipes into ChromaDB
│   ├── llm.py                ← LLM integration (OpenAI client to NaviGator)
│   ├── main.py               ← FastAPI application entry point
│   ├── models.py             ← Pydantic models for API request/response
│   ├── observability.py      ← Trace generation and Admin Dashboard HTML
│   ├── prompt_builder.py     ← Logic to assemble the prompt for Llama
│   ├── rag.py                ← Vector retrieval, embedding, and filtering logic
│   ├── recipes.json          ← The source dataset of recipes
│   ├── request_context.py    ← Logic for fetching time and weather (Open-Meteo)
│   └── requirements.txt      ← Python dependencies
├── frontend/                 ← Angular 17 frontend
│   ├── src/                  ← Angular source code
│   └── package.json          ← Node dependencies
├── start_backend.sh          ← Convenience script to start the backend
└── start_frontend.sh         ← Convenience script to start the frontend
```

## Setup and Running

### First Time Setup
The application requires Python 3.12+ and Node.js 18+.

1. **Backend Setup**
   ```bash
   cd backend
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   
   # Load the recipe dataset into ChromaDB
   python ingest.py
   ```

2. **Frontend Setup**
   ```bash
   cd frontend
   npm install
   ```

### Running the Application
We have provided two shell scripts to easily start the services.

**Terminal 1:**
```bash
./start_backend.sh
```

**Terminal 2:**
```bash
./start_frontend.sh
```

### URLs
- **Web App**: http://localhost:4200
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Admin Observability Dashboard**: http://localhost:8000/admin/observability

*Default credentials for the frontend UI: Email `admin@example.com`, Password `admin12345`.*

## Observability Dashboard

A powerful feature of this project is the built-in observability dashboard. You can access it at `http://localhost:8000/admin/observability`.

Every request to the `/recommend` endpoint generates a "Trace". A trace logs the exact state of the system at each step of the pipeline:
- **Input**: What the user requested.
- **Context**: The time of day and the fetched weather data.
- **Vector DB**: The exact query text generated, the candidates returned by ChromaDB, their distance scores, and which ones were kept or filtered (with reasons).
- **LLM**: The full prompt sent to Llama 3.1, the raw text returned by the model, and the parsed JSON.
- **Final Output**: The final response sent to the user.

This dashboard is invaluable for debugging why a certain recipe was or wasn't recommended!

## Configuration

To get real recommendations, you must provide a valid **UF NaviGator API token**. You can input this directly in the frontend UI when making a request. The application passes it securely to the backend for the LLM call.

## Deployment (Vercel + Ngrok)

Because the vector database and ML models require significant disk space and memory, the most cost-effective deployment strategy is to host the lightweight Angular frontend on Vercel while keeping the Python backend running locally on your machine.

To connect the public Vercel frontend to your local backend securely, use **Ngrok**:

1. Install [Ngrok](https://ngrok.com/) and authenticate it with your token.
2. Start the FastAPI backend locally on port 8000.
3. In a separate terminal, start the Ngrok tunnel: `ngrok http 8000`
4. Copy the secure `https://...ngrok-free.app` URL provided by Ngrok.
5. In the frontend codebase, open `src/environments/environment.prod.ts` and set the `apiUrl` to your Ngrok URL.
6. Commit your changes and push to GitHub.
7. Import your repository into Vercel and deploy. Vercel will automatically build the Angular application and route all API calls securely to your local laptop!

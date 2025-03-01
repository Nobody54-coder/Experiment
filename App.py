from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
import openai
import uvicorn
import os
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter
from slowapi.util import get_remote_address

# Load OpenAI API key
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# FastAPI app
app = FastAPI()

# Enable CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replace with frontend URL for security
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate Limiting (Prevent abuse)
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

# HTML Frontend
HTML_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI App Generator</title>
</head>
<body>
    <h1>AI App Generator</h1>
    <textarea id="prompt" placeholder="Describe your app..."></textarea><br>
    <button onclick="generateApp()">Generate App</button>
    <pre id="output"></pre>

    <script>
        async function generateApp() {
            let prompt = document.getElementById("prompt").value;
            let response = await fetch("/generate-app/", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ prompt: prompt })
            });
            let data = await response.json();
            document.getElementById("output").innerText = data.code || "Error generating app.";
        }
    </script>
</body>
</html>
"""

# Request model
class PromptInput(BaseModel):
    prompt: str

# Serve frontend
@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    return HTML_PAGE

# Generate AI-powered app code
@app.post("/generate-app/")
@limiter.limit("5/minute")  # Max 5 requests per minute
async def generate_code(request: PromptInput):
    try:
        openai.api_key = OPENAI_API_KEY
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": request.prompt}]
        )
        return {"code": response["choices"][0]["message"]["content"]}
    except openai.error.AuthenticationError:
        return JSONResponse(content={"error": "Invalid OpenAI API key."}, status_code=401)
    except openai.error.RateLimitError:
        return JSONResponse(content={"error": "Rate limit exceeded. Try again later."}, status_code=429)
    except Exception as e:
        return JSONResponse(content={"error": f"Something went wrong: {str(e)}"}, status_code=500)

# Run the app
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))

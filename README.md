# AI_CallCenter

# 📞 Multilingual AI Call Center

An intelligent, production-ready AI-powered call center built with Flask, Twilio, and Groq (Llama 3.3 70B). Handles inbound phone calls in 6 languages with real-time language detection, streaming AI responses, and Voice Activity Detection.

---

## 🌍 Supported Languages

| Language | Code | Voice |
|----------|------|-------|
| English | `en` | Polly.Joanna |
| Hindi | `hi` | Polly.Aditi |
| Spanish | `es` | Polly.Lucia |
| French | `fr` | Polly.Celine |
| German | `de` | Polly.Marlene |
| Portuguese | `pt` | Polly.Vitoria |

---

## ⚡ Features

- **Automatic Language Detection** — detects caller's language from their first message and switches the entire conversation accordingly
- **Streaming AI Responses** — Groq streams tokens in real-time; first sentence delivered to caller ~60% faster than standard calls
- **Voice Activity Detection (VAD)** — WebRTC VAD filters out silence and background noise before sending audio to speech recognition, saving latency and cost
- **Multilingual Knowledge Base** — FAQs, products, and order data served in the caller's language with LRU caching for instant repeated lookups
- **Thread-Safe Concurrency** — `ThreadPoolExecutor` with 20 workers handles simultaneous calls without blocking
- **Fire-and-Forget Logging** — call transcripts saved to disk in the background without delaying the response
- **Order Lookup** — looks up orders by phone number automatically during the call
- **Hot Reload** — knowledge base can be reloaded without restarting the server

---

## 🏗️ Architecture

```
Incoming Call (Twilio)
        │
        ▼
   /answer route
        │
        ▼
  Language Detection (langdetect)
        │
        ▼
  Voice Activity Detection (WebRTC VAD)
        │
        ▼
  Knowledge Base Search (LRU cached)
        │
        ▼
  Groq LLM — Llama 3.3 70B (stream=True)
        │
        ▼
  First sentence buffered → Twilio <Say>
        │
        ▼
  Call log saved (background thread)
```

---

## 📁 Project Structure

```
├── app.py                      # Main Flask app, routes, streaming LLM, VAD
├── knowledge_base.py           # Thread-safe multilingual KB with LRU cache
├── faqs_multilingual.json      # FAQ data in all 6 languages
├── products_multilingual.json  # Product/plan data in all 6 languages
├── orders.json                 # Order records (phone → order lookup)
├── call_logs/                  # Auto-created, stores call transcripts as JSON
├── requirements.txt
└── .env                        # API keys (never commit this)
```

---

## 🚀 Setup & Installation

### 1. Clone the repository
```bash
git clone https://github.com/your-username/your-repo-name.git
cd your-repo-name
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Set up environment variables

Create a `.env` file in the root directory:
```env
GROQ_API_KEY=your_groq_api_key_here
```

### 4. Add your knowledge base files

Make sure these JSON files exist in the root directory:
- `faqs_multilingual.json`
- `products_multilingual.json`
- `orders.json`

See the [Data Format](#-data-format) section below for structure.

### 5. Run the server
```bash
python app.py
```

Server starts at `http://0.0.0.0:3000`

### 6. Expose to the internet (for Twilio webhooks)
```bash
ngrok http 3000
```

Copy the `https://` URL ngrok gives you — you'll need it for Twilio.

---

## 📞 Twilio Configuration

1. Go to [Twilio Console](https://console.twilio.com)
2. Select your phone number
3. Under **Voice Configuration**, set:
   - **A call comes in** → Webhook → `https://your-ngrok-url.ngrok.io/answer`
   - **Call Status Changes** → `https://your-ngrok-url.ngrok.io/call-status`
4. Save

---

## 📊 Data Format

### `faqs_multilingual.json`
```json
[
  {
    "en": {
      "question": "What are your business hours?",
      "answer": "We are open Monday to Friday, 9am to 6pm."
    },
    "hi": {
      "question": "आपके व्यावसायिक घंटे क्या हैं?",
      "answer": "हम सोमवार से शुक्रवार, सुबह 9 बजे से शाम 6 बजे तक खुले हैं।"
    }
  }
]
```

### `products_multilingual.json`
```json
[
  {
    "en": {
      "name": "Basic Plan",
      "price": "$9.99/month",
      "features": "10GB storage, email support",
      "description": "Perfect for individuals"
    },
    "hi": {
      "name": "बेसिक प्लान",
      "price": "₹799/माह",
      "features": "10GB स्टोरेज, ईमेल सपोर्ट",
      "description": "व्यक्तिगत उपयोग के लिए"
    }
  }
]
```

### `orders.json`
```json
[
  {
    "order_id": "ORD-12345",
    "customer_phone": "+1234567890",
    "status": "Shipped",
    "tracking": "TRK-98765",
    "estimated_delivery": "2025-03-15"
  }
]
```

---

## 🔌 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/answer` | GET, POST | Entry point for incoming Twilio calls |
| `/process-speech` | POST | Handles speech recognition results |
| `/process-speech-timeout` | GET, POST | Handles caller silence/timeout |
| `/call-status` | GET, POST | Receives Twilio call status webhooks |
| `/vad-check` | POST | Voice Activity Detection check on raw audio |
| `/test` | GET | Health check — confirms all systems running |

### Health Check Response
```bash
curl http://localhost:3000/test
```
```json
{
  "status": "Server is running!",
  "async_mode": "ThreadPoolExecutor (max_workers=20)",
  "llm_client": "httpx + stream=True",
  "temperature": 0.4,
  "vad": "WebRTC VAD (mode=2, min_speech=100ms)",
  "knowledge_base": "multilingual",
  "supported_languages": ["en", "hi", "es", "fr", "de", "pt"],
  "active_calls": 0
}
```

---

## 🧠 How Streaming Works

Standard (no streaming):
```
Caller speaks → 1.5s silence → Full AI response plays
```

With `stream=True`:
```
Caller speaks → 0.6s → First sentence plays → rest continues
```

Groq sends tokens one by one. The server buffers them until the first `.`, `?`, or `!` is received, then immediately sends that sentence to Twilio. This cuts perceived response latency by ~60%.

---

## 🎤 How VAD Works

WebRTC VAD (the same engine used in Google Chrome) analyzes incoming audio in 20ms frames. It classifies each frame as speech or non-speech. If less than 20% of frames contain real voice energy, the audio is treated as silence and the LLM call is skipped entirely — saving processing time and API cost.

VAD aggressiveness is set to **mode 2** (scale 0–3):
- Mode 0 — least aggressive, passes most audio through
- Mode 2 — balanced, filters noise but keeps soft voices ✅
- Mode 3 — most aggressive, may cut off quiet speakers

---

## 📦 Requirements

```
flask
flask-cors
twilio
groq
httpx
webrtcvad
langdetect
python-dotenv
```

Install all:
```bash
pip install -r requirements.txt
```

---

## 🔐 Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GROQ_API_KEY` | ✅ Yes | Your Groq API key from [console.groq.com](https://console.groq.com) |

---

## 📝 Call Logs

Every completed call is automatically saved to the `call_logs/` directory as a JSON file:

```
call_logs/
  CA1234567890_20250313_143022.json
```

Each log contains:
- Caller phone number
- Detected language
- Full conversation transcript with timestamps
- Call start and end time

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch — `git checkout -b feature/your-feature`
3. Commit your changes — `git commit -m "feat: your feature description"`
4. Push — `git push origin feature/your-feature`
5. Open a Pull Request

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.
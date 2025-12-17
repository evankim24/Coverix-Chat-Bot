# Coverix Insurance Chatbot

An AI-powered conversational chatbot for insurance onboarding that collects user information through natural conversation.

## Features

- Natural conversational flow powered by OpenAI
- NHTSA API integration for vehicle validation
- Real-time database storage of conversations
- Live chat transcriptions
- Clean, intuitive UI

## Tech Stack

**Backend:**
- FastAPI (Python)
- SQLAlchemy + SQLite
- OpenAI API
- NHTSA Vehicle API

**Frontend:**
- React + Vite
- Axios
- CSS3

## Setup Instructions

### Prerequisites
- Python 3.9+
- Node.js 16+
- npm or yarn

### Backend Setup

1. Navigate to backend folder:
```bash
cd backend
```

2. Create virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create `.env` file with your OpenAI API key:
```
OPENAI_API_KEY=your-key-here
```

5. Start the backend server:
```bash
python3 -m uvicorn main:app --reload
```

Backend will run at `http://localhost:8000`

### Frontend Setup

1. Navigate to frontend folder:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Start the development server:
```bash
npm run dev
```

Frontend will run at `http://localhost:5173`

### Verify Installation

Backend: Visit `http://localhost:8000/docs` - you should see the API documentation
Frontend: Visit `http://localhost:5173` - you should see the chat interface

## Usage

1. Open `http://localhost:5173` in your browser
2. Chat with the bot to provide:
   - ZIP code
   - Full name
   - Email address
   - Vehicle information (VIN or Year/Make/Body Type)
   - Vehicle usage details
   - License information

## API Documentation

Once the backend is running, visit `http://localhost:8000/docs` for interactive API documentation.

### Key Endpoints

- `POST /api/start-conversation` - Start a new chat session
- `POST /api/chat` - Send a message
- `GET /api/conversation/{session_id}` - View full conversation transcript

## Database

The chatbot uses SQLite with three main tables:
- `conversations` - User information and session data
- `vehicles` - Vehicle details (supports multiple per user)
- `messages` - Complete chat transcripts with timestamps

To view the database:
```bash
cd backend
sqlite3 coverix_chatbot.db
SELECT * FROM conversations;
SELECT * FROM vehicles;
SELECT * FROM messages;
.quit
```

## Project Structure
```
coverix-chatbot/
├── backend/
│   ├── main.py           # FastAPI app & routes
│   ├── models.py         # Database models
│   ├── database.py       # Database connection
│   ├── chat_service.py   # OpenAI & API integrations
│   ├── requirements.txt
│   └── .env
├── frontend/
│   ├── src/
│   │   ├── App.jsx       # Main chat component
│   │   ├── App.css       # Styles
│   │   └── main.jsx
│   └── package.json
└── README.md
```

## Features Implementation

✅ **Scalable Data Storage** - Normalized database with relationships  
✅ **Stay On Track** - Step-by-step validation and flow control  
✅ **Live Transcriptions** - Real-time message storage with timestamps  
✅ **Vehicle Validation** - NHTSA API integration  
✅ **Frustration Detection** - Zen quotes API for user support

## Notes

- The OpenAI API key should never be committed to version control
- The database file (`coverix_chatbot.db`) is created automatically on first run
- For production deployment, replace SQLite with PostgreSQL or similar# Coverix-Chat-Bot

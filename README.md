# 🕉️ Vedic Astrology AI & Kundli GMT

An AI-powered Vedic astrology application that generates detailed birth charts (Kundli) and provides astrological insights using Google's Gemini AI.

## Features

- 📊 **Comprehensive Birth Charts**: Generate detailed D1 (Rasi) charts and other divisional charts
- 🎨 **Visual Chart Representation**: South Indian style chart display
- ⏳ **Dasha Timeline**: Interactive Vimshottari Dasha period visualizations
- 💬 **AI Astrologer**: Chat with an AI trained on Vedic astrology principles
- 👤 **User Profiles**: Save and load multiple birth profiles
- 🗂️ **Multi-Session Chat**: Create and manage separate conversation threads
- 💾 **Flexible Database**: SQLite for local development, MongoDB for cloud deployment

## Tech Stack

- **Frontend**: Streamlit
- **AI**: Google Gemini API
- **Astrology Engine**: jyotishyamitra, pyswisseph
- **Database**: SQLite (local) / MongoDB Atlas (cloud)
- **Visualization**: Plotly, custom HTML/CSS charts

## Setup

### Prerequisites

- Python 3.8+
- Google Gemini API Key ([Get it here](https://ai.google.dev/))
- (Optional) MongoDB Atlas account for cloud deployment

### Installation

1. Clone the repository:
```bash
git clone <your-repo-url>
cd Sai
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create `.streamlit/secrets.toml`:
```toml
# Optional: Add your Gemini API Key to avoid entering it each time
GEMINI_API_KEY = "your-api-key-here"

# Optional: For MongoDB (cloud deployment)
# MONGO_URI = "mongodb+srv://user:password@cluster.mongodb.net/..."
```

4. Run the app:
```bash
streamlit run app.py
```

## Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed instructions on deploying to Streamlit Cloud with MongoDB Atlas.

## Usage

1. **Login/Signup**: Create an account or login
2. **Enter Birth Details**: Input name, date, time, and city of birth
3. **Generate Chart**: View comprehensive astrological analysis
4. **Ask Questions**: Chat with the AI astrologer about your chart
5. **Save Profiles**: Store multiple profiles for quick access

## License

This project is for educational and entertainment purposes.

# AutoTube AI 🎬
### Automated AI Video Generation & Direct YouTube Publishing with Web Dashboard

AutoTube AI is an automated video creation and publishing platform powered by **Google GenAI (Veo & Gemini)**, **Neural Text-to-Speech (Edge-TTS)**, **MoviePy Compositor**, and the **YouTube Data API v3**.

---

## 🌟 Key Features

1. **AI Script & Prompt Generation**:
   - High-retention hooks and viral scripts generated with Google Gemini (`gemini-2.5-flash`).
   - Generates scene-by-scene prompts specifically crafted for Google's **Veo** video model.
2. **AI Video Generation**:
   - Direct integration with Google's **Veo** video generation API (`veo-3.1-generate-preview`) via the official `google-genai` SDK.
   - Built-in dynamic procedural fallback so the pipeline can also run locally for previews and dry runs.
3. **Studio-Quality Neural Voiceover**:
   - Zero-cost, high-fidelity neural narration powered by `edge-tts` with multiple male and female voices.
4. **Seamless Video Assembly**:
   - Auto-stitching of scene clips, precise voiceover sync, aspect ratio handling (Shorts 9:16 vs Standard 16:9), and thumbnail generation.
5. **Direct YouTube Uploading**:
   - Automatic or one-click direct upload to your YouTube channel using OAuth 2.0.
   - Sets title, description, tags, category, and privacy (`unlisted`, `private`, or `public`).
6. **Interactive Web Dashboard UI**:
   - **Video Studio**: Create new videos, choose formats and voices, track real-time progress.
   - **Video Library & Tracker**: Embedded in-browser video player, status badges (`Uploaded` / `Draft Ready` / `Failed`), direct YouTube links, and one-click publish button.
   - **Credentials & Status Monitor**: Visual check for API keys and YouTube authorization.

---

## 🚀 Quick Start

### 1. Installation
Ensure Python 3.10+ is installed. Open PowerShell in this directory:
```powershell
pip install -r requirements.txt
```

### 2. Configure Credentials

#### A. Google Gemini / Veo API Key
1. Get a free API Key from [Google AI Studio](https://aistudio.google.com/).
2. Open `.env` and set:
   ```env
   GEMINI_API_KEY=your_actual_api_key_here
   ```

#### B. YouTube Data API v3 (For Direct Uploads)
1. Go to [Google Cloud Console](https://console.cloud.google.com/).
2. Create a project and search for **YouTube Data API v3** -> Click **Enable**.
3. Go to **APIs & Services** -> **OAuth consent screen** -> Choose *External*, enter an app name and your email, and add your Google account as a *Test User*.
4. Go to **Credentials** -> **Create Credentials** -> **OAuth Client ID**.
5. Select Application type: **Desktop App**.
6. Download the generated JSON, rename it to `client_secret.json`, and place it in the project root:
   `C:\Users\abish\.gemini\antigravity\scratch\youtube_video_automation\client_secret.json`

---

## 🖥️ Launching the Web Dashboard UI

Run either of the following commands:
```powershell
python main.py --ui
```
or
```powershell
streamlit run app.py
```
This opens the interactive studio in your browser at `http://localhost:8501`.

---

## ⚡ CLI / Headless Automation

You can also run batch video generation and uploads directly from the command line:

```powershell
# Create a YouTube Short and save as local draft:
python main.py --topic "Top 5 Mind-Blowing Facts About Black Holes" --format shorts

# Create a standard landscape video and upload directly to YouTube as unlisted:
python main.py --topic "The History of Quantum Computing" --format standard --privacy unlisted --auto-upload
```

---

## 📂 Project Structure

```
youtube_video_automation/
├── app.py                      # Streamlit Web Dashboard UI
├── main.py                     # CLI Runner & launcher
├── config.py                   # Configuration and path settings
├── requirements.txt            # Python dependencies
├── .env                        # Environment variables and API keys
├── data/
│   └── video_registry.json     # Metadata database for all generated videos
├── modules/
│   ├── db.py                   # Video tracking and status management
│   ├── script_generator.py     # Gemini script & Veo visual prompts
│   ├── voice_generator.py      # Edge-TTS neural voiceover
│   ├── video_generator.py      # Google Veo & procedural scene rendering
│   ├── compositor.py           # MoviePy video stitching & audio sync
│   ├── youtube_uploader.py     # YouTube Data API v3 OAuth & upload
│   └── pipeline.py             # Unified end-to-end execution pipeline
└── outputs/
    ├── audio/                  # Generated narration MP3 files
    ├── clips/                  # Scene video clips
    └── videos/                 # Rendered final MP4 videos & thumbnails
```

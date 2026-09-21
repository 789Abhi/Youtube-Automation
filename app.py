import streamlit as st
import os
import sys
import tempfile
import uuid
import time
from pathlib import Path
from datetime import datetime

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from modules.db import get_all_videos, get_video, update_video_record, delete_video_record, create_video_record
from modules.pipeline import run_video_pipeline
from modules.voice_generator import AVAILABLE_VOICES
from modules.youtube_uploader import (
    upload_video_to_youtube,
    get_channel_info,
    disconnect_channel,
    start_nonblocking_oauth,
    get_oauth_status
)
from modules.script_generator import generate_video_script
from config import (
    GEMINI_API_KEY,
    YOUTUBE_CLIENT_SECRET_FILE,
    YOUTUBE_TOKEN_FILE,
    DEFAULT_TTS_VOICE,
    DEFAULT_PRIVACY,
    VIDEO_DIR
)

st.set_page_config(
    page_title="AutoTube AI - Studio & YouTube Publisher",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
<style>
    .metric-card {
        background-color: #1E293B;
        border-radius: 10px;
        padding: 16px;
        border: 1px solid #334155;
        text-align: center;
    }
    .badge-uploaded {
        background-color: #065F46;
        color: #34D399;
        padding: 4px 10px;
        border-radius: 12px;
        font-weight: bold;
        font-size: 0.85rem;
    }
    .badge-draft {
        background-color: #78350F;
        color: #FBBF24;
        padding: 4px 10px;
        border-radius: 12px;
        font-weight: bold;
        font-size: 0.85rem;
    }
    .badge-failed {
        background-color: #7F1D1D;
        color: #F87171;
        padding: 4px 10px;
        border-radius: 12px;
        font-weight: bold;
        font-size: 0.85rem;
    }
    .channel-box {
        background: linear-gradient(135deg, #1e1b4b, #1e293b);
        border: 1px solid #4338ca;
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 20px;
    }
    .auth-btn-link {
        display: inline-block;
        width: 100%;
        text-align: center;
        background-color: #4f46e5;
        color: white !important;
        font-weight: bold;
        padding: 12px;
        border-radius: 8px;
        text-decoration: none;
        margin-top: 10px;
        margin-bottom: 10px;
    }
    .auth-btn-link:hover {
        background-color: #4338ca;
    }
</style>
""", unsafe_allow_html=True)

# -------------------------------------------------------------
# SIDEBAR: CHANNEL & ACCOUNT MANAGER
# -------------------------------------------------------------
with st.sidebar:
    st.markdown("### 📺 Connected Channel")
    
    channel_info = get_channel_info()
    if channel_info:
        st.markdown(f"""
        <div class="channel-box">
            <div style="display:flex; align-items:center; gap:12px;">
                <img src="{channel_info.get('thumbnail')}" style="width:48px; height:48px; border-radius:50%; border:2px solid #6366f1;" />
                <div>
                    <h4 style="margin:0; color:#fff; font-size:15px;">{channel_info.get('title')}</h4>
                    <span style="color:#a5b4fc; font-size:12px;">{channel_info.get('custom_url')}</span>
                </div>
            </div>
            <div style="margin-top:12px; font-size:12px; color:#cbd5e1; display:flex; justify-content:space-between;">
                <span>👥 {int(channel_info.get('subscribers', 0)):,} subs</span>
                <span>🎬 {channel_info.get('video_count')} videos</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        col_s1, col_s2 = st.columns(2)
        with col_s1:
            if st.button("🔄 Switch", use_container_width=True, help="Switch YouTube account"):
                disconnect_channel()
                st.session_state["show_auth_panel"] = True
                st.rerun()
        with col_s2:
            if st.button("🚪 Logout", use_container_width=True, help="Disconnect current channel"):
                disconnect_channel()
                st.info("Logged out.")
                st.rerun()
    else:
        st.info("No YouTube channel connected yet.")
        has_secret = Path(YOUTUBE_CLIENT_SECRET_FILE).exists()
        
        if has_secret:
            if st.button("🔑 Connect YouTube Channel", type="primary", use_container_width=True):
                st.session_state["show_auth_panel"] = True
                start_nonblocking_oauth()
                st.rerun()
        else:
            st.warning("`client_secret.json` is missing.")

    st.divider()
    st.caption("AutoTube AI • Google Veo & YouTube API v3")


# -------------------------------------------------------------
# AUTHENTICATION PROMPT PANEL (NON-BLOCKING)
# -------------------------------------------------------------
oauth_status = get_oauth_status()

if st.session_state.get("show_auth_panel") or oauth_status.get("running"):
    if not oauth_status.get("authenticated"):
        res = start_nonblocking_oauth()
        auth_url = res.get("auth_url") or oauth_status.get("auth_url")

        with st.container():
            st.warning("### 🔐 Connect Your YouTube Channel")
            st.markdown("""
            Click the button below to sign in with Google and grant YouTube upload permission:
            """)
            
            if auth_url:
                st.markdown(f'<a href="{auth_url}" target="_blank" class="auth-btn-link">👉 CLICK HERE TO SIGN IN WITH GOOGLE</a>', unsafe_allow_html=True)
            
            st.info("""
            **💡 Having multiple Google accounts?**
            If Google shows *"400. That's an error (malformed request)"*, it's because multiple Google accounts are logged into the same browser.
            **Fix**: Right-click the blue button above ➔ **Copy link address** ➔ Open an **Incognito / Private Window** ➔ Paste & Sign in!
            """)

            st.markdown("""
            **What to do in the Google window:**
            1. Select your Google account that owns the YouTube channel.
            2. If you see *"Google hasn't verified this app"*, click **Advanced** ➔ **Go to YouTube Uploader (unsafe)**.
            3. Click **Continue / Allow**.
            """)

            col_a1, col_a2 = st.columns([1, 1])
            with col_a1:
                if st.button("✅ I have Authorized - Check & Connect", type="primary", use_container_width=True):
                    if Path(YOUTUBE_TOKEN_FILE).exists():
                        st.session_state["show_auth_panel"] = False
                        st.success("Successfully authenticated!")
                        st.rerun()
                    else:
                        st.info("Waiting for authorization... Please make sure you clicked 'Allow' in your browser.")
            with col_a2:
                if st.button("Cancel", use_container_width=True):
                    st.session_state["show_auth_panel"] = False
                    st.rerun()

            st.caption("💡 *Tip: You can also double-click `D:\\youtube_video_automation\\authorize_youtube.bat` on your desktop.*")
            st.divider()


# -------------------------------------------------------------
# MAIN APP HEADER & METRICS
# -------------------------------------------------------------
st.title("🎬 AutoTube AI Video Studio & Publisher")
st.caption("AI Video Generation, Manual Desktop Uploader & YouTube Management Dashboard")

# Summary Metrics
videos = get_all_videos()
total_count = len(videos)
uploaded_count = len([v for v in videos if v.get("status") == "uploaded"])
draft_count = len([v for v in videos if v.get("status") in ["draft_ready", "video_rendered"]])

col_m1, col_m2, col_m3 = st.columns(3)
with col_m1:
    st.metric("Total Videos in Library", total_count)
with col_m2:
    st.metric("Published to YouTube", uploaded_count)
with col_m3:
    st.metric("Drafts Ready to Upload", draft_count)

st.divider()

# Navigation Tabs
tab_create, tab_manual, tab_library, tab_settings = st.tabs([
    "🚀 AI Video Studio",
    "📤 Manual Video Upload",
    "📺 Video Library & Status",
    "⚙️ Credentials & Channels"
])

# -------------------------------------------------------------
# TAB 1: AI VIDEO GENERATOR
# -------------------------------------------------------------
with tab_create:
    st.subheader("Generate a New AI Video")
    
    col_input, col_config = st.columns([3, 2])
    
    with col_input:
        sample_topics = [
            "Kalki Avatar: The Fiery End of Kali Yuga and the Rebirth of the Golden Age",
            "The 4 Yugas Explained: From Divine Gods in Satya Yuga to Chaos in Kali Yuga",
            "The 7 Immortals (Chiranjeevis) Still Secretly Walking Among Us in 2026",
            "Kurukshetra: The Untold Cosmic War Where Celestial Weapons Shook the Earth",
            "Lord Shiva's Tandava: The Cosmic Dance That Destroys and Creates Universes",
            "Ancient Flying Vimanas and Lost High-Tech Metallurgy of the Vedic Era"
        ]
        
        selected_sample = st.selectbox("Quick Topic Inspiration:", ["-- Select or type custom below --"] + sample_topics)
        initial_topic = "" if selected_sample.startswith("--") else selected_sample
        
        topic = st.text_area(
            "Video Topic / Concept",
            value=initial_topic,
            placeholder="e.g., An epic movie trailer about Kalki Avatar descending on a white winged horse with a blazing fiery sword to end the darkness of Kali Yuga...",
            help="Provide any topic, idea, or movie-style prompt you'd like to turn into a video."
        )

    with col_config:
        format_choice = st.radio(
            "Video Format",
            options=["shorts", "standard"],
            format_func=lambda x: "📱 YouTube Shorts (Vertical 9:16)" if x == "shorts" else "🖥️ Standard Video (Horizontal 16:9)",
            index=0
        )
        
        voice_choice = st.selectbox(
            "Voiceover Narrator",
            options=list(AVAILABLE_VOICES.keys()),
            index=0
        )
        selected_voice_id = AVAILABLE_VOICES[voice_choice]
        
        privacy_choice = st.selectbox(
            "YouTube Privacy Status",
            options=["unlisted", "private", "public"],
            index=0
        )

        auto_upload = st.checkbox(
            "Automatically upload to YouTube right after generation",
            value=False
        )

    st.write("")
    generate_btn = st.button("✨ Generate AI Video", type="primary", use_container_width=True)

    if generate_btn:
        if not topic.strip():
            st.error("Please enter a video topic or concept to proceed.")
        else:
            progress_bar = st.progress(0.0)
            status_text = st.empty()

            def update_progress(pct: float, message: str):
                progress_bar.progress(pct)
                status_text.info(f"**Step {int(pct * 100)}%**: {message}")

            try:
                record = run_video_pipeline(
                    topic=topic.strip(),
                    format_type=format_choice,
                    voice=selected_voice_id,
                    privacy_status=privacy_choice,
                    auto_upload=auto_upload,
                    progress_callback=update_progress
                )
                
                status_text.empty()
                progress_bar.empty()
                st.success("🎉 Video generation finished successfully!")
                
                preview_col1, preview_col2 = st.columns([2, 3])
                with preview_col1:
                    video_path = record.get("video_path")
                    if video_path and Path(video_path).exists():
                        st.video(video_path)

                with preview_col2:
                    st.markdown(f"**Title**: {record.get('title')}")
                    st.markdown(f"**Status**: `{record.get('status')}`")
                    if record.get("youtube_url"):
                        st.markdown(f"🔗 **Live YouTube Link**: [{record.get('youtube_url')}]({record.get('youtube_url')})")
                    
                    st.text_area("Description", record.get("description", ""), height=120)
                    st.write(f"**Tags**: `{'`, `'.join(record.get('tags', []))}`")

            except Exception as e:
                st.error(f"Error executing generation pipeline: {e}")

# -------------------------------------------------------------
# TAB 2: MANUAL VIDEO UPLOAD
# -------------------------------------------------------------
with tab_manual:
    st.subheader("📤 Manual Video Uploader (Upload Any Video from Desktop)")
    st.caption("Upload pre-recorded videos, screen captures, or edited clips from your computer directly to YouTube.")

    uploaded_file = st.file_uploader(
        "Choose a video file from your computer",
        type=["mp4", "mov", "mkv", "avi"],
        help="Supports standard formats up to YouTube's size limit."
    )

    if uploaded_file is not None:
        col_m_preview, col_m_form = st.columns([2, 3])

        with col_m_preview:
            st.video(uploaded_file)
            st.caption(f"📁 **File**: `{uploaded_file.name}` ({uploaded_file.size / (1024*1024):.2f} MB)")

        with col_m_form:
            # AI Metadata helper
            with st.expander("✨ AI Auto-Fill Title & Description"):
                ai_topic = st.text_input("Enter video concept or keywords:", placeholder="e.g. My Trip to Japan Vlog")
                if st.button("Generate SEO Metadata"):
                    if ai_topic.strip():
                        with st.spinner("Generating SEO title and description with Gemini..."):
                            ai_data = generate_video_script(ai_topic, format_type="standard")
                            st.session_state["manual_title"] = ai_data.get("title", "")
                            st.session_state["manual_desc"] = ai_data.get("description", "")
                            st.session_state["manual_tags"] = ", ".join(ai_data.get("tags", []))
                            st.rerun()

            manual_title = st.text_input(
                "YouTube Video Title",
                value=st.session_state.get("manual_title", uploaded_file.name.rsplit(".", 1)[0]),
                max_chars=100
            )

            manual_desc = st.text_area(
                "Video Description",
                value=st.session_state.get("manual_desc", "Uploaded via AutoTube AI Studio.\n\n#Video"),
                height=130
            )

            manual_tags_str = st.text_input(
                "Tags (comma separated)",
                value=st.session_state.get("manual_tags", "Video, YouTube, Creator")
            )

            col_cat, col_priv = st.columns(2)
            with col_cat:
                category_options = {
                    "Education (27)": "27",
                    "Science & Technology (28)": "28",
                    "Entertainment (24)": "24",
                    "People & Blogs (22)": "22",
                    "Howto & Style (26)": "26",
                    "Gaming (20)": "20"
                }
                selected_cat_label = st.selectbox("Category", list(category_options.keys()), index=0)
                selected_cat_id = category_options[selected_cat_label]

            with col_priv:
                manual_privacy = st.selectbox(
                    "Privacy Status",
                    ["unlisted", "public", "private"],
                    index=0
                )

            st.write("")
            start_manual_upload = st.button("🚀 Upload to YouTube Channel", type="primary", use_container_width=True)

            if start_manual_upload:
                if not manual_title.strip():
                    st.error("Please provide a title for the video.")
                else:
                    saved_temp_path = VIDEO_DIR / f"manual_{uuid.uuid4().hex[:6]}_{uploaded_file.name}"
                    with open(saved_temp_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())

                    tag_list = [t.strip() for t in manual_tags_str.split(",") if t.strip()]

                    upload_progress_bar = st.progress(0.0)
                    upload_status_lbl = st.empty()

                    def on_upload_progress(pct, msg):
                        upload_progress_bar.progress(pct)
                        upload_status_lbl.info(msg)

                    try:
                        upload_status_lbl.info("Connecting to YouTube Data API...")
                        res = upload_video_to_youtube(
                            video_path=str(saved_temp_path),
                            title=manual_title.strip(),
                            description=manual_desc,
                            tags=tag_list,
                            privacy_status=manual_privacy,
                            category_id=selected_cat_id,
                            progress_callback=on_upload_progress
                        )

                        yt_url = res.get("youtube_url", "")
                        yt_id = res.get("video_id", "")

                        vid_id = f"manual_{uuid.uuid4().hex[:6]}"
                        create_video_record(
                            video_id=vid_id,
                            topic=manual_title.strip(),
                            format_type="custom"
                        )
                        update_video_record(vid_id, {
                            "title": manual_title.strip(),
                            "description": manual_desc,
                            "tags": tag_list,
                            "video_path": str(saved_temp_path),
                            "status": "uploaded",
                            "youtube_id": yt_id,
                            "youtube_url": yt_url,
                            "privacy_status": manual_privacy,
                            "uploaded_at": datetime.now().isoformat()
                        })

                        upload_progress_bar.empty()
                        upload_status_lbl.empty()

                        st.success(f"🎉 Successfully Uploaded to YouTube!")
                        st.markdown(f"🔗 **Watch your video on YouTube**: [{yt_url}]({yt_url})")

                    except Exception as e:
                        st.error(f"YouTube Upload Failed: {e}")

# -------------------------------------------------------------
# TAB 3: VIDEO LIBRARY & STATUS
# -------------------------------------------------------------
with tab_library:
    st.subheader("Your Generated & Uploaded Videos")

    f_col1, f_col2 = st.columns([1, 4])
    with f_col1:
        if st.button("🔄 Refresh List"):
            st.rerun()
    with f_col2:
        filter_status = st.selectbox(
            "Filter by Status:",
            ["All", "Uploaded to YouTube", "Drafts (Ready to Upload)", "Failed"],
            index=0
        )

    all_vids = get_all_videos()
    
    if filter_status == "Uploaded to YouTube":
        filtered_vids = [v for v in all_vids if v.get("status") == "uploaded"]
    elif filter_status == "Drafts (Ready to Upload)":
        filtered_vids = [v for v in all_vids if v.get("status") in ["draft_ready", "video_rendered"]]
    elif filter_status == "Failed":
        filtered_vids = [v for v in all_vids if v.get("status") == "failed"]
    else:
        filtered_vids = all_vids

    if not filtered_vids:
        st.info("No videos found matching the current filter.")
    else:
        for vid in filtered_vids:
            vid_id = vid.get("id")
            title = vid.get("title") or vid.get("topic") or "Untitled Video"
            status = vid.get("status", "unknown")
            created_at = vid.get("created_at", "")
            yt_url = vid.get("youtube_url", "")
            video_file = vid.get("video_path", "")

            with st.container():
                st.markdown(f"#### {title}")
                c_vid, c_info, c_action = st.columns([2, 3, 2])

                with c_vid:
                    if video_file and Path(video_file).exists():
                        st.video(video_file)
                    else:
                        st.caption("*(Video file not found or rendering)*")

                with c_info:
                    if status == "uploaded":
                        st.markdown(f'<span class="badge-uploaded">✓ UPLOADED TO YOUTUBE</span>', unsafe_allow_html=True)
                        if yt_url:
                            st.markdown(f"🔗 [Watch on YouTube]({yt_url})")
                    elif status in ["draft_ready", "video_rendered"]:
                        st.markdown(f'<span class="badge-draft">DRAFT - READY TO PUBLISH</span>', unsafe_allow_html=True)
                    else:
                        st.markdown(f'<span class="badge-failed">{status.upper()}</span>', unsafe_allow_html=True)
                        if vid.get("error_message"):
                            st.caption(f"Error: {vid.get('error_message')}")

                    st.caption(f"**Topic**: {vid.get('topic')}")
                    st.caption(f"**Format**: {vid.get('format', 'shorts')} | **Created**: {created_at[:19] if created_at else 'N/A'}")
                    
                    if vid.get("scenes"):
                        with st.expander("View Script & Scenes"):
                            for sc in vid.get("scenes", []):
                                st.markdown(f"**Scene {sc.get('scene_number')}**: {sc.get('narration')}")

                with c_action:
                    if status != "uploaded" and video_file and Path(video_file).exists():
                        if st.button(f"🚀 Upload to YouTube", key=f"up_{vid_id}", use_container_width=True):
                            with st.spinner("Connecting to YouTube and uploading video..."):
                                try:
                                    res = upload_video_to_youtube(
                                        video_path=video_file,
                                        title=title,
                                        description=vid.get("description", ""),
                                        tags=vid.get("tags", []),
                                        privacy_status=vid.get("privacy_status", "unlisted")
                                    )
                                    update_video_record(vid_id, {
                                        "status": "uploaded",
                                        "youtube_id": res.get("video_id"),
                                        "youtube_url": res.get("youtube_url"),
                                        "uploaded_at": datetime.now().isoformat()
                                    })
                                    st.success(f"Uploaded! [View on YouTube]({res.get('youtube_url')})")
                                    st.rerun()
                                except Exception as upload_err:
                                    st.error(f"Upload failed: {upload_err}")

                    if st.button("🗑️ Delete Record", key=f"del_{vid_id}", use_container_width=True):
                        delete_video_record(vid_id)
                        st.rerun()

                st.divider()

# -------------------------------------------------------------
# TAB 4: CREDENTIALS & CHANNELS
# -------------------------------------------------------------
with tab_settings:
    st.subheader("Channels & API Configuration")

    st.markdown("### 1. YouTube Channel Authentication")
    curr_channel = get_channel_info()
    if curr_channel:
        st.success(f"✓ Connected to Channel: **{curr_channel.get('title')}** ({curr_channel.get('custom_url')})")
        col_auth1, col_auth2 = st.columns(2)
        with col_auth1:
            if st.button("🔄 Switch YouTube Channel / Account"):
                disconnect_channel()
                st.session_state["show_auth_panel"] = True
                st.rerun()
        with col_auth2:
            if st.button("Disconnect Channel"):
                disconnect_channel()
                st.rerun()
    else:
        st.warning("⚠️ No channel authenticated yet.")
        
        # Check client_secret.json
        if not Path(YOUTUBE_CLIENT_SECRET_FILE).exists():
            st.error("❌ `client_secret.json` is missing on this cloud instance.")
            st.markdown("Upload your `client_secret.json` file to enable YouTube features:")
            uploaded_secret = st.file_uploader("Upload client_secret.json", type=["json"], key="up_secret_file")
            if uploaded_secret is not None:
                with open(YOUTUBE_CLIENT_SECRET_FILE, "wb") as f:
                    f.write(uploaded_secret.getbuffer())
                st.success("✓ `client_secret.json` uploaded successfully!")
                st.rerun()

        # Check token.pickle (Direct cloud sync without OAuth loops!)
        if not Path(YOUTUBE_TOKEN_FILE).exists():
            st.info("💡 **Quick Cloud Connect**: If you already authorized locally on your PC, upload your `token.pickle`:")
            uploaded_token = st.file_uploader("Upload token.pickle (from D:\\youtube_video_automation\\token.pickle)", type=["pickle"], key="up_token_file")
            if uploaded_token is not None:
                with open(YOUTUBE_TOKEN_FILE, "wb") as f:
                    f.write(uploaded_token.getbuffer())
                st.success("✓ `token.pickle` uploaded successfully! Channel connected.")
                st.rerun()

        if Path(YOUTUBE_CLIENT_SECRET_FILE).exists() and not Path(YOUTUBE_TOKEN_FILE).exists():
            st.success("✓ `client_secret.json` is installed.")
            if st.button("🔑 Connect YouTube Channel Now", type="primary"):
                st.session_state["show_auth_panel"] = True
                start_nonblocking_oauth()
                st.rerun()

    st.markdown("### 2. Google Gemini & Veo API")
    if GEMINI_API_KEY:
        st.success(f"✓ Google AI API Key configured (`{GEMINI_API_KEY[:6]}...{GEMINI_API_KEY[-4:]}`)")
    else:
        st.error("Google AI API key not set.")
        st.markdown("Set `GEMINI_API_KEY` in Streamlit Cloud Secrets or in `.env`.")
        input_key = st.text_input("Or enter Gemini API Key temporarily:", type="password")
        if st.button("Save API Key"):
            if input_key.strip():
                with open(BASE_DIR / ".env", "a") as f:
                    f.write(f"\nGEMINI_API_KEY={input_key.strip()}\n")
                st.success("Saved! Reloading...")
                st.rerun()

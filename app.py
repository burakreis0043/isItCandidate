import os
import json
import html
import tempfile
import pandas as pd
import streamlit as st

from cv_screening_engine import CVScreeningEngine
from db_manager import DatabaseManager

# --- SAYFA YAPILANDIRMASI (KURUMSAL PROFESYONEL TEMA) ---
st.set_page_config(
    page_title="isItCandidate | AI Screening & Match Studio",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- YARDIMCI FONKSİYONLAR ---
def get_initials(name: str) -> str:
    """Aday isminden avatar baş harflerini üretir (Örn: Mert Yılmaz -> MY)."""
    parts = [p for p in name.strip().split() if p]
    if len(parts) >= 2:
        return (parts[0][0] + parts[-1][0]).upper()
    elif len(parts) == 1 and len(parts[0]) > 0:
        return parts[0][:2].upper()
    return "CV"


# --- PROFESYONEL TASARIM SİSTEMİ & CSS ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

    html, body, [class*="css"], .stApp {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
        -webkit-font-smoothing: antialiased;
        letter-spacing: -0.015em;
    }

    code, pre {
        font-family: 'JetBrains Mono', monospace !important;
    }

    h1, h2, h3, h4 {
        letter-spacing: -0.035em !important;
        font-weight: 700 !important;
    }

    /* Sol Kenar Çubuğunu Gizle - Tam Genişlikli Studio Tasarımı */
    section[data-testid="stSidebar"], [data-testid="collapsedControl"] {
        display: none !important;
    }
    .main .block-container {
        max-width: 95% !important;
        padding-top: 1.5rem !important;
        padding-bottom: 3.5rem !important;
    }

    /* Derin Koyu Zemin & Ambient Glow */
    .stApp {
        background-color: #061312 !important;
        background-image: 
            radial-gradient(circle at 10% 10%, rgba(13, 148, 136, 0.16) 0px, transparent 45%),
            radial-gradient(circle at 90% 15%, rgba(20, 184, 166, 0.1) 0px, transparent 40%),
            radial-gradient(circle at 50% 95%, rgba(6, 78, 59, 0.22) 0px, transparent 60%) !important;
        color: #F0FDFA !important;
    }

    /* İnce Scrollbar */
    ::-webkit-scrollbar {
        width: 6px;
        height: 6px;
    }
    ::-webkit-scrollbar-track {
        background: #061312;
    }
    ::-webkit-scrollbar-thumb {
        background: #115E59;
        border-radius: 9999px;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: #14B8A6;
    }

    /* Kurumsal Kart Paneli */
    .teal-target-card {
        background: rgba(9, 29, 27, 0.82);
        border: 1px solid rgba(20, 184, 166, 0.2);
        border-radius: 16px;
        padding: 22px 24px;
        box-shadow: 0 10px 30px -10px rgba(0, 0, 0, 0.5);
        backdrop-filter: blur(16px);
        margin-bottom: 20px;
    }
    .teal-target-header {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 1.15rem;
        font-weight: 700;
        color: #FFFFFF;
        padding-bottom: 12px;
        margin-bottom: 14px;
        border-bottom: 1px solid rgba(20, 184, 166, 0.16);
        letter-spacing: -0.02em;
    }

    /* Form Girdi Alanları */
    .stTextInput input, .stTextArea textarea, div[data-baseweb="select"] > div {
        background-color: rgba(9, 29, 27, 0.9) !important;
        border: 1px solid rgba(20, 184, 166, 0.22) !important;
        border-radius: 10px !important;
        color: #F0FDFA !important;
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        font-size: 0.9rem !important;
        transition: all 0.2s ease !important;
    }
    .stTextInput input:focus, .stTextArea textarea:focus, div[data-baseweb="select"] > div:focus-within {
        border-color: #14B8A6 !important;
        box-shadow: 0 0 0 3px rgba(20, 184, 166, 0.25) !important;
        background-color: rgba(9, 29, 27, 0.98) !important;
    }

    /* Butonlar */
    div.stButton > button {
        border-radius: 10px !important;
        font-weight: 600 !important;
        font-size: 0.88rem !important;
        padding: 9px 20px !important;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
        border: 1px solid rgba(20, 184, 166, 0.2) !important;
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        letter-spacing: -0.01em;
    }
    div.stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #0F766E 0%, #0D9488 50%, #14B8A6 100%) !important;
        color: #FFFFFF !important;
        border: 1px solid rgba(45, 212, 191, 0.3) !important;
        box-shadow: 0 4px 16px rgba(13, 148, 136, 0.35) !important;
    }
    div.stButton > button[kind="primary"]:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 24px rgba(20, 184, 166, 0.5) !important;
        background: linear-gradient(135deg, #0D9488 0%, #14B8A6 100%) !important;
    }
    div.stButton > button[kind="secondary"] {
        background: rgba(15, 41, 39, 0.7) !important;
        color: #CCFBF1 !important;
    }
    div.stButton > button[kind="secondary"]:hover {
        background: rgba(19, 78, 74, 0.8) !important;
        transform: translateY(-1px) !important;
        border-color: rgba(45, 212, 191, 0.45) !important;
    }

    /* Etiketler ve Tipografi Standartları */
    label[data-testid="stWidgetLabel"] p, label[data-testid="stWidgetLabel"] span {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        font-weight: 600 !important;
        font-size: 0.86rem !important;
        color: #CCFBF1 !important;
        letter-spacing: -0.01em !important;
    }

    /* Streamlit Expander Akordeon */
    div[data-testid="stExpander"] {
        background: rgba(9, 29, 27, 0.6) !important;
        border: 1px solid rgba(20, 184, 166, 0.2) !important;
        border-radius: 12px !important;
        overflow: hidden;
        margin-top: 8px;
    }
    div[data-testid="stExpander"] details summary {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        font-weight: 600 !important;
        color: #5EEAD4 !important;
        font-size: 0.88rem !important;
    }
    div[data-testid="stExpander"] details summary:hover {
        color: #2DD4BF !important;
    }

    /* Dışa Aktarma / Download Butonu */
    div.stDownloadButton > button {
        border-radius: 10px !important;
        font-weight: 600 !important;
        font-size: 0.88rem !important;
        padding: 9px 20px !important;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
        border: 1px solid rgba(20, 184, 166, 0.3) !important;
        background: rgba(15, 41, 39, 0.7) !important;
        color: #CCFBF1 !important;
        font-family: 'Plus Jakarta Sans', sans-serif !important;
    }
    div.stDownloadButton > button:hover {
        background: rgba(19, 78, 74, 0.85) !important;
        border-color: rgba(45, 212, 191, 0.5) !important;
        color: #FFFFFF !important;
    }

    /* Dosya Yükleyici */
    div[data-testid="stFileUploader"] section {
        background-color: rgba(9, 29, 27, 0.5) !important;
        border: 1px dashed rgba(20, 184, 166, 0.3) !important;
        border-radius: 12px !important;
    }
    div[data-testid="stFileUploader"] section:hover {
        border-color: #14B8A6 !important;
    }

    /* Streamlit Tabs Tasarımı */
    .stTabs [data-baseweb="tab-list"] {
        gap: 12px;
        background-color: rgba(9, 29, 27, 0.75);
        padding: 6px;
        border-radius: 12px;
        border: 1px solid rgba(20, 184, 166, 0.2);
        margin-bottom: 22px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        color: #99F6E4 !important;
        font-weight: 600 !important;
        font-size: 0.92rem !important;
        padding: 9px 22px !important;
        border: none !important;
        font-family: 'Plus Jakarta Sans', sans-serif !important;
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #0F766E 0%, #0D9488 100%) !important;
        color: #FFFFFF !important;
        box-shadow: 0 4px 12px rgba(13, 148, 136, 0.4) !important;
    }

    /* Kurumsal Üst Bar */
    .teal-navbar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 12px 24px;
        background: rgba(9, 29, 27, 0.85);
        backdrop-filter: blur(20px);
        border: 1px solid rgba(20, 184, 166, 0.2);
        border-radius: 9999px;
        margin-bottom: 22px;
        box-shadow: 0 10px 25px -10px rgba(0, 0, 0, 0.5);
    }
    .teal-brand-logo {
        display: flex;
        align-items: center;
        gap: 10px;
        font-size: 1.25rem;
        font-weight: 800;
        letter-spacing: -0.03em;
        color: #FFFFFF;
    }
    .teal-logo-badge {
        width: 28px;
        height: 28px;
        background: linear-gradient(135deg, #14B8A6, #0D9488);
        border-radius: 7px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 0.85rem;
        font-weight: 800;
        color: #FFFFFF;
        box-shadow: 0 0 10px rgba(20, 184, 166, 0.5);
    }
    .teal-status-badge {
        background: rgba(20, 184, 166, 0.12);
        color: #5EEAD4;
        border: 1px solid rgba(20, 184, 166, 0.3);
        padding: 5px 14px;
        border-radius: 9999px;
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        display: inline-flex;
        align-items: center;
        gap: 8px;
    }
    .teal-pulse-dot {
        width: 7px;
        height: 7px;
        background-color: #2DD4BF;
        border-radius: 50%;
        box-shadow: 0 0 10px #2DD4BF;
        animation: pulseTeal 2s infinite;
    }
    @keyframes pulseTeal {
        0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(45, 212, 191, 0.7); }
        70% { transform: scale(1.05); box-shadow: 0 0 0 8px rgba(45, 212, 191, 0); }
        100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(45, 212, 191, 0); }
    }

    /* Hero Bölümü */
    .teal-hero-container {
        padding: 6px 4px 18px 4px;
        position: relative;
    }
    .teal-pill-tag {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        background: rgba(20, 184, 166, 0.12);
        border: 1px solid rgba(45, 212, 191, 0.28);
        color: #2DD4BF;
        padding: 4px 12px;
        border-radius: 9999px;
        font-size: 0.74rem;
        font-weight: 700;
        margin-bottom: 8px;
        letter-spacing: 0.05em;
        text-transform: uppercase;
    }
    .teal-hero-title {
        font-size: 2.35rem;
        font-weight: 800;
        line-height: 1.15;
        letter-spacing: -0.04em;
        color: #FFFFFF;
        margin-bottom: 6px;
    }
    .teal-hero-title span {
        background: linear-gradient(135deg, #2DD4BF 0%, #14B8A6 60%, #38BDF8 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .teal-hero-subtitle {
        font-size: 0.98rem;
        color: #99F6E4;
        max-width: 820px;
        line-height: 1.5;
        margin-bottom: 16px;
        opacity: 0.9;
    }

    /* KPI Metrik Kartları */
    .teal-kpi-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
        gap: 12px;
        margin-bottom: 20px;
    }
    .teal-kpi-card {
        background: rgba(9, 29, 27, 0.78);
        border: 1px solid rgba(20, 184, 166, 0.2);
        border-radius: 14px;
        padding: 15px 18px;
        backdrop-filter: blur(16px);
        transition: transform 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;
        position: relative;
        overflow: hidden;
    }
    .teal-kpi-card:hover {
        border-color: rgba(45, 212, 191, 0.5);
        transform: translateY(-2px);
        box-shadow: 0 10px 24px -6px rgba(0, 0, 0, 0.4);
    }
    .teal-kpi-icon-bar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 6px;
    }
    .teal-kpi-number {
        font-size: 1.85rem;
        font-weight: 800;
        letter-spacing: -0.03em;
        margin-bottom: 2px;
        color: #FFFFFF;
        font-family: 'JetBrains Mono', monospace;
    }
    .teal-kpi-label {
        font-size: 0.72rem;
        color: #5EEAD4;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    /* Aday Kartı */
    .teal-candidate-card {
        background: rgba(9, 29, 27, 0.85);
        border: 1px solid rgba(20, 184, 166, 0.2);
        border-radius: 16px;
        padding: 20px 22px;
        margin-bottom: 16px;
        transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
        position: relative;
        backdrop-filter: blur(16px);
        box-shadow: 0 6px 20px -6px rgba(0, 0, 0, 0.45);
    }
    .teal-candidate-card:hover {
        border-color: rgba(45, 212, 191, 0.55);
        box-shadow: 0 14px 30px -8px rgba(0, 0, 0, 0.6), 0 0 20px rgba(20, 184, 166, 0.15);
        transform: translateY(-2px);
    }
    .teal-card-strip-call {
        border-left: 4px solid #10B981 !important;
    }
    .teal-card-strip-reserve {
        border-left: 4px solid #F59E0B !important;
    }
    .teal-card-strip-reject {
        border-left: 4px solid #F43F5E !important;
    }

    .teal-card-header {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        margin-bottom: 12px;
        gap: 16px;
    }
    .teal-candidate-identity {
        display: flex;
        align-items: center;
        gap: 14px;
        flex: 1;
        min-width: 0;
    }
    .teal-avatar {
        width: 46px;
        height: 46px;
        border-radius: 12px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 800;
        font-size: 1.05rem;
        color: #FFFFFF;
        flex-shrink: 0;
        border: 1px solid rgba(45, 212, 191, 0.35);
        box-shadow: 0 3px 10px rgba(0, 0, 0, 0.35);
        font-family: 'JetBrains Mono', monospace;
    }
    .teal-name-row {
        display: flex;
        align-items: center;
        gap: 8px;
        flex-wrap: wrap;
        margin-bottom: 4px;
    }
    .teal-candidate-name {
        margin: 0;
        font-size: 1.35rem;
        font-weight: 800;
        color: #FFFFFF;
        letter-spacing: -0.03em;
    }
    .teal-candidate-meta {
        color: #99F6E4;
        font-size: 0.88rem;
        display: flex;
        align-items: center;
        flex-wrap: wrap;
        gap: 8px;
    }
    .teal-candidate-meta code {
        background: rgba(20, 184, 166, 0.12);
        border: 1px solid rgba(20, 184, 166, 0.25);
        padding: 2px 7px;
        border-radius: 5px;
        color: #CCFBF1;
        font-size: 0.8rem;
    }

    /* Match Score Göstergesi */
    .teal-match-gauge {
        min-width: 120px;
        padding: 8px 12px;
        border-radius: 12px;
        background: rgba(4, 47, 46, 0.7);
        border: 1px solid rgba(45, 212, 191, 0.3);
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        flex-shrink: 0;
    }
    .teal-match-val {
        font-size: 1.45rem;
        font-weight: 800;
        letter-spacing: -0.03em;
        font-family: 'JetBrains Mono', monospace;
    }
    .teal-match-tag {
        font-size: 0.64rem;
        font-weight: 700;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        margin-top: 1px;
    }
    .teal-progress-track {
        width: 100%;
        height: 4px;
        background: rgba(255, 255, 255, 0.1);
        border-radius: 9999px;
        margin-top: 5px;
        overflow: hidden;
    }
    .teal-progress-fill {
        height: 100%;
        border-radius: 9999px;
    }

    /* Rozetler */
    .teal-badge-pill {
        display: inline-flex;
        align-items: center;
        gap: 5px;
        padding: 3px 10px;
        border-radius: 9999px;
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.03em;
        text-transform: uppercase;
    }

    /* Yönetici Değerlendirme Raporu */
    .teal-advice-card {
        background: rgba(4, 28, 26, 0.6);
        border: 1px solid rgba(20, 184, 166, 0.16);
        border-left: 3px solid #14B8A6;
        border-radius: 12px;
        padding: 12px 15px;
        margin: 12px 0;
    }
    .teal-advice-header {
        font-size: 0.76rem;
        color: #2DD4BF;
        font-weight: 700;
        margin-bottom: 4px;
        letter-spacing: 0.05em;
        text-transform: uppercase;
    }
    .teal-advice-text {
        font-size: 0.9rem;
        color: #E6FFFA;
        line-height: 1.55;
    }

    /* Yetkinlik Hapları */
    .teal-keyword-pill {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        padding: 3px 10px;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
        letter-spacing: 0.01em;
    }
    .teal-keyword-match {
        border: 1px solid rgba(45, 212, 191, 0.35);
        background: rgba(20, 184, 166, 0.12);
        color: #5EEAD4;
    }
    .teal-keyword-gap {
        border: 1px solid rgba(244, 63, 94, 0.35);
        background: rgba(244, 63, 94, 0.1);
        color: #FDA4AF;
    }
</style>
""", unsafe_allow_html=True)


# --- SESSION STATE BAŞLATMA ---
if "engine" not in st.session_state:
    st.session_state.engine = CVScreeningEngine(model_name="qwen2.5:14b")

if "db" not in st.session_state:
    st.session_state.db = DatabaseManager()

if "results" not in st.session_state:
    st.session_state.results = []

if "filter_status" not in st.session_state:
    st.session_state.filter_status = "TÜMÜ"

# Önceden tanımlı hazır pozisyon şablonları
PRESET_TEMPLATES = {
    "Senior Python & Backend Developer": {
        "title": "Senior Python & FastAPI Developer",
        "mandatory": "En az 4 yıl Python tecrübesi, FastAPI veya Django uzmanlığı, PostgreSQL ve Redis, Docker ile container mimarisi, Akıcı teknik İngilizce.",
        "bonus": "Kubernetes (K8s) tecrübesi, Mikroservis mimarisi, CI/CD pipeline tasarımı, Ekip liderliği veya genç geliştirici mentörlüğü.",
        "policies": "Haftada en az 2 gün İstanbul Kadıköy ofisinde bulunabilecek adaylar kabul edilir (Hibrit Model). %100 uzaktan çalışma seçeneği yoktur. Erkek adaylar için askerlik tamamlanmış veya en az 2 yıl tecilli olmalıdır."
    },
    "AI / Makine Öğrenmesi Mühendisi": {
        "title": "Senior AI & Machine Learning Engineer",
        "mandatory": "En az 3 yıl Python ve PyTorch/TensorFlow deneyimi, NLP, LLM fine-tuning, RAG (Retrieval-Augmented Generation) ve Vektör Veritabanları (Chroma, Qdrant vb.), Docker.",
        "bonus": "Ollama veya vLLM ile yerel model deployment tecrübesi, HuggingFace transformers, LangChain/LlamaIndex bilgisi.",
        "policies": "Hibrit veya tam uzaktan çalışmaya uygundur. İleri düzey İngilizce (C1) zorunludur (uluslararası ekiplerle toplantı yapılır)."
    },
    "Kıdemli Frontend / React Geliştirici": {
        "title": "Senior Frontend Developer (React / Next.js)",
        "mandatory": "En az 4 yıl modern JavaScript/TypeScript, React ve Next.js deneyimi, Tailwind CSS, Responsive & Mobile-first tasarım prensipleri.",
        "bonus": "Figma'dan pixel-perfect kodlama, Framer Motion veya GSAP animasyonları, State management (Zustand, Redux Toolkit).",
        "policies": "Haftada 1 gün ofis, 4 gün uzaktan (Esnek Hibrit). İstanbul içi ikamet tercih sebebidir."
    }
}


# --- ÜST BAR (KURUMSAL NAVBAR) ---
active_backend = st.session_state.db.backend_name

st.html(f"""
<div class="teal-navbar">
    <div class="teal-brand-logo">
        <div class="teal-logo-badge" style="font-size: 0.78rem; letter-spacing: -0.04em; font-weight: 800;">iC</div>
        <span>isIt<span style="color:#2DD4BF;">Candidate</span></span>
        <span style="font-weight:400; color:#5EEAD4; font-size: 0.85rem; margin-left: 6px; letter-spacing: 0.03em;">| AI SCREENING & MATCH STUDIO</span>
    </div>
    <div class="teal-status-badge">
        <span class="teal-pulse-dot"></span>
        QWEN 2.5:14B LOCAL ENGINE · {active_backend} CONNECTED
    </div>
</div>
""")


# --- HERO BÖLÜMÜ ---
st.html("""
<div class="teal-hero-container">
    <div class="teal-pill-tag">
        <span>ENTERPRISE TALENT INTELLIGENCE</span>
    </div>
    <div class="teal-hero-title">
        Hedef Pozisyon ve Kurumsal Politikalarla<br>
        <span>Yapay Zeka Destekli CV Eleme ve Eşleştirme</span>
    </div>
    <div class="teal-hero-subtitle">
        Aday özgeçmişlerini belirlediğiniz pozisyon kriterleri, teknik yetkinlikler ve katı şirket politikalarıyla eşleştirin. 
        Yerel yapay zeka motoru ile ATS anahtar kelime uyumunu ve eksik yetkinlikleri anında tespit edin.
    </div>
</div>
""")



# --- ANA ÇALIŞMA ALANI SEKMELERİ (STUDIO & TALENT POOL) ---
tab_studio, tab_pool = st.tabs([
    "Aday İnceleme ve Eşleştirme Stüdyosu",
    f"Kayıtlı Aday Havuzu (Talent Pool — {st.session_state.db.backend_name})"
])

with tab_studio:
    # --- İKİ SÜTUNLU SPLIT STUDIO ÇALIŞMA ALANI ---
    col_target, col_matcher = st.columns([5, 7], gap="large")


    # ==========================================
    # SOL SÜTUN: HEDEF POZİSYON & KURUMSAL POLİTİKALAR
    # ==========================================
    with col_target:
        st.html("""
        <div class="teal-target-card">
            <div class="teal-target-header">
                HEDEF POZİSYON VE ŞİRKET POLİTİKALARI
            </div>
            <div style="font-size: 0.85rem; color: #99F6E4; opacity: 0.9;">
                Aday CV'leri aşağıdaki zorunlu nitelikler, tercihler ve çalışma koşulları baz alınarak puanlanacaktır.
            </div>
        </div>
        """)

        # Şablon seçimi
        selected_preset = st.selectbox(
            "Pozisyon Şablonu:",
            ["Özel Kriterler Belirle"] + list(PRESET_TEMPLATES.keys())
        )

        if selected_preset != "Özel Kriterler Belirle":
            preset_data = PRESET_TEMPLATES[selected_preset]
            default_title = preset_data["title"]
            default_mandatory = preset_data["mandatory"]
            default_bonus = preset_data["bonus"]
            default_policies = preset_data["policies"]
        else:
            default_title = "Senior Python & FastAPI Developer"
            default_mandatory = "En az 3 yıl Python tecrübesi, FastAPI veya Django bilgisi, Docker deneyimi, İngilizce."
            default_bonus = "Kubernetes, Mikroservisler, Ekip mentörlüğü tecrübesi."
            default_policies = "Haftada en az 2 gün İstanbul ofisinde bulunabilecek adaylar kabul edilir (Hibrit). Tam uzaktan çalışma yoktur."

        job_title = st.text_input("Hedef Pozisyon Unvanı", value=default_title)

        mandatory_reqs = st.text_area(
            "Zorunlu Nitelikler (Minimum Şartlar):",
            value=default_mandatory,
            height=120
        )

        bonus_reqs = st.text_area(
            "Tercih Sebebi Nitelikler (Artı Puan):",
            value=default_bonus,
            height=85
        )

        company_policies = st.text_area(
            "Kurumsal Politikalar ve Çalışma Modeli (Policy Gate):",
            value=default_policies,
            height=100,
            help="Örn: Çalışma modeli (Ofis/Hibrit), askerlik, ikametgah, seyahat engeli vb."
        )

        st.html("""
        <div style="background: rgba(4, 28, 26, 0.7); border: 1px solid rgba(20, 184, 166, 0.2); border-radius: 12px; padding: 13px 15px; margin-top: 14px;">
            <div style="font-size: 0.8rem; font-weight: 700; color: #2DD4BF; margin-bottom: 3px; letter-spacing: 0.04em; text-transform: uppercase;">VERİ GİZLİLİĞİ VE YEREL İŞLEME</div>
            <div style="font-size: 0.78rem; color: #99F6E4; line-height: 1.45;">Özgeçmiş verileri harici sunuculara aktarılmaz. Sistem, bilgisayarınızda çalışan yerel <strong>qwen2.5:14b</strong> modeliyle tamamen çevrimdışı yürütülür.</div>
        </div>
        """)


    # ==========================================
    # SAĞ SÜTUN: CV YÜKLEME, ANALİZ VE EŞLEŞTİRME SONUÇLARI
    # ==========================================
    with col_matcher:
        st.html("""
        <div class="teal-target-card">
            <div class="teal-target-header">
                ADAY PORTFÖYÜ VE EŞLEŞTİRME AKIŞI
            </div>
            <div style="font-size: 0.85rem; color: #99F6E4; opacity: 0.9;">
                PDF veya TXT formatındaki CV dosyalarını yükleyebilir veya örnek aday havuzu ile testi başlatabilirsiniz.
            </div>
        </div>
        """)

        sub_col1, sub_col2 = st.columns([3, 2], gap="medium")
        with sub_col1:
            uploaded_files = st.file_uploader(
                "Özgeçmiş Dosyalarını Seçin:",
                type=["pdf", "txt"],
                accept_multiple_files=True
            )
        with sub_col2:
            st.write("")
            st.write("")
            load_demo_btn = st.button("Örnek Portföyü Yükle (3 Aday)", use_container_width=True)

        # Analizi Başlat Butonu
        analyze_btn = st.button("Eşleştirme Analizini Başlat (Qwen 2.5:14B)", type="primary", use_container_width=True)

        # Dosya işleme mantığı
        files_to_process = []

        if load_demo_btn:
            demo_dir = "ornek_cvler"
            if os.path.exists(demo_dir):
                for fname in os.listdir(demo_dir):
                    fpath = os.path.join(demo_dir, fname)
                    with open(fpath, "r", encoding="utf-8") as f:
                        files_to_process.append((fname, f.read()))
                st.success("Örnek aday havuzu yüklendi. Analiz başlatılıyor...")
                analyze_btn = True

        elif analyze_btn and uploaded_files:
            for uf in uploaded_files:
                with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uf.name)[1]) as tmp:
                    tmp.write(uf.getvalue())
                    tmp_path = tmp.name

                extracted_text = st.session_state.engine.extract_text_from_file(tmp_path)
                files_to_process.append((uf.name, extracted_text))
                try:
                    os.remove(tmp_path)
                except:
                    pass

        if analyze_btn and files_to_process:
            st.session_state.results = []
            progress_bar = st.progress(0)
            status_text = st.empty()

            for idx, (filename, text) in enumerate(files_to_process):
                status_text.markdown(f"İnceleniyor ({idx + 1}/{len(files_to_process)}): `{filename}`...")

                result = st.session_state.engine.analyze_cv(
                    cv_text=text,
                    job_title=job_title,
                    mandatory_requirements=mandatory_reqs,
                    bonus_requirements=bonus_reqs,
                    company_policies=company_policies,
                    file_name=filename
                )

                # Veritabanına (PostgreSQL / SQLite) otomatik kaydet
                try:
                    db_cand_id = st.session_state.db.save_candidate(result, job_title)
                    result["db_id"] = db_cand_id
                except Exception as db_err:
                    result["db_id"] = None

                st.session_state.results.append(result)
                progress_bar.progress((idx + 1) / len(files_to_process))

            status_text.markdown(f"Tüm adayların analizi tamamlandı ve `{st.session_state.db.backend_name}` veritabanına kaydedildi.")
            st.toast(f"Adaylar başarıyla {st.session_state.db.backend_name} veritabanına işlendi.")

        # --- SONUÇLAR VE TEAL MATCH KARTLARI ---
        results = st.session_state.results

        if results:
            st.markdown("<hr style='border-color: rgba(20, 184, 166, 0.2); margin: 20px 0;'>", unsafe_allow_html=True)

            # İstatistik Hesaplama
            total_candidates = len(results)
            calls = [r for r in results if r.get("verdict") == "MÜLAKATA ÇAĞIR"]
            reserves = [r for r in results if r.get("verdict") == "YEDEK ADAY"]
            rejects = [r for r in results if r.get("verdict") == "UYGUN DEĞİL"]

            pct_call = int(len(calls)/total_candidates*100) if total_candidates else 0
            pct_reserves = int(len(reserves)/total_candidates*100) if total_candidates else 0
            pct_rejects = int(len(rejects)/total_candidates*100) if total_candidates else 0

            # KPI İstatistikleri Kartları
            st.html(f"""
            <div class="teal-kpi-grid">
                <div class="teal-kpi-card" style="border-top: 3px solid #14B8A6;">
                    <div class="teal-kpi-icon-bar">
                        <span style="font-size:0.7rem; color:#5EEAD4; font-weight:800; letter-spacing:0.06em;">TOPLAM</span>
                    </div>
                    <div class="teal-kpi-number">{total_candidates}</div>
                    <div class="teal-kpi-label">İncelenen</div>
                </div>
                <div class="teal-kpi-card" style="border-top: 3px solid #10B981;">
                    <div class="teal-kpi-icon-bar">
                        <span style="font-size:0.7rem; color:#34D399; font-weight:800; letter-spacing:0.06em;">%{pct_call} ORAN</span>
                    </div>
                    <div class="teal-kpi-number" style="color: #34D399;">{len(calls)}</div>
                    <div class="teal-kpi-label">Yüksek Uyum</div>
                </div>
                <div class="teal-kpi-card" style="border-top: 3px solid #F59E0B;">
                    <div class="teal-kpi-icon-bar">
                        <span style="font-size:0.7rem; color:#FBBF24; font-weight:800; letter-spacing:0.06em;">%{pct_reserves} ORAN</span>
                    </div>
                    <div class="teal-kpi-number" style="color: #FBBF24;">{len(reserves)}</div>
                    <div class="teal-kpi-label">Yedek Havuzu</div>
                </div>
                <div class="teal-kpi-card" style="border-top: 3px solid #F43F5E;">
                    <div class="teal-kpi-icon-bar">
                        <span style="font-size:0.7rem; color:#FB7185; font-weight:800; letter-spacing:0.06em;">%{pct_rejects} ORAN</span>
                    </div>
                    <div class="teal-kpi-number" style="color: #FB7185;">{len(rejects)}</div>
                    <div class="teal-kpi-label">Kural İhlali / Elenen</div>
                </div>
            </div>
            """)

            # Filtreleme Butonları & Dışa Aktarma
            filter_col1, filter_col2, filter_col3, filter_col4, export_col = st.columns([1, 1, 1, 1, 2])

            with filter_col1:
                if st.button(f"Tümü ({total_candidates})", use_container_width=True):
                    st.session_state.filter_status = "TÜMÜ"
            with filter_col2:
                if st.button(f"Mülakat ({len(calls)})", use_container_width=True):
                    st.session_state.filter_status = "MÜLAKATA ÇAĞIR"
            with filter_col3:
                if st.button(f"Yedek ({len(reserves)})", use_container_width=True):
                    st.session_state.filter_status = "YEDEK ADAY"
            with filter_col4:
                if st.button(f"Elenen ({len(rejects)})", use_container_width=True):
                    st.session_state.filter_status = "UYGUN DEĞİL"

            with export_col:
                df_export = pd.DataFrame([
                    {
                        "Dosya Adı": r.get("file_name"),
                        "Aday Adı": r.get("candidate_name"),
                        "Mevcut Unvan": r.get("current_title"),
                        "Tecrübe": r.get("experience_years"),
                        "Uyum Skoru": r.get("suitability_score"),
                        "Karar": r.get("verdict"),
                        "Politika İhlali": "EVET" if r.get("policy_violation") else "HAYIR",
                        "Özet": r.get("executive_summary")
                    }
                    for r in results
                ])
                csv_data = df_export.to_csv(index=False).encode('utf-8-sig')
                st.download_button(
                    "Değerlendirme Raporunu İndir (CSV)",
                    data=csv_data,
                    file_name="aday_degerlendirme_raporu.csv",
                    mime="text/csv",
                    use_container_width=True
                )

            st.markdown("<br>", unsafe_allow_html=True)

            # Filtreye göre sonuçları listeleme
            filtered_results = results
            if st.session_state.filter_status != "TÜMÜ":
                filtered_results = [r for r in results if r.get("verdict") == st.session_state.filter_status]

            # Puanına göre azalan sırala
            filtered_results = sorted(filtered_results, key=lambda x: x.get("suitability_score", 0), reverse=True)

            for res in filtered_results:
                verdict = res.get("verdict", "YEDEK ADAY")
                score = res.get("suitability_score", 50)
                raw_candidate_name = str(res.get("candidate_name", "İsimsiz Aday"))
                candidate_name = html.escape(raw_candidate_name)
                initials = html.escape(get_initials(raw_candidate_name))
                current_title = html.escape(str(res.get("current_title", "Uzmanlık Belirtilmemiş")))
                experience = html.escape(str(res.get("experience_years", "-")))
                policy_violation = res.get("policy_violation", False)
                file_name = html.escape(str(res.get("file_name", "CV.pdf")))
                executive_summary = html.escape(str(res.get("executive_summary", "")))

                # Kurumsal Stil ve Uyum Seviyesi
                if verdict == "MÜLAKATA ÇAĞIR":
                    card_strip = "teal-card-strip-call"
                    badge_class = "teal-badge-pill"
                    badge_style = "background: rgba(16, 185, 129, 0.15); color: #34D399; border: 1px solid rgba(16, 185, 129, 0.4);"
                    score_color = "#34D399"
                    score_tag = "YÜKSEK UYUM"
                    fill_color = "linear-gradient(90deg, #059669, #10B981)"
                    avatar_gradient = "linear-gradient(135deg, #065F46 0%, #0D9488 100%)"
                elif verdict == "YEDEK ADAY":
                    card_strip = "teal-card-strip-reserve"
                    badge_class = "teal-badge-pill"
                    badge_style = "background: rgba(245, 158, 11, 0.15); color: #FBBF24; border: 1px solid rgba(245, 158, 11, 0.4);"
                    score_color = "#FBBF24"
                    score_tag = "POTANSİYEL"
                    fill_color = "linear-gradient(90deg, #D97706, #F59E0B)"
                    avatar_gradient = "linear-gradient(135deg, #78350F 0%, #D97706 100%)"
                else:
                    card_strip = "teal-card-strip-reject"
                    badge_class = "teal-badge-pill"
                    badge_style = "background: rgba(244, 63, 94, 0.15); color: #FB7185; border: 1px solid rgba(244, 63, 94, 0.4);"
                    score_color = "#FB7185"
                    score_tag = "DÜŞÜK UYUM"
                    fill_color = "linear-gradient(90deg, #DC2626, #F43F5E)"
                    avatar_gradient = "linear-gradient(135deg, #881337 0%, #E11D48 100%)"

                policy_html = ""
                if policy_violation:
                    policy_html = "<span class='teal-badge-pill' style='background: rgba(244, 63, 94, 0.15); color: #FB7185; border: 1px solid rgba(244, 63, 94, 0.4); margin-left:6px;'>POLİTİKA İHLALİ</span>"

                matched_tags = "".join([f"<span class='teal-keyword-pill teal-keyword-match'><span style='font-weight:700;'>+</span> {html.escape(str(m))}</span>" for m in res.get("matched_requirements", [])])
                missing_tags = "".join([f"<span class='teal-keyword-pill teal-keyword-gap'><span style='font-weight:700;'>-</span> {html.escape(str(g))}</span>" for g in res.get("missing_or_gap_requirements", [])])

                # Aday Kartı HTML
                card_html = f"""
                <div class="teal-candidate-card {card_strip}">
                    <div class="teal-card-header">
                        <div class="teal-candidate-identity">
                            <div class="teal-avatar" style="background: {avatar_gradient};">
                                <span>{initials}</span>
                            </div>
                            <div>
                                <div class="teal-name-row">
                                    <h3 class="teal-candidate-name">{candidate_name}</h3>
                                    <span class="{badge_class}" style="{badge_style}">{verdict}</span>{policy_html}
                                </div>
                                <div class="teal-candidate-meta">
                                    <span>Unvan: <strong>{current_title}</strong></span>
                                    <span style="color:#115E59;">•</span>
                                    <span>Deneyim: <strong>{experience}</strong></span>
                                    <span style="color:#115E59;">•</span>
                                    <span>Dosya: <code>{file_name}</code></span>
                                </div>
                            </div>
                        </div>

                        <div class="teal-match-gauge">
                            <div class="teal-match-val" style="color: {score_color};">%{score}</div>
                            <div class="teal-match-tag" style="color: {score_color};">{score_tag}</div>
                            <div class="teal-progress-track">
                                <div class="teal-progress-fill" style="width: {score}%; background: {fill_color};"></div>
                            </div>
                        </div>
                    </div>

                    <div class="teal-advice-card">
                        <div class="teal-advice-header">YÖNETİCİ DEĞERLENDİRME ÖZETİ VE ATS RAPORU</div>
                        <div class="teal-advice-text">{executive_summary}</div>
                    </div>

                    <div style="margin-top: 12px;">
                        <div style="font-size: 0.74rem; font-weight: 700; color: #5EEAD4; margin-bottom: 6px; letter-spacing: 0.05em; text-transform: uppercase;">Eşleşen Yetkinlikler ve Eksik Alanlar:</div>
                        <div style="display: flex; flex-wrap: wrap; gap: 6px;">{matched_tags} {missing_tags}</div>
                    </div>
                </div>
                """
                st.html(card_html)

                # Genişletilebilir Detaylar (Mülakat Soruları ve Yetkinlikler)
                with st.expander(f"{candidate_name} — Mülakat Soruları ve Yetkinlik Doğrulama"):
                    col_q, col_detail = st.columns([1, 1], gap="medium")

                    with col_q:
                        st.markdown("##### Adaya Özel Mülakat Soruları:")
                        questions = res.get("tailored_interview_questions", [])
                        for q_idx, q in enumerate(questions):
                            st.markdown(f"**{q_idx + 1}.** {q}")

                    with col_detail:
                        st.markdown("##### Öne Çıkan Güçlü Yönler:")
                        for s in res.get("top_strengths", []):
                            st.markdown(f"• {s}")

                        st.markdown("##### Olası Riskler ve Doğrulama Noktaları:")
                        for r_risk in res.get("potential_risks", []):
                            st.markdown(f"• {r_risk}")
        else:
            st.info("Sol panelden kriterleri belirleyip aday CV dosyalarını yükleyin ve 'Eşleştirme Analizini Başlat' butonuna tıklayın.")


with tab_pool:
    st.html(f"""
    <div class="teal-target-card" style="margin-bottom: 16px;">
        <div class="teal-target-header" style="justify-content: space-between;">
            <span>KURUMSAL ADAY HAVUZU (TALENT POOL)</span>
            <span class="teal-status-badge" style="font-size: 0.7rem;">VERİTABANI: {st.session_state.db.backend_name}</span>
        </div>
        <div style="font-size: 0.85rem; color: #99F6E4; opacity: 0.9;">
            Daha önce analiz edilmiş tüm adaylar ilişkisel veritabanında saklanır. 
            Buradan aday geçmişini arayabilir, filtreleyebilir, mülakat aşamalarını güncelleyebilir ve mülakat sorularını inceleyebilirsiniz.
        </div>
    </div>
    """)

    db_stats = st.session_state.db.get_stats()
    total_db_cands = db_stats.get("total_candidates", 0)
    avg_score = db_stats.get("avg_score", 0)
    verdict_stats = db_stats.get("verdicts", {})
    call_count = verdict_stats.get("MÜLAKATA ÇAĞIR", 0)
    reserve_count = verdict_stats.get("YEDEK ADAY", 0)
    reject_count = verdict_stats.get("UYGUN DEĞİL", 0)

    # Canlı KPI Kartları
    st.html(f"""
    <div class="teal-kpi-grid">
        <div class="teal-kpi-card" style="border-top: 3px solid #14B8A6;">
            <div class="teal-kpi-icon-bar"><span style="font-size:0.7rem; color:#5EEAD4; font-weight:800;">TOPLAM HAVUZ</span></div>
            <div class="teal-kpi-number">{total_db_cands}</div>
            <div class="teal-kpi-label">Kayıtlı Aday</div>
        </div>
        <div class="teal-kpi-card" style="border-top: 3px solid #38BDF8;">
            <div class="teal-kpi-icon-bar"><span style="font-size:0.7rem; color:#38BDF8; font-weight:800;">ORTALAMA</span></div>
            <div class="teal-kpi-number">%{avg_score}</div>
            <div class="teal-kpi-label">Uyum Skoru</div>
        </div>
        <div class="teal-kpi-card" style="border-top: 3px solid #10B981;">
            <div class="teal-kpi-icon-bar"><span style="font-size:0.7rem; color:#34D399; font-weight:800;">MÜLAKAT</span></div>
            <div class="teal-kpi-number" style="color:#34D399;">{call_count}</div>
            <div class="teal-kpi-label">Yüksek Uyum</div>
        </div>
        <div class="teal-kpi-card" style="border-top: 3px solid #F59E0B;">
            <div class="teal-kpi-icon-bar"><span style="font-size:0.7rem; color:#FBBF24; font-weight:800;">YEDEK</span></div>
            <div class="teal-kpi-number" style="color:#FBBF24;">{reserve_count}</div>
            <div class="teal-kpi-label">Potansiyel</div>
        </div>
        <div class="teal-kpi-card" style="border-top: 3px solid #F43F5E;">
            <div class="teal-kpi-icon-bar"><span style="font-size:0.7rem; color:#FB7185; font-weight:800;">ELENEN</span></div>
            <div class="teal-kpi-number" style="color:#FB7185;">{reject_count}</div>
            <div class="teal-kpi-label">Uygun Değil</div>
        </div>
    </div>
    """)

    # SQL Filtreleme Çubuğu
    fcol1, fcol2, fcol3, fcol4 = st.columns([3, 2, 2, 2], gap="small")
    with fcol1:
        pool_search = st.text_input("Aday, Unvan veya Yetkinlik Ara (SQL Arama):", placeholder="Örn: Mert, Python, Docker, Fast...", key="sql_search_pool")
    with fcol2:
        saved_positions = ["TÜMÜ"] + st.session_state.db.get_unique_positions()
        pool_position = st.selectbox("Pozisyon:", saved_positions, key="sql_pos_pool")
    with fcol3:
        pool_verdict = st.selectbox("Karar Durumu:", ["TÜMÜ", "MÜLAKATA ÇAĞIR", "YEDEK ADAY", "UYGUN DEĞİL"], key="sql_verdict_pool")
    with fcol4:
        pool_min_score = st.slider("Minimum Uyum:", 0, 100, 0, key="sql_score_pool")

    # SQL Veritabanından Çek
    pool_candidates = st.session_state.db.get_candidates(
        search_query=pool_search,
        verdict_filter=pool_verdict,
        min_score=pool_min_score,
        position_filter=pool_position
    )

    if not pool_candidates:
        st.info("Kriterlere uygun kayıtlı aday bulunamadı. Yeni aday analizi yapmak için 'Aday İnceleme ve Eşleştirme Stüdyosu' sekmesini kullanabilirsiniz.")
    else:
        # İndirme ve Sayaç Çubuğu
        cnt_col, export_col = st.columns([3, 2])
        with cnt_col:
            st.markdown(f"<div style='font-size:0.9rem; color:#5EEAD4; padding-top:8px;'>Filtreye uygun <strong>{len(pool_candidates)}</strong> aday listeleniyor ({st.session_state.db.backend_name}).</div>", unsafe_allow_html=True)
        with export_col:
            df_export_pool = pd.DataFrame([
                {
                    "ID": c.get("id"),
                    "Aday": c.get("candidate_name"),
                    "Hedef Pozisyon": c.get("target_position"),
                    "Mevcut Unvan": c.get("current_title"),
                    "Tecrübe": c.get("experience_years"),
                    "Uyum Skoru": c.get("suitability_score"),
                    "Karar": c.get("verdict"),
                    "Aşama": c.get("status"),
                    "Tarih": str(c.get("created_at")),
                    "İK Notu": c.get("recruiter_notes", "")
                }
                for c in pool_candidates
            ])
            csv_pool = df_export_pool.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                "Aday Havuzunu İndir (CSV)",
                data=csv_pool,
                file_name="aday_havuzu_arsiv.csv",
                mime="text/csv",
                use_container_width=True,
                key="btn_dl_pool_csv"
            )

        st.markdown("<hr style='border-color: rgba(20, 184, 166, 0.2); margin: 16px 0;'>", unsafe_allow_html=True)

        # Aday Kartları
        for c in pool_candidates:
            cand_id = c.get("id")
            verdict = c.get("verdict", "YEDEK ADAY")
            score = c.get("suitability_score", 50)
            raw_candidate_name = str(c.get("candidate_name", "İsimsiz Aday"))
            candidate_name = html.escape(raw_candidate_name)
            initials = html.escape(get_initials(raw_candidate_name))
            current_title = html.escape(str(c.get("current_title", "Uzmanlık Belirtilmemiş")))
            experience = html.escape(str(c.get("experience_years", "-")))
            target_pos = html.escape(str(c.get("target_position", "-")))
            policy_violation = c.get("policy_violation", False)
            file_name = html.escape(str(c.get("file_name", "CV.pdf")))
            executive_summary = html.escape(str(c.get("executive_summary", "")))
            current_stage = str(c.get("status", "Yeni Başvuru"))
            recruiter_notes = str(c.get("recruiter_notes", ""))
            created_at_str = str(c.get("created_at", ""))[:16]

            if verdict == "MÜLAKATA ÇAĞIR":
                card_strip = "teal-card-strip-call"
                badge_class = "teal-badge-pill"
                badge_style = "background: rgba(16, 185, 129, 0.15); color: #34D399; border: 1px solid rgba(16, 185, 129, 0.4);"
                score_color = "#34D399"
                score_tag = "YÜKSEK UYUM"
                fill_color = "linear-gradient(90deg, #059669, #10B981)"
                avatar_gradient = "linear-gradient(135deg, #065F46 0%, #0D9488 100%)"
            elif verdict == "YEDEK ADAY":
                card_strip = "teal-card-strip-reserve"
                badge_class = "teal-badge-pill"
                badge_style = "background: rgba(245, 158, 11, 0.15); color: #FBBF24; border: 1px solid rgba(245, 158, 11, 0.4);"
                score_color = "#FBBF24"
                score_tag = "POTANSİYEL"
                fill_color = "linear-gradient(90deg, #D97706, #F59E0B)"
                avatar_gradient = "linear-gradient(135deg, #78350F 0%, #D97706 100%)"
            else:
                card_strip = "teal-card-strip-reject"
                badge_class = "teal-badge-pill"
                badge_style = "background: rgba(244, 63, 94, 0.15); color: #FB7185; border: 1px solid rgba(244, 63, 94, 0.4);"
                score_color = "#FB7185"
                score_tag = "DÜŞÜK UYUM"
                fill_color = "linear-gradient(90deg, #DC2626, #F43F5E)"
                avatar_gradient = "linear-gradient(135deg, #881337 0%, #E11D48 100%)"

            policy_html = ""
            if policy_violation:
                policy_html = "<span class='teal-badge-pill' style='background: rgba(244, 63, 94, 0.15); color: #FB7185; border: 1px solid rgba(244, 63, 94, 0.4); margin-left:6px;'>POLİTİKA İHLALİ</span>"

            matched_tags = "".join([f"<span class='teal-keyword-pill teal-keyword-match'><span style='font-weight:700;'>+</span> {html.escape(str(m))}</span>" for m in c.get("matched_requirements", [])])
            missing_tags = "".join([f"<span class='teal-keyword-pill teal-keyword-gap'><span style='font-weight:700;'>-</span> {html.escape(str(g))}</span>" for g in c.get("missing_requirements", [])])

            card_html = f"""
            <div class="teal-candidate-card {card_strip}">
                <div class="teal-card-header">
                    <div class="teal-candidate-identity">
                        <div class="teal-avatar" style="background: {avatar_gradient};">
                            <span>{initials}</span>
                        </div>
                        <div>
                            <div class="teal-name-row">
                                <h3 class="teal-candidate-name">{candidate_name}</h3>
                                <span class="{badge_class}" style="{badge_style}">{verdict}</span>
                                <span class="teal-badge-pill" style="background: rgba(20, 184, 166, 0.15); color: #5EEAD4; border: 1px solid rgba(20, 184, 166, 0.35); margin-left:4px;">{html.escape(current_stage)}</span>
                                {policy_html}
                            </div>
                            <div class="teal-candidate-meta">
                                <span>Hedef: <strong>{target_pos}</strong></span>
                                <span style="color:#115E59;">•</span>
                                <span>Unvan: <strong>{current_title}</strong></span>
                                <span style="color:#115E59;">•</span>
                                <span>Deneyim: <strong>{experience}</strong></span>
                                <span style="color:#115E59;">•</span>
                                <span>Kayıt: <code>{created_at_str}</code></span>
                            </div>
                        </div>
                    </div>
                    
                    <div class="teal-match-gauge">
                        <div class="teal-match-val" style="color: {score_color};">%{score}</div>
                        <div class="teal-match-tag" style="color: {score_color};">{score_tag}</div>
                        <div class="teal-progress-track">
                            <div class="teal-progress-fill" style="width: {score}%; background: {fill_color};"></div>
                        </div>
                    </div>
                </div>
                
                <div class="teal-advice-card">
                    <div class="teal-advice-header">YÖNETİCİ DEĞERLENDİRME ÖZETİ VE ATS RAPORU</div>
                    <div class="teal-advice-text">{executive_summary}</div>
                </div>

                <div style="margin-top: 12px;">
                    <div style="font-size: 0.74rem; font-weight: 700; color: #5EEAD4; margin-bottom: 6px; letter-spacing: 0.05em; text-transform: uppercase;">Eşleşen Yetkinlikler ve Eksik Alanlar:</div>
                    <div style="display: flex; flex-wrap: wrap; gap: 6px;">{matched_tags} {missing_tags}</div>
                </div>
            </div>
            """
            st.html(card_html)

            # Detaylar ve ATS Süreç Yönetimi
            with st.expander(f"{candidate_name} — ATS Süreci, İK Notları ve Mülakat Soruları (ID: #{cand_id})"):
                c_stage_col, c_notes_col = st.columns([1, 1], gap="medium")
                
                with c_stage_col:
                    st.markdown("##### Aday ATS Aşaması:")
                    stage_options = ["Yeni Başvuru", "Ön Eleme Geçti", "1. Mülakat Planlandı", "Teklif Aşamasında", "İşe Alındı", "Reddedildi"]
                    current_idx = stage_options.index(current_stage) if current_stage in stage_options else 0
                    new_selected_stage = st.selectbox(
                        "Mevcut Durum:",
                        stage_options,
                        index=current_idx,
                        key=f"stage_sel_{cand_id}"
                    )
                    
                    new_note_val = st.text_area(
                        "İK & Mülakatçı Değerlendirme Notu:",
                        value=recruiter_notes,
                        key=f"notes_val_{cand_id}",
                        height=80
                    )
                    
                    btn_u1, btn_u2 = st.columns([1, 1])
                    with btn_u1:
                        if st.button("Aşamayı ve Notu Güncelle", key=f"btn_save_{cand_id}", use_container_width=True):
                            st.session_state.db.update_candidate_status(cand_id, new_selected_stage, new_note_val)
                            st.toast(f"{candidate_name} güncellendi.")
                            st.rerun()
                    with btn_u2:
                        if st.button("Adayı Havuzdan Sil", key=f"btn_del_{cand_id}", use_container_width=True):
                            st.session_state.db.delete_candidate(cand_id)
                            st.toast(f"{candidate_name} silindi.")
                            st.rerun()

                with c_notes_col:
                    st.markdown("##### Adaya Özel Mülakat Soruları:")
                    p_questions = c.get("interview_questions", [])
                    if p_questions:
                        for p_idx, pq in enumerate(p_questions):
                            st.markdown(f"**{p_idx + 1}.** {pq}")
                    else:
                        st.caption("Kayıtlı mülakat sorusu bulunmuyor.")

                    st.markdown("##### Güçlü Yönler ve Olası Riskler:")
                    p_strengths = c.get("top_strengths", [])
                    for ps in p_strengths:
                        st.markdown(f"• {ps}")
                    p_risks = c.get("potential_risks", [])
                    for pr in p_risks:
                        st.markdown(f"• {pr}")

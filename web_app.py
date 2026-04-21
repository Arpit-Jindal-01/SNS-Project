import io
import os
from typing import Dict, List, Tuple
import time

import librosa
import numpy as np
import plotly.graph_objects as go
import soundfile as sf
import streamlit as st
from scipy.signal import butter, filtfilt
import requests
from urllib.parse import quote_plus

try:
    from groq import Groq  # type: ignore[reportMissingImports]
except ImportError:
    Groq = None

try:
    from openai import OpenAI  # type: ignore[reportMissingImports]
except ImportError:
    OpenAI = None


GEMINI_API_KEY_DEFAULT = "AIzaSyAhTUGBm25gTDy4GsjrEFCAlm7JgA-3Qvc"


def get_gemini_api_key() -> str:
    return os.getenv("GEMINI_API_KEY", "").strip() or GEMINI_API_KEY_DEFAULT


st.set_page_config(
    page_title="SNS Studio",
    page_icon="SNS",
    layout="wide",
    initial_sidebar_state="expanded",
)

VOICE_PRESETS = [
    "Chipmunk (+12)",
    "High (+6)",
    "Normal (0)",
    "Deep (-6)",
    "Bass (-12)",
    "Space Echo",
    "Cyborg",
    "Spooky",
    "Retro",
    "Cartoon",
]

REALTIME_EFFECTS = ["Passthrough", "Echo", "Robot", "Pitch Shift"]

EFFECT_INFO = {
    "Passthrough": {
        "formula": "y[n] = g * x[n]",
        "details": "Baseline identity path with gain control for A/B comparisons.",
        "system": "Linear, time-invariant, memoryless, and causal.",
        "spectrum": "The magnitude spectrum is scaled by g, while phase stays unchanged.",
        "sound": "The waveform shape stays the same, but loudness changes.",
    },
    "Echo": {
        "formula": "y[n] = x[n] + alpha x[n-d]",
        "details": "Adds delayed feedback signal to create room/space impression.",
        "system": "Linear, time-invariant, causal, and has memory because of the delay.",
        "spectrum": "The delayed copy creates constructive and destructive interference in frequency.",
        "sound": "The sound feels spacious because a second copy arrives after a short delay.",
    },
    "Robot": {
        "formula": "y[n] = tanh(beta * (x[n] * sin(2*pi*f*n/Fs)))",
        "details": "Ring modulation and saturation for metallic robotic tone.",
        "system": "Nonlinear and effectively time-varying, so it is not a simple LTI block.",
        "spectrum": "New frequency components and sidebands appear because the waveform is multiplied by a carrier.",
        "sound": "The voice sounds synthetic because harmonics are introduced and reshaped.",
    },
    "Pitch Shift": {
        "formula": "f_out = f_in * 2^(k/12)",
        "details": "Phase-vocoder pitch transposition with tempo preservation.",
        "system": "Time-frequency processing is used, so it behaves like a nonstationary transform.",
        "spectrum": "Prominent spectral peaks move up or down by the semitone factor.",
        "sound": "Pitch changes while speech content stays understandable.",
    },
}

EDU_STAGES = {
    "Input": "Raw recorded waveform from microphone or uploaded file.",
    "Noise Gate": "Low-level background components are suppressed below threshold.",
    "Effect": "A selected system transforms the waveform using DSP rules.",
    "Normalization": "Output peak is scaled to a safe range before playback/export.",
}


def inject_styles() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

        :root {
            --bg-main: #f8fafc;
            --bg-card: #ffffff;
            --text-main: #1a1a1a;
            --text-muted: #5f6470;
            --accent: #3f5efb;
            --accent-2: #00a0ff;
            --border: #e8ebf2;
            --shadow: 0 12px 28px rgba(8, 18, 38, 0.06);
        }

        html, body, .stApp {
            font-family: 'Inter', sans-serif;
            background:
                radial-gradient(circle at 10% 10%, rgba(63,94,251,0.06), transparent 28%),
                radial-gradient(circle at 90% 80%, rgba(0,160,255,0.07), transparent 32%),
                var(--bg-main);
            color: var(--text-main);
        }

        .stApp,
        .stApp p,
        .stApp label,
        .stApp li,
        .stApp div,
        .stApp span,
        .stApp [data-testid="stMarkdownContainer"] {
            color: #162136;
        }

        .stTextInput input,
        .stTextArea textarea,
        .stNumberInput input,
        .stSelectbox [data-baseweb="select"] > div,
        .stMultiSelect [data-baseweb="select"] > div {
            background: #ffffff !important;
            color: #162136 !important;
            border-color: #d7dfed !important;
        }

        .stSidebar,
        .stSidebar p,
        .stSidebar label,
        .stSidebar .stMarkdown {
            color: #162136 !important;
        }

        .stChatMessage {
            border: 1px solid #e4eaf7;
            border-radius: 10px;
            background: #ffffff;
            padding: 0.35rem;
        }

        .hero {
            border: 1px solid var(--border);
            border-radius: 16px;
            background: var(--bg-card);
            padding: 24px;
            box-shadow: var(--shadow);
            margin-bottom: 20px;
            animation: rise 260ms ease-out;
        }

        .main-title {
            font-size: clamp(2rem, 4vw, 2.8rem);
            font-weight: 700;
            margin: 0;
            letter-spacing: -0.02em;
        }

        .subtitle {
            color: var(--text-muted);
            margin-top: 8px;
            max-width: 800px;
        }

        .stat-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 12px;
            margin-top: 16px;
        }

        .stat-card {
            border: 1px solid var(--border);
            border-radius: 10px;
            background: #fcfdff;
            padding: 12px;
            transition: transform 220ms ease, box-shadow 220ms ease;
        }

        .stat-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 18px rgba(0, 0, 0, 0.06);
        }

        .stat-title {
            color: var(--text-muted);
            font-size: 12px;
        }

        .stat-value {
            margin-top: 4px;
            font-weight: 600;
        }

        .panel {
            border: 1px solid var(--border);
            border-radius: 12px;
            background: var(--bg-card);
            padding: 22px 22px 18px 22px;
            box-shadow: var(--shadow);
            animation: rise 260ms ease-out;
        }

        .panel h1, .panel h2, .panel h3, .panel h4 {
            margin-top: 0.7rem !important;
            margin-bottom: 0.45rem !important;
            color: #10243d !important;
            line-height: 1.25 !important;
        }

        .panel p, .panel li {
            line-height: 1.62 !important;
            margin-bottom: 0.5rem !important;
            color: #1b2e4a !important;
        }

        .panel ul, .panel ol {
            margin-top: 0.2rem !important;
            margin-bottom: 0.65rem !important;
            padding-left: 1.2rem !important;
        }

        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
            border-bottom: none;
        }

        .stTabs [data-baseweb="tab"] {
            border: 1px solid var(--border);
            border-radius: 8px;
            height: 38px;
            padding: 0 14px;
            background: #ffffff;
            font-weight: 600;
            color: #17304d !important;
        }

        .stTabs [aria-selected="true"] {
            border-color: #8ea6ff;
            color: #102f8f !important;
            background: #eef3ff !important;
            box-shadow: inset 0 0 0 1px #c6d4ff;
        }

        .stButton > button {
            background: #1f4fd6 !important;
            color: #ffffff !important;
            border: 1px solid #1a46c0 !important;
        }

        .stButton > button:hover {
            background: #183fb0 !important;
            color: #ffffff !important;
        }

        .stDownloadButton > button {
            background: linear-gradient(135deg, #1849d6 0%, #143ba8 100%) !important;
            color: #ffffff !important;
            border: 1px solid #5c7fe8 !important;
            border-radius: 14px !important;
            font-weight: 700 !important;
            padding: 0.55rem 1rem !important;
            box-shadow: 0 8px 18px rgba(14, 52, 158, 0.35) !important;
        }

        .stDownloadButton > button:hover {
            background: linear-gradient(135deg, #1238a8 0%, #102f8c 100%) !important;
            color: #ffffff !important;
            border-color: #86a3f5 !important;
        }

        .stDownloadButton > button p,
        .stDownloadButton > button span,
        .stDownloadButton > button div {
            color: #ffffff !important;
        }

        .stCaption, [data-testid="stCaptionContainer"] {
            color: #334e6f !important;
        }

        div[data-testid="stAlert"], div[data-testid="stAlert"] * {
            color: #12263f !important;
        }

        div[data-testid="stAlert"] {
            background: #eef4ff !important;
            border: 1px solid #cbd9ff !important;
        }

        input::placeholder, textarea::placeholder {
            color: #6a7f9a !important;
            opacity: 1 !important;
        }

        .small-note {
            font-size: 12px;
            color: var(--text-muted);
        }

        @keyframes rise {
            from { opacity: 0; transform: translateY(8px); }
            to { opacity: 1; transform: translateY(0); }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_header() -> None:
    st.markdown(
        """
        <section class="hero">
            <p style="margin:0; font-size:12px; color:#5f6470; font-weight:600;">Real-Time Audio Signal Processing Suite</p>
            <h1 class="main-title">SNS Studio</h1>
            <p class="subtitle">
                Real-time voice effect lab, upload voice transformation engine, and Signals and Systems AI tutor
                powered by Groq-compatible LLM APIs.
            </p>
            <div class="stat-grid">
                <div class="stat-card"><div class="stat-title">Real-Time Effects</div><div class="stat-value">4 Live Modes + Controls</div></div>
                <div class="stat-card"><div class="stat-title">Upload Presets</div><div class="stat-value">10 Voice Transform Presets</div></div>
                <div class="stat-card"><div class="stat-title">Signal Tutor</div><div class="stat-value">Groq API + Fallback</div></div>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def ensure_state() -> None:
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "last_reply" not in st.session_state:
        st.session_state.last_reply = ""
    if "realtime_raw_bytes" not in st.session_state:
        st.session_state.realtime_raw_bytes = None
    if "upload_raw_bytes" not in st.session_state:
        st.session_state.upload_raw_bytes = None
    if "last_provider_used" not in st.session_state:
        st.session_state.last_provider_used = "-"
    if "realtime_prev_params" not in st.session_state:
        st.session_state.realtime_prev_params = None


def _domain_guard() -> str:
    return (
        "You are an expert Signals and Systems tutor with strong pedagogy and accuracy. "
        "Answer only topics related to signal processing and systems: LTI systems, convolution, Fourier series, "
        "Fourier transform, Laplace transform, Z-transform, causality, stability, sampling theorem, filters, modulation. "
        "If a question is outside this scope, politely refuse and request a Signals and Systems question. "
        "For technical answers, use this structure: (1) Direct answer (2) Key equations (3) Step-by-step reasoning "
        "(4) Final takeaway. If assumptions are needed, state them."
    )


def educational_intro(effect: str) -> str:
    data = EFFECT_INFO.get(effect, EFFECT_INFO["Passthrough"])
    return (
        f"**What happens to the wave?**\n\n"
        f"- **Input waveform**: the raw signal is x[n] for discrete time or x(t) for continuous time.\n"
        f"- **System processing**: the selected block transforms x into y using {data['formula']}.\n"
        f"- **System properties**: {data['system']}\n"
        f"- **Spectrum view**: {data['spectrum']}\n"
        f"- **Why it sounds different**: {data['sound']}\n"
        f"- **Normalization**: y[n] is scaled so the peak stays below clipping, which prevents distortion."
    )


def effect_theory_card(effect: str) -> str:
    data = EFFECT_INFO.get(effect, EFFECT_INFO["Passthrough"])
    return (
        f"### Effect Info: {effect}\n\n"
        f"**Formula**: `{data['formula']}`\n\n"
        f"**Signal model**\n"
        f"- Input: x[n] or x(t)\n"
        f"- System: selected effect block\n"
        f"- Output: y[n] or y(t)\n\n"
        f"**Visual changes**\n"
        f"- Amplitude may change with gain, delay mixing, normalization, or modulation\n"
        f"- Time shape may stretch, shift, or gain extra oscillations\n"
        f"- Spectrum may remain similar, shift, widen, or create new harmonics\n\n"
        f"**System notes**\n"
        f"- {data['system']}\n"
        f"- {data['details']}"
    )


def preset_story(preset: str) -> str:
    if preset == "Chipmunk (+12)":
        return "This preset shifts the spectrum upward by 12 semitones, so harmonics move higher and the voice sounds smaller and brighter."
    if preset == "High (+6)":
        return "This preset raises pitch by 6 semitones, increasing fundamental frequency while preserving the spoken content."
    if preset == "Normal (0)":
        return "This preset keeps pitch unchanged, useful as a control signal for comparing against other transforms."
    if preset == "Deep (-6)":
        return "This preset lowers pitch by 6 semitones and filters high frequencies, creating a darker, deeper voice character."
    if preset == "Bass (-12)":
        return "This preset lowers pitch by 12 semitones for a strong bass-like effect with reduced high-frequency detail."
    if preset == "Space Echo":
        return "This preset adds a delayed copy of the waveform, which creates reflections and the perception of space."
    if preset == "Cyborg":
        return "This preset combines pitch reduction and ring modulation, creating metallic sidebands and a synthetic texture."
    if preset == "Spooky":
        return "This preset lowers pitch and adds echo, which makes the waveform more spacious and eerie."
    if preset == "Retro":
        return "This preset band-limits and bit-crushes the signal, resembling older communication systems with reduced fidelity."
    if preset == "Cartoon":
        return "This preset raises pitch and adds subtle modulation, making the waveform more playful and exaggerated."
    return "This preset changes the waveform using a preset-specific signal-processing chain."


def local_fallback_answer(question: str) -> str:
    q = question.lower()
    if "convolution" in q:
        return "For LTI systems, y[n] = sum_k x[k]h[n-k] and y(t) = integral x(tau)h(t-tau)dtau."
    if "fourier" in q:
        return "Fourier transform: X(jw) = integral x(t)e^(-jwt)dt, used to inspect spectral content."
    if "laplace" in q:
        return "Laplace transform: X(s) = integral x(t)e^(-st)dt. ROC determines causality and stability."
    if "z" in q and "transform" in q:
        return "Z-transform: X(z)=sum x[n]z^(-n). ROC is essential for uniqueness and system properties."
    return "Ask me any Signals and Systems question, and I will solve it step-by-step with formulas."


def web_search_fallback(question: str) -> str:
    """Use public web endpoints (no API key) to fetch context and summarize.

    This is a best-effort fallback when Gemini/OpenAI/Groq are unavailable.
    """
    snippets: List[str] = []
    headers = {"User-Agent": "SNS-Studio/1.0 (Signals-and-Systems-Education-App)"}

    # 1) DuckDuckGo Instant Answer API (no key required)
    try:
        ddg_url = (
            "https://api.duckduckgo.com/?q="
            f"{quote_plus(question + ' signals and systems')}&format=json&no_html=1&skip_disambig=1"
        )
        ddg_resp = requests.get(ddg_url, timeout=12, headers=headers)
        ddg_resp.raise_for_status()
        ddg = ddg_resp.json()

        abstract = (ddg.get("AbstractText") or "").strip()
        heading = (ddg.get("Heading") or "").strip()
        related = ddg.get("RelatedTopics", []) or []

        if heading or abstract:
            snippets.append(f"DuckDuckGo: {heading} - {abstract}".strip(" -"))

        for item in related[:3]:
            if isinstance(item, dict):
                text = (item.get("Text") or "").strip()
                if text:
                    snippets.append(f"Related: {text}")
    except Exception:
        pass

    # 2) Wikipedia summary API (no key required)
    try:
        wiki_search = requests.get(
            "https://en.wikipedia.org/w/api.php",
            params={
                "action": "query",
                "list": "search",
                "srsearch": f"{question} signal processing",
                "srlimit": 3,
                "format": "json",
            },
            timeout=12,
            headers=headers,
        )
        wiki_search.raise_for_status()
        result = wiki_search.json()
        search_items = result.get("query", {}).get("search", []) if isinstance(result, dict) else []
        titles = [item.get("title", "") for item in search_items if item.get("title")]

        for title in titles[:2]:
            summary_url = "https://en.wikipedia.org/api/rest_v1/page/summary/" + quote_plus(title)
            s_resp = requests.get(summary_url, timeout=12, headers=headers)
            if s_resp.status_code == 200:
                s_json = s_resp.json()
                extract = (s_json.get("extract") or "").strip()
                if extract:
                    snippets.append(f"Wikipedia ({title}): {extract}")
    except Exception:
        pass

    if not snippets:
        return local_fallback_answer(question)

    # Build concise synthesis from collected snippets
    bullet_points = "\n".join(f"- {s[:320]}" for s in snippets[:5])
    return f"Web-sourced notes:\n{bullet_points}\n\n{local_fallback_answer(question)}"


def gemini_chat(question: str, history: List[Dict[str, str]], model_name: str) -> str:
    api_key = get_gemini_api_key()
    if not api_key:
        return local_fallback_answer(question)

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"

    contents = []
    for item in history[-12:]:
        role = "model" if item["role"] == "assistant" else "user"
        contents.append({"role": role, "parts": [{"text": item["content"]}]})

    contents.append({"role": "user", "parts": [{"text": question}]})

    payload = {
        "system_instruction": {"parts": [{"text": _domain_guard()}]},
        "contents": contents,
        "generationConfig": {
            "temperature": 0.2,
            "topP": 0.9,
            "maxOutputTokens": 1400,
        },
    }

    last_error = None
    for attempt in range(3):
        try:
            response = requests.post(url, json=payload, timeout=60)
            # Retry on rate limits.
            if response.status_code == 429:
                last_error = requests.HTTPError(f"429 Too Many Requests (attempt {attempt + 1}/3)")
                time.sleep(1.5 * (attempt + 1))
                continue

            response.raise_for_status()
            data = response.json()
            candidates = data.get("candidates", [])
            if not candidates:
                return local_fallback_answer(question)
            parts = candidates[0].get("content", {}).get("parts", [])
            text = "".join(part.get("text", "") for part in parts)
            return text.strip() or local_fallback_answer(question)
        except Exception as exc:
            last_error = exc
            # Retry transient failures for first 2 attempts.
            if attempt < 2:
                time.sleep(1.5 * (attempt + 1))
                continue

    raise RuntimeError(f"Gemini request failed after retries: {last_error}")


def ask_ai_tutor(question: str, history: List[Dict[str, str]], provider: str, model_name: str) -> str:
    messages = [{"role": "system", "content": _domain_guard()}]
    for item in history[-12:]:
        messages.append({"role": item["role"], "content": item["content"]})
    messages.append({"role": "user", "content": question})

    if provider == "OpenAI":
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key or OpenAI is None:
            return local_fallback_answer(question)

        try:
            client = OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model=model_name,
                messages=messages,
                temperature=0.2,
                max_tokens=1000,
            )
            st.session_state.last_provider_used = f"OpenAI ({model_name})"
            return response.choices[0].message.content or "No response from model."
        except Exception as exc:
            # Try Gemini fallback first.
            try:
                gemini_model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
                result = gemini_chat(question, history, gemini_model)
                st.session_state.last_provider_used = f"Gemini fallback ({gemini_model})"
                return result
            except Exception:
                pass

            # Try Groq fallback second.
            groq_key = os.getenv("GROQ_API_KEY", "").strip()
            if groq_key and Groq is not None:
                try:
                    groq_model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
                    client = Groq(api_key=groq_key)
                    response = client.chat.completions.create(
                        model=groq_model,
                        messages=messages,
                        temperature=0.2,
                        max_tokens=1000,
                    )
                    st.session_state.last_provider_used = f"Groq fallback ({groq_model})"
                    return response.choices[0].message.content or "No response from model."
                except Exception:
                    pass

            st.session_state.last_provider_used = "Web fallback"
            return web_search_fallback(question)

    if provider == "Gemini":
        try:
            result = gemini_chat(question, history, model_name)
            st.session_state.last_provider_used = f"Gemini ({model_name})"
            return result
        except Exception as exc:
            # Smart failover path when Gemini is rate-limited or unavailable.
            openai_key = os.getenv("OPENAI_API_KEY", "").strip()
            groq_key = os.getenv("GROQ_API_KEY", "").strip()

            if openai_key and OpenAI is not None:
                result = ask_ai_tutor(question, history, "OpenAI", os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
                st.session_state.last_provider_used = f"OpenAI fallback ({os.getenv('OPENAI_MODEL', 'gpt-4o-mini')})"
                return result
            if groq_key and Groq is not None:
                result = ask_ai_tutor(question, history, "Groq", os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"))
                st.session_state.last_provider_used = f"Groq fallback ({os.getenv('GROQ_MODEL', 'llama-3.3-70b-versatile')})"
                return result

            st.session_state.last_provider_used = "Web fallback"
            return web_search_fallback(question)

    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key or Groq is None:
        return local_fallback_answer(question)

    try:
        client = Groq(api_key=api_key)
        response = client.chat.completions.create(
            model=model_name,
            messages=messages,
            temperature=0.2,
            max_tokens=1000,
        )
        st.session_state.last_provider_used = f"Groq ({model_name})"
        return response.choices[0].message.content or "No response from model."
    except Exception as exc:
        # Try Gemini fallback first.
        try:
            gemini_model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
            result = gemini_chat(question, history, gemini_model)
            st.session_state.last_provider_used = f"Gemini fallback ({gemini_model})"
            return result
        except Exception:
            pass

        # Try OpenAI fallback second.
        openai_key = os.getenv("OPENAI_API_KEY", "").strip()
        if openai_key and OpenAI is not None:
            try:
                openai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
                client = OpenAI(api_key=openai_key)
                response = client.chat.completions.create(
                    model=openai_model,
                    messages=messages,
                    temperature=0.2,
                    max_tokens=1000,
                )
                st.session_state.last_provider_used = f"OpenAI fallback ({openai_model})"
                return response.choices[0].message.content or "No response from model."
            except Exception:
                pass

        st.session_state.last_provider_used = "Web fallback"
        return web_search_fallback(question)


def normalize_signal(y: np.ndarray) -> np.ndarray:
    peak = float(np.max(np.abs(y))) if len(y) else 1.0
    if peak < 1e-8:
        return y.astype(np.float32)
    return (0.95 * y / peak).astype(np.float32)


def describe_signal(signal: np.ndarray, sr: int) -> str:
    if len(signal) == 0:
        return "Empty signal"

    peak = float(np.max(np.abs(signal)))
    rms = float(np.sqrt(np.mean(np.square(signal))))
    duration = len(signal) / float(sr)
    zero_crossings = int(np.sum(np.diff(np.signbit(signal)) != 0))
    return (
        f"Duration: {duration:.2f}s | Peak: {peak:.3f} | RMS: {rms:.3f} | "
        f"Zero crossings: {zero_crossings}"
    )


def apply_noise_gate(y: np.ndarray, threshold: float) -> np.ndarray:
    out = y.copy().astype(np.float32)
    out[np.abs(out) < threshold] = 0.0
    return out


def lowpass_filter(y: np.ndarray, sr: int, cutoff_hz: float) -> np.ndarray:
    cutoff = min(sr * 0.5 - 100.0, cutoff_hz) / (sr * 0.5)
    if not (0 < cutoff < 1):
        return y.astype(np.float32)
    b, a = butter(4, cutoff, btype="low")
    return filtfilt(b, a, y).astype(np.float32)


def bandpass_filter(y: np.ndarray, sr: int, low_hz: float, high_hz: float) -> np.ndarray:
    low = max(20.0, low_hz) / (sr * 0.5)
    high = min(sr * 0.5 - 100.0, high_hz) / (sr * 0.5)
    if not (0 < low < high < 1):
        return y.astype(np.float32)
    b, a = butter(4, [low, high], btype="band")
    return filtfilt(b, a, y).astype(np.float32)


def add_echo(y: np.ndarray, sr: int, delay_sec: float, mix: float) -> np.ndarray:
    out = y.copy().astype(np.float32)
    delay_samples = max(1, int(delay_sec * sr))
    if delay_samples < len(out):
        out[delay_samples:] += mix * y[:-delay_samples]
    return out


def ring_modulate(y: np.ndarray, sr: int, freq_hz: float) -> np.ndarray:
    t = np.arange(len(y), dtype=np.float32) / float(sr)
    carrier = np.sin(2 * np.pi * freq_hz * t).astype(np.float32)
    return (y * carrier).astype(np.float32)


def bit_crush(y: np.ndarray, bits: int = 6) -> np.ndarray:
    levels = float(2 ** bits)
    return np.round(y * levels) / levels


def apply_realtime_effect(
    y: np.ndarray,
    sr: int,
    effect: str,
    volume: float,
    noise_gate_enabled: bool,
    gate_threshold: float,
    pitch_steps: int,
    echo_mix: float,
    echo_delay: float,
) -> np.ndarray:
    out = y.astype(np.float32)

    if noise_gate_enabled:
        out = apply_noise_gate(out, gate_threshold)

    if effect == "Echo":
        out = add_echo(out, sr, delay_sec=echo_delay, mix=echo_mix)
    elif effect == "Robot":
        out = ring_modulate(out, sr, 35.0)
        out = np.tanh(2.2 * out)
    elif effect == "Pitch Shift":
        out = librosa.effects.pitch_shift(out, sr=sr, n_steps=pitch_steps)

    out = volume * out
    return normalize_signal(out)


def convert_uploaded_voice(y: np.ndarray, sr: int, preset: str) -> np.ndarray:
    out = y.astype(np.float32)

    if preset == "Chipmunk (+12)":
        out = librosa.effects.pitch_shift(out, sr=sr, n_steps=12)
    elif preset == "High (+6)":
        out = librosa.effects.pitch_shift(out, sr=sr, n_steps=6)
    elif preset == "Normal (0)":
        out = out
    elif preset == "Deep (-6)":
        out = librosa.effects.pitch_shift(out, sr=sr, n_steps=-6)
        out = lowpass_filter(out, sr, 4200)
    elif preset == "Bass (-12)":
        out = librosa.effects.pitch_shift(out, sr=sr, n_steps=-12)
        out = lowpass_filter(out, sr, 2800)
    elif preset == "Space Echo":
        out = add_echo(out, sr, delay_sec=0.28, mix=0.55)
    elif preset == "Cyborg":
        out = ring_modulate(out, sr, 45.0)
        out = librosa.effects.pitch_shift(out, sr=sr, n_steps=-2)
        out = np.tanh(2.6 * out)
    elif preset == "Spooky":
        out = librosa.effects.pitch_shift(out, sr=sr, n_steps=-4)
        out = add_echo(out, sr, delay_sec=0.35, mix=0.4)
    elif preset == "Retro":
        out = bandpass_filter(out, sr, 250, 3100)
        out = bit_crush(out, bits=5)
    elif preset == "Cartoon":
        out = librosa.effects.pitch_shift(out, sr=sr, n_steps=8)
        out = ring_modulate(out, sr, 6.0)

    return normalize_signal(out)


def to_wav_bytes(y: np.ndarray, sr: int) -> bytes:
    buffer = io.BytesIO()
    sf.write(buffer, y, sr, format="WAV")
    buffer.seek(0)
    return buffer.read()


def signal_stats(y: np.ndarray) -> Dict[str, float]:
    return {
        "peak": float(np.max(np.abs(y))) if len(y) else 0.0,
        "rms": float(np.sqrt(np.mean(np.square(y)))) if len(y) else 0.0,
        "mean": float(np.mean(y)) if len(y) else 0.0,
    }


def waveform_compare_fig(original: np.ndarray, processed: np.ndarray, sr: int) -> go.Figure:
    n = min(len(original), len(processed), 5000)
    if n <= 1:
        return go.Figure()

    t = np.arange(n) / float(sr)
    o = original[:n]
    p = processed[:n]
    d = p - o

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=t, y=o, name="Original", mode="lines", line=dict(color="#007f5f", width=2.0)))
    fig.add_trace(go.Scatter(x=t, y=p, name="Processed", mode="lines", line=dict(color="#335cdb", width=2.0)))
    fig.add_trace(go.Scatter(x=t, y=d, name="Difference", mode="lines", line=dict(color="#d94841", width=1.6, dash="dot")))
    fig.update_layout(
        height=320,
        margin=dict(l=18, r=18, t=40, b=20),
        template="plotly_dark",
        title="Wave Comparison Panel",
        xaxis_title="Time (s)",
        yaxis_title="Amplitude",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        plot_bgcolor="#0b1220",
        paper_bgcolor="#0b1220",
        font=dict(color="#e7eefc"),
    )
    fig.update_xaxes(showgrid=True, gridcolor="#25324a")
    fig.update_yaxes(showgrid=True, gridcolor="#25324a", zeroline=True, zerolinecolor="#4b6286")
    return fig


def waveform_stage_fig(stages: Dict[str, np.ndarray], sr: int, normalize_display: bool) -> go.Figure:
    names = [name for name in ["Input", "Noise Gate", "Effect", "Normalization"] if name in stages]
    if not names:
        return go.Figure()

    fig = make_wave_grid(stages, sr, names, normalize_display)
    return fig


def make_wave_grid(stages: Dict[str, np.ndarray], sr: int, names: List[str], normalize_display: bool) -> go.Figure:
    from plotly.subplots import make_subplots

    rows = len(names)
    fig = make_subplots(rows=rows, cols=1, shared_xaxes=True, vertical_spacing=0.08, subplot_titles=names)

    colors = {
        "Input": "#138a5f",
        "Noise Gate": "#c77700",
        "Effect": "#2f49cf",
        "Normalization": "#096f67",
    }

    for idx, name in enumerate(names, start=1):
        wave = stages[name]
        # Show a longer window so delayed effects (e.g., echo at 0.2s) are visible.
        n = min(len(wave), 12000)
        if n <= 1:
            continue
        t = np.arange(n) / float(sr)

        segment = wave[:n].astype(np.float32)
        local_peak = float(np.max(np.abs(segment))) if n else 0.0
        if normalize_display and local_peak > 1e-9:
            display_wave = segment / local_peak
        else:
            display_wave = segment

        fig.add_trace(
            go.Scatter(
                x=t,
                y=display_wave,
                mode="lines",
                name=name,
                line=dict(color=colors.get(name, "#3f5efb"), width=2.0),
                showlegend=False,
            ),
            row=idx,
            col=1,
        )

    fig.update_layout(
        height=max(320, 180 * rows),
        margin=dict(l=18, r=18, t=42, b=20),
        template="plotly_dark",
        title="Wave Transformation Journey",
        plot_bgcolor="#0b1220",
        paper_bgcolor="#0b1220",
        font=dict(color="#e7eefc"),
    )

    # Keep subplot titles readable and away from axis labels.
    for ann in fig.layout.annotations:
        ann.font = dict(size=12, color="#dfe9ff")
        ann.yshift = 8

    y_label = "Normalized Amplitude" if normalize_display else "Amplitude"
    for row_idx in range(1, rows + 1):
        fig.update_yaxes(
            title_text=y_label,
            row=row_idx,
            col=1,
            showgrid=True,
            gridcolor="#25324a",
            zeroline=True,
            zerolinecolor="#4b6286",
        )
        fig.update_xaxes(
            title_text="Time (s)" if row_idx == rows else "",
            row=row_idx,
            col=1,
            showticklabels=(row_idx == rows),
            showgrid=True,
            gridcolor="#25324a",
        )
    return fig


def waveform_3d_fig(processed: np.ndarray, sr: int) -> go.Figure:
    n = min(len(processed), 8192)
    if n <= 256:
        return go.Figure()

    y = processed[:n]
    n_fft = 512
    hop = 96
    spec = np.abs(librosa.stft(y, n_fft=n_fft, hop_length=hop, center=False))
    spec_db = librosa.amplitude_to_db(spec + 1e-7, ref=np.max)

    max_bins = min(120, spec_db.shape[0])
    z = spec_db[:max_bins, :]
    freqs = librosa.fft_frequencies(sr=sr, n_fft=n_fft)[:max_bins]
    times = librosa.frames_to_time(np.arange(z.shape[1]), sr=sr, hop_length=hop)

    fig = go.Figure(
        data=[
            go.Surface(
                x=times,
                y=freqs,
                z=z,
                colorscale="Magma",
                cmin=-80,
                cmax=0,
                showscale=True,
                colorbar=dict(title="dB"),
                contours={"z": {"show": True, "usecolormap": True, "highlightcolor": "#ffffff", "project_z": True}},
            )
        ]
    )
    fig.update_layout(
        height=450,
        margin=dict(l=8, r=8, t=36, b=10),
        title="3D Spectral Wave Surface",
        template="plotly_dark",
        paper_bgcolor="#0b1220",
        font=dict(color="#e7eefc"),
        scene=dict(
            xaxis_title="Time (s)",
            yaxis_title="Frequency (Hz)",
            zaxis_title="Magnitude (dB)",
            camera=dict(eye=dict(x=1.65, y=1.25, z=1.05)),
            xaxis=dict(backgroundcolor="#0b1220", gridcolor="#25324a", zerolinecolor="#4b6286"),
            yaxis=dict(backgroundcolor="#0b1220", gridcolor="#25324a", zerolinecolor="#4b6286"),
            zaxis=dict(backgroundcolor="#0b1220", gridcolor="#25324a", zerolinecolor="#4b6286"),
        ),
    )
    return fig


def analyze_signal(signal: np.ndarray, sr: int) -> Dict[str, float]:
    if len(signal) == 0:
        return {
            "peak": 0.0,
            "rms": 0.0,
            "energy": 0.0,
            "centroid": 0.0,
            "bandwidth": 0.0,
            "dominant": 0.0,
            "zcr": 0.0,
        }

    window = np.hanning(len(signal))
    spectrum = np.abs(np.fft.rfft(signal * window))
    freqs = np.fft.rfftfreq(len(signal), d=1.0 / sr)
    total = float(np.sum(spectrum) + 1e-9)
    centroid = float(np.sum(freqs * spectrum) / total)
    bandwidth = float(np.sqrt(np.sum(((freqs - centroid) ** 2) * spectrum) / total))
    dominant = float(freqs[int(np.argmax(spectrum))]) if len(freqs) else 0.0

    return {
        "peak": float(np.max(np.abs(signal))),
        "rms": float(np.sqrt(np.mean(np.square(signal)))),
        "energy": float(np.sum(np.square(signal))),
        "centroid": centroid,
        "bandwidth": bandwidth,
        "dominant": dominant,
        "zcr": float(np.sum(np.diff(np.signbit(signal)) != 0)),
    }


def realtime_graph_explanations(
    effect: str,
    analysis_in: Dict[str, float],
    analysis_out: Dict[str, float],
    s1: Dict[str, float],
    s2: Dict[str, float],
) -> str:
    delta_peak = s2["peak"] - s1["peak"]
    delta_rms = s2["rms"] - s1["rms"]
    delta_centroid = analysis_out["centroid"] - analysis_in["centroid"]
    delta_bw = analysis_out["bandwidth"] - analysis_in["bandwidth"]
    delta_dom = analysis_out["dominant"] - analysis_in["dominant"]
    in_rms = max(s1["rms"], 1e-9)
    in_peak = max(s1["peak"], 1e-9)
    rms_pct = (delta_rms / in_rms) * 100.0
    peak_pct = (delta_peak / in_peak) * 100.0

    return (
        "### Real-Time Graph Explanations\n\n"
        "1. **Signal Flow Diagram**\n"
        "This block diagram shows the exact DSP pipeline used for your current settings: input, optional noise gate, selected effect, then normalization.\n"
        "Significance: it tells you *where* in the chain each change is happening.\n\n"
        "2. **Wave Transformation Journey**\n"
        "These stacked waveforms show how the same signal evolves at each stage.\n"
        "Significance: you can visually verify if the effect alters shape, polarity, transient behavior, or silence regions.\n\n"
        "3. **Frequency-Domain View (Magnitude/Phase)**\n"
        "This compares the original and processed spectrum. Peaks are dominant frequency components; phase traces indicate timing alignment in frequency bins.\n"
        "Significance: helps confirm whether the effect shifts pitch, adds harmonics, or changes spectral balance.\n"
        f"Observed now: centroid change = {delta_centroid:+.1f} Hz, bandwidth change = {delta_bw:+.1f} Hz, dominant-frequency shift = {delta_dom:+.1f} Hz.\n\n"
        "4. **Temporal Dynamics (Recorded Data)**\n"
        "This panel is computed directly from your recorded signal and its processed output. It shows amplitude envelope and short-time energy over time.\n"
        "Significance: reveals how dynamics, transients, and loudness flow change due to the selected effect.\n\n"
        "5. **Wave Comparison Panel**\n"
        "Shows original, processed, and difference signal. The difference trace isolates what the effect added/removed.\n"
        "Significance: good for judging effect strength and avoiding over-processing artifacts.\n\n"
        "6. **3D Spectral Surface**\n"
        "Time-frequency-energy surface of the processed signal: x-axis time, y-axis frequency, z-axis magnitude (dB).\n"
        "Significance: reveals how spectral content evolves over time, which is hard to see in 2D waveform plots.\n\n"
        "### Real-Time Value Significance (Current Recording)\n"
        f"- **Signal Flow Diagram (current settings)**: effect = {effect}, so these values indicate where change is introduced before normalization.\n"
        f"- **Wave Transformation Journey (time-domain level change)**: peak changed by {delta_peak:+.4f} ({peak_pct:+.1f}%), RMS changed by {delta_rms:+.4f} ({rms_pct:+.1f}%).\n"
        f"- **Frequency-Domain View (spectral shift)**: dominant frequency moved by {delta_dom:+.1f} Hz; centroid moved by {delta_centroid:+.1f} Hz; bandwidth changed by {delta_bw:+.1f} Hz.\n"
        f"- **Temporal Dynamics (envelope/energy meaning)**: output RMS {s2['rms']:.4f} vs input RMS {s1['rms']:.4f}, so loudness-energy trend is {'higher' if s2['rms'] > s1['rms'] else 'lower or similar'}.\n"
        f"- **Wave Comparison Panel (difference strength)**: larger difference trace means stronger processing; with current values, |Δpeak|={abs(delta_peak):.4f} and |ΔRMS|={abs(delta_rms):.4f}.\n"
        f"- **3D Spectral Surface (time-varying timbre)**: processed centroid {analysis_out['centroid']:.1f} Hz and bandwidth {analysis_out['bandwidth']:.1f} Hz summarize current brightness and spread over time.\n\n"
        "### Why the Metrics Matter\n"
        f"- **Peak** ({s2['peak']:.3f}, change {delta_peak:+.3f}): indicates clipping risk and headroom.\n"
        f"- **RMS** ({s2['rms']:.3f}, change {delta_rms:+.3f}): indicates perceived loudness/energy level.\n"
        f"- **Spectral Centroid** ({analysis_out['centroid']:.1f} Hz): higher means brighter tone, lower means darker tone.\n"
        f"- **Bandwidth** ({analysis_out['bandwidth']:.1f} Hz): larger means broader frequency spread/timbre complexity.\n"
        f"- **Dominant Frequency** ({analysis_out['dominant']:.1f} Hz): strongest frequency component, often tied to pitch region.\n"
        f"- **Zero Crossings** ({analysis_out['zcr']:.0f}): higher values often indicate noisier or brighter/high-frequency content.\n\n"
        f"Current effect: **{effect}**. Use these graphs together (time + frequency + temporal dynamics) for complete Signals and Systems interpretation."
    )


def slider_change_explanations(
    effect: str,
    params: Dict[str, float],
    prev_params: Dict[str, float] | None,
    analysis_in: Dict[str, float],
    analysis_out: Dict[str, float],
) -> str:
    changed_lines: List[str] = []
    if prev_params:
        keys = ["volume", "gate_threshold", "pitch_steps", "echo_mix", "echo_delay", "noise_gate_enabled", "effect"]
        for key in keys:
            old_v = prev_params.get(key)
            new_v = params.get(key)
            if old_v != new_v:
                changed_lines.append(f"- `{key}` changed from `{old_v}` to `{new_v}`")

    if not changed_lines:
        changed_lines.append("- No slider/control change detected since last run. Current values are still interpreted below.")

    centroid_shift = analysis_out["centroid"] - analysis_in["centroid"]
    bw_shift = analysis_out["bandwidth"] - analysis_in["bandwidth"]
    rms_ratio = (analysis_out["rms"] / max(analysis_in["rms"], 1e-9))

    return (
        "### Slider Change Impact (Real-Time)\n\n"
        "**Detected changes**\n"
        f"{'\n'.join(changed_lines)}\n\n"
        "**What these changes typically do**\n"
        f"- `volume={params['volume']:.2f}`: scales amplitude level. Higher values raise output loudness and clipping risk.\n"
        f"- `noise_gate_enabled={params['noise_gate_enabled']}` with `gate_threshold={params['gate_threshold']:.3f}`: removes low-level content below threshold, reducing noise but potentially removing weak speech details.\n"
        f"- `echo_mix={params['echo_mix']:.2f}` and `echo_delay={params['echo_delay']:.2f}s`: stronger/later reflections increase spatial effect and smear transients.\n"
        f"- `pitch_steps={int(params['pitch_steps'])}`: shifts spectral peaks up/down, changing perceived pitch and brightness.\n"
        f"- `effect={params['effect']}`: switches DSP block, which changes system behavior itself.\n\n"
        "**Current measured significance on this recording**\n"
        f"- RMS ratio (output/input): `{rms_ratio:.2f}x`\n"
        f"- Spectral centroid shift: `{centroid_shift:+.1f} Hz`\n"
        f"- Bandwidth shift: `{bw_shift:+.1f} Hz`\n"
        f"- Dominant frequency now: `{analysis_out['dominant']:.1f} Hz`\n"
        f"- Zero crossings now: `{analysis_out['zcr']:.0f}`\n"
    )


def signal_flow_fig(effect: str, volume: float, gate_threshold: float, echo_delay: float, echo_mix: float, pitch_steps: int) -> go.Figure:
    fig = go.Figure()
    box_y = 0.5
    boxes = [
        (0.05, 0.68, 0.18, 0.28, "Input\n$x[n]$", "Raw waveform"),
        (0.28, 0.68, 0.18, 0.28, "Noise Gate\n$g_n$", f"Threshold {gate_threshold:.3f}"),
        (0.51, 0.68, 0.18, 0.28, f"Effect\n{effect}", _effect_brief(effect, echo_delay, echo_mix, pitch_steps)),
        (0.74, 0.68, 0.18, 0.28, "Normalize\n$y[n]$", f"Gain {volume:.2f}"),
    ]

    for x0, y0, w, h, title, subtitle in boxes:
        fig.add_shape(type="rect", x0=x0, y0=y0, x1=x0 + w, y1=y0 + h, line=dict(color="#cdd8ee", width=1.4), fillcolor="#fbfcff")
        fig.add_annotation(x=x0 + w / 2, y=y0 + h * 0.66, text=f"<b>{title}</b>", showarrow=False, font=dict(size=14, color="#17304d"))
        fig.add_annotation(x=x0 + w / 2, y=y0 + h * 0.28, text=subtitle, showarrow=False, font=dict(size=11, color="#4f647d"))

    for x in [0.23, 0.46, 0.69]:
        fig.add_annotation(x=x, y=0.82, text="→", showarrow=False, font=dict(size=28, color="#5871d6"))

    fig.update_xaxes(visible=False, range=[0, 1])
    fig.update_yaxes(visible=False, range=[0, 1])
    fig.update_layout(
        height=230,
        margin=dict(l=10, r=10, t=10, b=10),
        template="plotly_dark",
        plot_bgcolor="#0b1220",
        paper_bgcolor="#0b1220",
        font=dict(color="#e7eefc"),
        showlegend=False,
    )
    return fig


def _effect_brief(effect: str, echo_delay: float, echo_mix: float, pitch_steps: int) -> str:
    if effect == "Echo":
        return f"Delay {echo_delay:.2f}s, mix {echo_mix:.2f}"
    if effect == "Pitch Shift":
        return f"Shift {pitch_steps:+d} semitones"
    if effect == "Robot":
        return "Ring modulation + saturation"
    return "Identity + gain"


def preset_to_effect_kind(preset: str) -> str:
    if preset in {"Space Echo", "Echo"}:
        return "Echo"
    if preset in {"Cyborg", "Retro"}:
        return "Robot"
    if preset in {"Chipmunk (+12)", "High (+6)", "Normal (0)", "Deep (-6)", "Bass (-12)", "Cartoon"}:
        return "Pitch Shift"
    return "Passthrough"


def spectrum_compare_fig(original: np.ndarray, processed: np.ndarray, sr: int) -> go.Figure:
    n = min(len(original), len(processed))
    if n <= 2:
        return go.Figure()

    window = np.hanning(n)
    f = np.fft.rfftfreq(n, d=1.0 / sr)
    mag_o = 20 * np.log10(np.abs(np.fft.rfft(original[:n] * window)) + 1e-9)
    mag_p = 20 * np.log10(np.abs(np.fft.rfft(processed[:n] * window)) + 1e-9)
    phase_o = np.unwrap(np.angle(np.fft.rfft(original[:n] * window)))
    phase_p = np.unwrap(np.angle(np.fft.rfft(processed[:n] * window)))

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=f, y=mag_o, mode="lines", name="Original Magnitude", line=dict(color="#008a63", width=2.1)))
    fig.add_trace(go.Scatter(x=f, y=mag_p, mode="lines", name="Processed Magnitude", line=dict(color="#3550d8", width=2.1)))
    fig.add_trace(go.Scatter(x=f, y=phase_o, mode="lines", name="Original Phase", line=dict(color="#15a5c9", width=1.2, dash="dot"), visible="legendonly"))
    fig.add_trace(go.Scatter(x=f, y=phase_p, mode="lines", name="Processed Phase", line=dict(color="#c76a00", width=1.2, dash="dot"), visible="legendonly"))
    fig.update_layout(
        height=340,
        margin=dict(l=18, r=18, t=64, b=84),
        template="plotly_dark",
        title="Frequency-Domain View: X(f), H(f), and Y(f)",
        title_x=0.01,
        title_xanchor="left",
        title_y=0.98,
        xaxis_title="Frequency (Hz)",
        yaxis_title="Magnitude (dB) / Phase (rad)",
        legend=dict(orientation="h", yanchor="top", y=-0.18, xanchor="left", x=0, font=dict(size=12)),
        plot_bgcolor="#0b1220",
        paper_bgcolor="#0b1220",
        font=dict(color="#e7eefc"),
    )
    fig.update_xaxes(showgrid=True, gridcolor="#25324a")
    fig.update_yaxes(showgrid=True, gridcolor="#25324a", zeroline=True, zerolinecolor="#4b6286")
    return fig


def temporal_dynamics_fig(original: np.ndarray, processed: np.ndarray, sr: int, normalize_display: bool) -> go.Figure:
    from plotly.subplots import make_subplots

    n = min(len(original), len(processed), 6000)
    if n <= 16:
        return go.Figure()

    orig = original[:n].astype(np.float32)
    proc = processed[:n].astype(np.float32)

    # Real-data envelopes from recorded signal using moving-average smoothed absolute value.
    win = max(8, int(0.015 * sr))
    kernel = np.ones(win, dtype=np.float32) / float(win)
    env_o = np.convolve(np.abs(orig), kernel, mode="same")
    env_p = np.convolve(np.abs(proc), kernel, mode="same")

    # Real-data short-time energy trajectories.
    e_win = max(16, int(0.02 * sr))
    e_kernel = np.ones(e_win, dtype=np.float32) / float(e_win)
    en_o = np.convolve(orig * orig, e_kernel, mode="same")
    en_p = np.convolve(proc * proc, e_kernel, mode="same")

    t = np.arange(n) / float(sr)

    # Optional display normalization for readability (plot-only).
    if normalize_display:
        env_o = env_o / (np.max(env_o) + 1e-9)
        env_p = env_p / (np.max(env_p) + 1e-9)
        en_o = en_o / (np.max(en_o) + 1e-9)
        en_p = en_p / (np.max(en_p) + 1e-9)

    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=False,
        vertical_spacing=0.14,
        subplot_titles=(
            "Amplitude Envelope from Recorded Audio",
            "Short-Time Energy from Recorded Audio",
        ),
    )

    fig.add_trace(
        go.Scatter(
            x=t,
            y=env_o,
            mode="lines",
            name="Original Envelope",
            line=dict(color="#0b8a61", width=2.0),
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=t,
            y=env_p,
            mode="lines",
            name="Processed Envelope",
            line=dict(color="#3150d9", width=2.0),
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=t,
            y=en_o,
            mode="lines",
            name="Original Energy",
            line=dict(color="#c77700", width=1.8, dash="dot"),
        ),
        row=2,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=t,
            y=en_p,
            mode="lines",
            name="Processed Energy",
            line=dict(color="#d94841", width=1.8),
        ),
        row=2,
        col=1,
    )

    fig.update_layout(
        height=430,
        margin=dict(l=18, r=18, t=72, b=96),
        template="plotly_dark",
        title="Temporal Dynamics (Real Recorded Data)",
        title_x=0.01,
        title_xanchor="left",
        title_y=0.98,
        legend=dict(orientation="h", yanchor="top", y=-0.18, xanchor="left", x=0, font=dict(size=12)),
        plot_bgcolor="#0b1220",
        paper_bgcolor="#0b1220",
        font=dict(color="#e7eefc"),
    )

    # Push subplot headers down slightly so they do not collide with the main title.
    for ann in fig.layout.annotations:
        ann.font = dict(size=12, color="#dfe9ff")
        ann.yshift = -8

    fig.update_xaxes(title_text="", row=1, col=1, showticklabels=False, showgrid=True, gridcolor="#25324a")
    y_label = "Normalized Level" if normalize_display else "Level"
    fig.update_yaxes(title_text=y_label, row=1, col=1, showgrid=True, gridcolor="#25324a", zeroline=True, zerolinecolor="#4b6286")
    fig.update_xaxes(title_text="Time (s)", row=2, col=1, showgrid=True, gridcolor="#25324a")
    fig.update_yaxes(title_text=y_label, row=2, col=1, showgrid=True, gridcolor="#25324a", zeroline=True, zerolinecolor="#4b6286")
    return fig


def build_ai_summary(effect: str, signal_kind: str, original: np.ndarray, processed: np.ndarray, sr: int, params: Dict[str, float]) -> str:
    stats_in = analyze_signal(original, sr)
    stats_out = analyze_signal(processed, sr)
    data = EFFECT_INFO.get(effect, EFFECT_INFO["Passthrough"])
    return (
        f"Summarize this for a beginner using clear signals-and-systems language.\n\n"
        f"Signal kind: {signal_kind}\n"
        f"Effect: {effect}\n"
        f"Formula: {data['formula']}\n"
        f"System properties: {data['system']}\n"
        f"Input stats: peak={stats_in['peak']:.3f}, rms={stats_in['rms']:.3f}, centroid={stats_in['centroid']:.1f} Hz, dominant={stats_in['dominant']:.1f} Hz\n"
        f"Output stats: peak={stats_out['peak']:.3f}, rms={stats_out['rms']:.3f}, centroid={stats_out['centroid']:.1f} Hz, dominant={stats_out['dominant']:.1f} Hz\n"
        f"Parameters: {params}\n"
        f"Explain how x[n] becomes y[n], what changed in time domain, what changed in frequency domain, and why the sound changed.\n"
        f"Keep the answer structured with headings and short bullet points."
    )


def summarize_with_provider(prompt: str, history: List[Dict[str, str]], provider: str, model_name: str) -> str:
    if provider == "Gemini":
        return gemini_chat(prompt, history, model_name)
    if provider == "OpenAI":
        return ask_ai_tutor(prompt, history, provider, model_name)
    return ask_ai_tutor(prompt, history, provider, model_name)


def decode_audio(raw_bytes: bytes, sr: int = 22050) -> Tuple[np.ndarray, int]:
    y, out_sr = librosa.load(io.BytesIO(raw_bytes), sr=sr, mono=True)
    return y.astype(np.float32), out_sr


def render_sidebar() -> None:
    st.sidebar.header("Settings")
    provider = st.sidebar.selectbox("Chat Provider", ["Gemini", "OpenAI", "Groq"], index=0)
    st.session_state.chat_provider = provider

    if provider == "Gemini":
        model_default = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
        st.session_state.chat_model = st.sidebar.text_input("Gemini Model", value=model_default)
        st.sidebar.caption("Set GEMINI_API_KEY. Recommended: gemini-2.0-flash.")
    elif provider == "OpenAI":
        model_default = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        st.session_state.chat_model = st.sidebar.text_input("OpenAI Model", value=model_default)
        st.sidebar.caption("Set OPENAI_API_KEY. For best quality, use GPT-4 class model.")
    else:
        model_default = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
        st.session_state.chat_model = st.sidebar.text_input("Groq Model", value=model_default)
        st.sidebar.caption("Set GROQ_API_KEY. For best quality, use llama-3.3-70b-versatile.")

    st.sidebar.divider()
    st.sidebar.markdown("### Upload Voice Presets")
    for idx, preset in enumerate(VOICE_PRESETS, start=1):
        st.sidebar.write(f"{idx}. {preset}")


def realtime_tab() -> None:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.subheader("Real-Time Lab")
    st.caption("Record from microphone, process with live DSP settings, compare original and transformed waveforms.")

    c1, c2, c3 = st.columns(3)
    with c1:
        effect = st.selectbox("Effect", REALTIME_EFFECTS, index=1)
        volume = st.slider("Passthrough Volume", 0.2, 2.0, 1.0, 0.05)
    with c2:
        noise_gate_enabled = st.toggle("Noise Gate", value=True)
        gate_threshold = st.slider("Noise Gate Threshold", 0.0, 0.08, 0.005, 0.001)
    with c3:
        pitch_steps = st.slider("Pitch Shift (semitones)", -12, 12, 5, 1)
        echo_mix = st.slider("Echo Mix", 0.1, 0.85, 0.5, 0.05)
    echo_delay = st.slider("Echo Delay (sec)", 0.05, 0.45, 0.2, 0.01)
    normalize_display = st.toggle("Normalize graph display", value=False)

    audio_in = st.audio_input("Record sample")
    if audio_in is not None:
        st.session_state.realtime_raw_bytes = audio_in.read()

    raw = st.session_state.realtime_raw_bytes
    if raw is not None:
        original, sr = decode_audio(raw)
        gated = apply_noise_gate(original, gate_threshold) if noise_gate_enabled else original.astype(np.float32)
        effect_input = gated.copy().astype(np.float32)
        if effect == "Echo":
            effect_stage = add_echo(effect_input, sr, delay_sec=echo_delay, mix=echo_mix)
        elif effect == "Robot":
            effect_stage = np.tanh(2.2 * ring_modulate(effect_input, sr, 35.0))
        elif effect == "Pitch Shift":
            effect_stage = librosa.effects.pitch_shift(effect_input, sr=sr, n_steps=pitch_steps)
        else:
            effect_stage = effect_input

        normalized = normalize_signal(volume * effect_stage)

        processed = normalized
        stage_map = {
            "Input": original,
            "Noise Gate": gated,
            "Effect": effect_stage,
            "Normalization": normalized,
        }
        processed = apply_realtime_effect(
            original,
            sr,
            effect,
            volume,
            noise_gate_enabled,
            gate_threshold,
            pitch_steps,
            echo_mix,
            echo_delay,
        )
        wav_bytes = to_wav_bytes(processed, sr)

        st.info(describe_signal(original, sr))

        analysis_in = analyze_signal(original, sr)
        analysis_out = analyze_signal(processed, sr)
        current_params = {
            "effect": effect,
            "volume": float(volume),
            "noise_gate_enabled": bool(noise_gate_enabled),
            "gate_threshold": float(gate_threshold),
            "pitch_steps": int(pitch_steps),
            "echo_mix": float(echo_mix),
            "echo_delay": float(echo_delay),
        }
        prev_params = st.session_state.get("realtime_prev_params")
        st.session_state.realtime_prev_params = current_params.copy()

        feature_cols = st.columns(4)
        feature_cols[0].metric("Dominant Freq", f"{analysis_out['dominant']:.1f} Hz", f"{analysis_out['dominant'] - analysis_in['dominant']:.1f}")
        feature_cols[1].metric("Spectral Centroid", f"{analysis_out['centroid']:.1f} Hz", f"{analysis_out['centroid'] - analysis_in['centroid']:.1f}")
        feature_cols[2].metric("Bandwidth", f"{analysis_out['bandwidth']:.1f} Hz", f"{analysis_out['bandwidth'] - analysis_in['bandwidth']:.1f}")
        feature_cols[3].metric("Zero Crossings", f"{analysis_out['zcr']:.0f}", f"{analysis_out['zcr'] - analysis_in['zcr']:.0f}")

        st.write("Original")
        st.audio(raw)
        st.write("Processed")
        st.audio(wav_bytes, format="audio/wav")

        s1, s2 = signal_stats(original), signal_stats(processed)
        m1, m2, m3 = st.columns(3)
        m1.metric("Input Peak", f"{s1['peak']:.3f}", f"{s2['peak'] - s1['peak']:.3f}")
        m2.metric("Input RMS", f"{s1['rms']:.3f}", f"{s2['rms'] - s1['rms']:.3f}")
        m3.metric("Output RMS", f"{s2['rms']:.3f}")

        st.plotly_chart(signal_flow_fig(effect, volume, gate_threshold, echo_delay, echo_mix, pitch_steps), use_container_width=True)
        st.plotly_chart(waveform_stage_fig(stage_map, sr, normalize_display), use_container_width=True)
        st.plotly_chart(spectrum_compare_fig(original, processed, sr), use_container_width=True)
        st.plotly_chart(temporal_dynamics_fig(original, processed, sr, normalize_display), use_container_width=True)
        st.plotly_chart(waveform_compare_fig(original, processed, sr), use_container_width=True)
        st.plotly_chart(waveform_3d_fig(processed, sr), use_container_width=True)

        with st.expander("Graph Explanations", expanded=True):
            st.markdown(realtime_graph_explanations(effect, analysis_in, analysis_out, s1, s2))

        with st.expander("Slider Change Impact", expanded=True):
            st.markdown(
                slider_change_explanations(
                    effect,
                    current_params,
                    prev_params,
                    analysis_in,
                    analysis_out,
                )
            )

        st.download_button(
            "Download Processed Audio",
            data=wav_bytes,
            file_name=f"realtime_{effect.lower().replace(' ', '_')}.wav",
            mime="audio/wav",
        )

        with st.expander("AI Summary", expanded=False):
            if st.button("Generate AI Summary", key=f"summary_realtime_{effect}"):
                provider = st.session_state.get("chat_provider", "Gemini")
                model_name = st.session_state.get("chat_model", "gemini-2.0-flash")
                prompt = build_ai_summary(
                    effect,
                    "Realtime live input",
                    original,
                    processed,
                    sr,
                    {
                        "volume": volume,
                        "gate_threshold": gate_threshold,
                        "pitch_steps": pitch_steps,
                        "echo_mix": echo_mix,
                        "echo_delay": echo_delay,
                    },
                )
                st.session_state.realtime_summary = summarize_with_provider(prompt, [], provider, model_name)
            if st.session_state.get("realtime_summary"):
                st.markdown(st.session_state.realtime_summary)
    else:
        st.info("Record a sample first. After recording, sliders and effect controls will reprocess audio instantly.")

    effect_data = EFFECT_INFO[effect]
    st.markdown(effect_theory_card(effect))
    st.markdown(educational_intro(effect))
    st.markdown('</div>', unsafe_allow_html=True)


def upload_tab() -> None:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.subheader("Upload Audio")
    st.caption("Drag-and-drop a voice recording, apply any of 10 presets, preview, and export.")

    preset = st.selectbox("Voice Preset", VOICE_PRESETS, index=0)
    uploaded = st.file_uploader("Upload audio", type=["wav", "mp3", "m4a", "ogg", "flac"])

    if uploaded is not None:
        st.session_state.upload_raw_bytes = uploaded.read()

    raw = st.session_state.upload_raw_bytes
    if raw is not None:
        st.audio(raw)
        with st.spinner("Applying preset..."):
            y, sr = decode_audio(raw)
            out = convert_uploaded_voice(y, sr, preset)
            out_bytes = to_wav_bytes(out, sr)

        st.success("Transformation complete. Changing preset updates output immediately.")
        st.info(describe_signal(y, sr))
        analysis_in = analyze_signal(y, sr)
        analysis_out = analyze_signal(out, sr)
        feature_cols = st.columns(4)
        feature_cols[0].metric("Dominant Freq", f"{analysis_out['dominant']:.1f} Hz", f"{analysis_out['dominant'] - analysis_in['dominant']:.1f}")
        feature_cols[1].metric("Spectral Centroid", f"{analysis_out['centroid']:.1f} Hz", f"{analysis_out['centroid'] - analysis_in['centroid']:.1f}")
        feature_cols[2].metric("Bandwidth", f"{analysis_out['bandwidth']:.1f} Hz", f"{analysis_out['bandwidth'] - analysis_in['bandwidth']:.1f}")
        feature_cols[3].metric("Zero Crossings", f"{analysis_out['zcr']:.0f}", f"{analysis_out['zcr'] - analysis_in['zcr']:.0f}")
        st.audio(out_bytes, format="audio/wav")
        st.markdown(f"### How this preset changes the waveform\n\n{preset_story(preset)}")
        st.markdown(effect_theory_card(preset_to_effect_kind(preset)))
        st.plotly_chart(waveform_compare_fig(y, out, sr), use_container_width=True)
        st.plotly_chart(spectrum_compare_fig(y, out, sr), use_container_width=True)
        st.plotly_chart(waveform_3d_fig(out, sr), use_container_width=True)
        st.download_button(
            "Download Converted Voice",
            data=out_bytes,
            file_name=f"converted_{preset.lower().replace(' ', '_').replace('(', '').replace(')', '').replace('+', 'plus').replace('-', 'minus')}.wav",
            mime="audio/wav",
        )

        with st.expander("AI Summary", expanded=False):
            if st.button("Generate AI Summary", key=f"summary_upload_{preset}"):
                provider = st.session_state.get("chat_provider", "Gemini")
                model_name = st.session_state.get("chat_model", "gemini-2.0-flash")
                prompt = build_ai_summary(
                    preset,
                    "Uploaded recording",
                    y,
                    out,
                    sr,
                    {"preset": preset},
                )
                st.session_state.upload_summary = summarize_with_provider(prompt, [], provider, model_name)
            if st.session_state.get("upload_summary"):
                st.markdown(st.session_state.upload_summary)

    st.markdown('<p class="small-note">Tip: 5-20 second clips produce best results and faster processing.</p>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)


def chat_tab() -> None:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.subheader("Signal Q&A")
    st.caption("Ask about Fourier, Laplace, Z-transform, sampling, filters, modulation, and system stability.")

    st.markdown(
        """
        ### What this assistant can explain
        - Continuous and discrete-time signals
        - Amplitude, frequency, phase, and sampling concepts
        - LTI systems, convolution, impulse response, and stability
        - Fourier, Laplace, and Z-transform formulas
        - How waveform changes map to sound changes
        """
    )

    provider = st.session_state.get("chat_provider", "Groq")
    model_name = st.session_state.get("chat_model", "llama-3.3-70b-versatile")
    st.caption(f"Selected provider: {provider} | Last response source: {st.session_state.get('last_provider_used', '-')}")

    # Keep chat surface clean: provider fallback status is shown via source badge.

    b1, b2 = st.columns([1, 1])
    with b1:
        if st.button("Clear Conversation"):
            st.session_state.chat_history = []
            st.session_state.last_reply = ""
    with b2:
        if st.button("Show Last Reply for Copy") and st.session_state.last_reply:
            st.text_area("Copy response", value=st.session_state.last_reply, height=160)

    for msg in st.session_state.chat_history:
        with st.chat_message("assistant" if msg["role"] == "assistant" else "user"):
            st.markdown(msg["content"])

    prompt = st.chat_input("Ask a Signals and Systems question")
    if prompt:
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                reply = ask_ai_tutor(prompt, st.session_state.chat_history, provider, model_name)
            st.markdown(reply)
            st.caption(f"Response source: {st.session_state.get('last_provider_used', provider)}")

        st.session_state.chat_history.append({"role": "assistant", "content": reply})
        st.session_state.last_reply = reply

    with st.expander("Learning map for new users", expanded=False):
        st.markdown(
            """
            **Signal to sound mapping**

            - A signal is a function that carries information.
            - In audio, the waveform amplitude controls loudness over time.
            - Frequency controls pitch.
            - Phase affects alignment and waveform shape.
            - Linear systems transform signals using rules like convolution.
            - Nonlinear effects create harmonics and timbral changes.
            """
        )

    st.markdown('</div>', unsafe_allow_html=True)


def main() -> None:
    inject_styles()
    ensure_state()
    render_sidebar()
    render_header()

    tab1, tab2, tab3 = st.tabs(["Real-Time", "Upload Audio", "Signal Q&A"])
    with tab1:
        realtime_tab()
    with tab2:
        upload_tab()
    with tab3:
        chat_tab()


if __name__ == "__main__":
    main()

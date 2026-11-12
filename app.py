from pathlib import Path
import base64
import html
import io
import json
import re
import uuid

import numpy as np
import streamlit as st
import streamlit.components.v1 as components
from faster_whisper import WhisperModel
from faster_whisper.audio import decode_audio


# ---------- PAGE ----------

st.set_page_config(
    page_title="Audio Escape Room",
    page_icon="🔐",
    layout="wide",
)

ROOT = Path(__file__).parent
ASSETS = ROOT / "assets"
AUDIO_ROOT = ROOT / "audio"


# ---------- MISSIONS ----------

MISSIONS = {
    "missing_key": {
        "title": "The Missing Key",
        "description": (
            "The office key is missing. Three recovered recordings "
            "contain schedule changes and storage instructions. "
            "Work out the exact location of the key."
        ),
        "question": "Which room and which drawer contain the key?",
        "kind": "key_location",
        "room": "18",
        "drawer": "middle",
        "recordings": [
            ("Reception voicemail", "reception.wav", "reception"),
            ("Employee message", "employee.wav", "employee"),
            ("Security handover", "security.wav", "security"),
        ],
        "success": "You found the key. Mission complete!",
    },

    "locked_archive": {
        "title": "The Locked Archive",
        "description": (
            "An important project file is inside a locked archive. "
            "Compare the recovered messages and work out "
            "the four-digit access code."
        ),
        "question": "What is the four-digit access code?",
        "kind": "code",
        "answers": {"9214"},
        "recordings": [
            ("Manager's voicemail", "manager.wav", "employee"),
            ("Reception message", "reception.wav", "reception"),
            ("Courier update", "courier.wav", "security"),
            ("Security handover", "security.wav", "security"),
            ("Archived voice note", "old_message.wav", "employee"),
        ],
        "success": "Archive unlocked. You recovered the project file!",
    },

    "missing_backup": {
        "title": "The Missing Backup",
        "description": (
            "The team needs its backup drive, but nobody can find it. "
            "Listen to the handover messages and identify "
            "the correct storage location."
        ),
        "question": "Where would you look for the backup drive?",
        "kind": "location",
        "answers": {
            "3",
            "drawer 3",
            "in drawer 3",
            "the drive is in drawer 3",
            "the backup drive is in drawer 3",
        },
        "recordings": [
            ("Manager's instructions", "manager.wav", "reception"),
            ("Design handover", "designer.wav", "employee"),
            ("Storage check", "assistant.wav", "reception"),
        ],
        "success": "You located the backup drive. Mission complete!",
    },

    "redirected_delivery": {
        "title": "The Redirected Delivery",
        "description": (
            "A delivery driver has conflicting instructions. "
            "Listen to the office updates and determine "
            "which loading bay the driver should use."
        ),
        "question": "Which loading bay should the driver use?",
        "kind": "location",
        "answers": {
            "6",
            "bay 6",
            "loading bay 6",
            "in bay 6",
            "use bay 6",
            "the driver should use bay 6",
            "the driver should use loading bay 6",
        },
        "recordings": [
            ("Dispatch message", "dispatcher.wav", "security"),
            ("Allocation update", "coordinator.wav", "employee"),
            ("Supervisor's correction", "supervisor.wav", "reception"),
        ],
        "success": "Delivery redirected to the correct loading bay!",
    },

    "supply_safe": {
        "title": "The Supply Safe",
        "description": (
            "The office supplies are locked inside a safe. "
            "Review the inventory messages and work out "
            "the three-digit code."
        ),
        "question": "What is the three-digit safe code?",
        "kind": "code",
        "answers": {"315"},
        "recordings": [
            ("Manager's instructions", "manager.wav", "reception"),
            ("Inventory recording", "inventory.wav", "employee"),
            ("Returns update", "returns.wav", "security"),
        ],
        "success": "Safe unlocked. You recovered the supplies!",
    },
}


# ---------- IMAGE HELPERS ----------

@st.cache_data
def image_uri(path_string, modified):
    path = Path(path_string)
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


required_assets = [
    ASSETS / "office_background.png",
    ASSETS / "characters.png",
]

missing_assets = [
    path.name
    for path in required_assets
    if not path.is_file()
]

if missing_assets:
    st.error(
        "Missing artwork: "
        + ", ".join(missing_assets)
        + ". Extract the downloaded assets folder beside app.py."
    )
    st.stop()

office_path, characters_path = required_assets

OFFICE = image_uri(
    str(office_path),
    office_path.stat().st_mtime_ns,
)

CHARACTERS = image_uri(
    str(characters_path),
    characters_path.stat().st_mtime_ns,
)


# ---------- DESIGN ----------

st.html("""
<style>
:root {
    color-scheme: dark;
}

.stApp {
    background-color: #070D20;
    color: #EFF3FF;
}

[data-testid="stHeader"],
[data-testid="stToolbar"] {
    display: none !important;
}

.block-container {
    max-width: 1500px;
    padding: 1.8rem 2rem 3rem;
}

h1, h2, h3, h4,
.stMarkdown p,
[data-testid="stWidgetLabel"] p {
    color: #EFF3FF !important;
}

[data-testid="stCaptionContainer"] p {
    color: #ADBDE0 !important;
}

.brand {
    display: flex;
    align-items: center;
    gap: 15px;
    margin-bottom: 10px;
}

.brand-symbol {
    display: flex;
    align-items: center;
    gap: 4px;
    height: 52px;
}

.brand-symbol i {
    width: 4px;
    border-radius: 8px;
    background: #36B8FF;
    box-shadow: 0 0 12px #258DFF55;
}

.brand-name {
    font-size: clamp(26px, 3vw, 40px);
    font-weight: 800;
    letter-spacing: -1px;
}

.brand-tagline {
    color: #9AADE0;
    font-size: 21px;
    margin-top: 3px;
}

.mission-badge {
    display: inline-block;
    border: 1px solid #E8B94F;
    border-radius: 30px;
    background: #080F21CC;
    color: #FFD16A;
    padding: 8px 18px;
    font-size: 15px;
    font-weight: 700;
}

.mission-title {
    font-size: clamp(32px, 4vw, 52px);
    line-height: 1.15;
    font-weight: 800;
    margin: 15px 0 10px;
    letter-spacing: -1px;
    color: #F5F7FF;
}

.mission-description {
    font-size: 19px;
    line-height: 1.6;
    color: #B6C5ED;
    max-width: 1000px;
    margin-bottom: 25px;
}

.st-key-clues_panel,
.st-key-answer_panel {
    border: 1px solid #43598F !important;
    border-radius: 20px !important;
    padding: 20px !important;
    background: linear-gradient(
        135deg,
        rgba(12, 21, 48, 0.94),
        rgba(21, 32, 67, 0.86)
    );
    box-shadow: 0 15px 45px #00000035;
}

.panel-heading {
    font-size: 30px;
    font-weight: 800;
    color: #F3F5FF;
    margin-bottom: 5px;
}

.panel-note {
    font-size: 14px;
    color: #AABCE1;
    margin-bottom: 16px;
    line-height: 1.5;
}

.security-stage {
    position: relative;
    height: 290px;
    border: 1px solid #405A91;
    border-radius: 17px;
    overflow: hidden;
    margin-bottom: 18px;
    background-color: #111E3B;
}

.security-stage::after {
    content: "";
    position: absolute;
    inset: 0;
    background: linear-gradient(
        90deg,
        #0A142AEF 0%,
        #0A142A80 55%,
        transparent 100%
    );
    pointer-events: none;
}

.character {
    background-repeat: no-repeat;
    background-size: 300% 100%;
}

.character.reception {
    background-position: left center;
}

.character.employee {
    background-position: center center;
}

.character.security {
    background-position: right center;
}

.guard {
    position: absolute;
    right: -5px;
    top: -57px;
    width: 230px;
    height: 460px;
    z-index: 1;
}

.speech {
    position: absolute;
    left: 18px;
    bottom: 25px;
    width: 65%;
    z-index: 2;
    box-sizing: border-box;
    border: 1px solid #5A7AB9;
    border-radius: 23px 23px 23px 5px;
    padding: 18px 20px;
    background: linear-gradient(
        120deg,
        #18284EFA,
        #213561F5
    );
    box-shadow: 0 10px 25px #00000035;
}

.speech-label {
    color: #3ADBEF;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    margin-bottom: 10px;
}

.speech-question {
    color: #F5F7FF;
    font-size: clamp(19px, 2vw, 27px);
    line-height: 1.4;
    font-weight: 700;
}

.status-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 10px;
    padding: 13px 15px;
    margin-bottom: 15px;
    border: 1px solid #38578A;
    border-radius: 15px;
    background: #08142BD9;
    color: #B5C8EB;
    font-size: 14px;
}

.status-pill {
    padding: 6px 13px;
    border: 1px solid #AA813F;
    border-radius: 25px;
    color: #FFD16A;
    background: #382D1D;
}

.status-pill.solved {
    border-color: #18B69F;
    color: #65F1D2;
    background: #0B3937;
}

.voice-decoration {
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 25px;
    padding: 10px 0;
}

.microphone-ring {
    display: flex;
    justify-content: center;
    align-items: center;
    width: 86px;
    height: 86px;
    border: 4px solid #39E4DF;
    border-radius: 50%;
    background: radial-gradient(
        circle,
        #123C58,
        #081C33
    );
    box-shadow: 0 0 25px #19D7D875;
}

.mic-icon {
    position: relative;
    display: block;
    width: 34px;
    height: 48px;
}

.mic-icon::before {
    content: "";
    position: absolute;
    top: 2px;
    left: 10px;
    width: 14px;
    height: 28px;
    background: #FFFFFF;
    border-radius: 10px;
}

.mic-icon::after {
    content: "";
    position: absolute;
    top: 16px;
    left: 4px;
    width: 26px;
    height: 22px;
    box-sizing: border-box;
    border: 3px solid #FFFFFF;
    border-top: none;
    border-radius: 0 0 16px 16px;
}

.mic-stem {
    position: absolute;
    top: 36px;
    left: 15px;
    width: 4px;
    height: 9px;
    background: #FFFFFF;
}

.mic-stem::after {
    content: "";
    position: absolute;
    bottom: 0;
    left: -7px;
    width: 18px;
    height: 3px;
    background: #FFFFFF;
    border-radius: 3px;
}

.ambient-wave {
    display: flex;
    align-items: center;
    gap: 5px;
    height: 75px;
}

.ambient-wave i {
    width: 4px;
    border-radius: 7px;
    background: #38DAE4;
    box-shadow: 0 0 8px #24D8E955;
    animation: ambient 1.2s ease-in-out infinite alternate;
}

@keyframes ambient {
    from {
        transform: scaleY(0.45);
        opacity: 0.5;
    }
    to {
        transform: scaleY(1);
        opacity: 1;
    }
}

@media (prefers-reduced-motion: reduce) {
    .ambient-wave i {
        animation: none;
    }
}

.stButton > button,
.stFormSubmitButton > button {
    min-height: 45px;
    border-radius: 13px !important;
    background: #192C52 !important;
    border: 1px solid #5876B3 !important;
    color: #F2F5FF !important;
}

button[kind="primary"],
button[kind="primaryFormSubmit"] {
    background: linear-gradient(
        110deg,
        #087F97,
        #275FC2
    ) !important;
    border-color: #3BC4DD !important;
}

.stButton > button:hover,
.stFormSubmitButton > button:hover {
    border-color: #4DE9E8 !important;
}

[data-baseweb="input"],
[data-baseweb="select"] > div {
    background: #101E3A !important;
    border-color: #4F689C !important;
    border-radius: 12px !important;
    color: #F3F6FF !important;
}

input {
    color: #F3F6FF !important;
    -webkit-text-fill-color: #F3F6FF !important;
}

input::placeholder {
    color: #92A5CC !important;
    -webkit-text-fill-color: #92A5CC !important;
}

[role="tab"] {
    color: #B7C7EC !important;
}

[role="tab"][aria-selected="true"] {
    color: #3EE1E6 !important;
}

[data-testid="stForm"] {
    padding: 0;
    border: 0;
}

.footer {
    text-align: center;
    color: #9BAED2;
    font-size: 13px;
    margin-top: 25px;
}

@media (max-width: 700px) {
    .block-container {
        padding: 1rem;
    }

    .security-stage {
        height: 260px;
    }

    .guard {
        width: 180px;
        height: 360px;
        top: -25px;
        right: -15px;
    }

    .speech {
        width: 70%;
        left: 10px;
        padding: 14px;
    }

    .panel-heading {
        font-size: 25px;
    }

    .ambient-wave {
        gap: 3px;
    }
}
</style>
""")

st.html(f"""
<style>
.stApp {{
    background-image:
        linear-gradient(
            to bottom,
            rgba(5, 10, 25, 0.12),
            rgba(5, 10, 25, 0.72)
        ),
        url("{OFFICE}");
    background-size: cover;
    background-position: center top;
    background-repeat: no-repeat;
    background-attachment: fixed;
}}

.character {{
    background-image: url("{CHARACTERS}");
}}

.security-stage {{
    background-image: url("{OFFICE}");
    background-size: cover;
    background-position: right center;
}}
</style>
""")


# ---------- WHISPER ----------

@st.cache_resource
def load_whisper():
    return WhisperModel(
        "base.en",
        device="cpu",
        compute_type="int8",
    )


# ---------- ANSWER CHECKING ----------

DIGIT_WORDS = {
    "zero": "0",
    "one": "1",
    "two": "2",
    "three": "3",
    "four": "4",
    "five": "5",
    "six": "6",
    "seven": "7",
    "eight": "8",
    "nine": "9",
    "forty": "40",
    "eighteen": "18",
}


def normalize_answer(answer, mission):
    text = answer.lower().strip()

    for word, digit in DIGIT_WORDS.items():
        text = re.sub(rf"\b{word}\b", digit, text)

    if mission["kind"] == "code":
        text = re.sub(
            r"^(?:(?:the\s+)?(?:(?:access|safe)\s+)?"
            r"code\s+is\s+|it\s+is\s+)",
            "",
            text,
        )
        return re.sub(r"[\s,.\-!?;:]+", "", text)

    text = re.sub(r"[^\w\s]", " ", text)
    return " ".join(text.split())


def answer_is_correct(answer, mission):
    text = normalize_answer(answer, mission)

    if mission["kind"] == "key_location":
        rooms = re.findall(
            r"\broom\s+(?:number\s+)?(\d+)\b",
            text,
        )

        drawers = re.findall(
            r"\b(top|middle|bottom)\b",
            text,
        )

        numbers = re.findall(
            r"\b\d+\b",
            text,
        )

        return (
            bool(rooms)
            and set(rooms) == {mission["room"]}
            and bool(drawers)
            and set(drawers) == {mission["drawer"]}
            and bool(re.search(r"\bdrawer\b", text))
            and set(numbers) == {mission["room"]}
            and not bool(
                re.search(
                    r"\b(?:not|isnt|isn\s+t)\b",
                    text,
                )
            )
        )

    return text in mission["answers"]


def check_answer(answer, mission):
    if not answer.strip():
        st.session_state["feedback"] = (
            "warning",
            "Enter or record your conclusion first.",
        )
        st.rerun()

    st.session_state["attempts"] += 1

    if answer_is_correct(answer, mission):
        st.session_state["mission_solved"] = True
        st.session_state.pop("feedback", None)
    else:
        st.session_state["feedback"] = (
            "error",
            "That conclusion does not solve the mystery. "
            "Replay the recordings and compare the details.",
        )

    st.rerun()


def clear_voice_text():
    st.session_state.pop("voice_text", None)
    st.session_state.pop("feedback", None)


def reset_progress():
    st.session_state["mission_solved"] = False
    st.session_state["attempts"] = 0

    st.session_state["game_number"] = (
        st.session_state.get("game_number", 0) + 1
    )

    for key in (
        "voice_text",
        "typed_answer",
        "feedback",
    ):
        st.session_state.pop(key, None)


# ---------- WAVEFORM DATA ----------

@st.cache_data
def load_recording(path_string, modified):
    path = Path(path_string)

    samples = decode_audio(
        str(path),
        sampling_rate=16000,
    )

    if len(samples) == 0:
        raise ValueError(
            f"{path.name} contains no audio."
        )

    blocks = np.array_split(samples, 40)

    levels = np.array([
        float(np.sqrt(np.mean(block ** 2)))
        if len(block) else 0.0
        for block in blocks
    ])

    maximum = float(levels.max())

    if maximum > 0:
        levels = levels / maximum

    heights = [
        round(5 + float(level) * 43, 2)
        for level in levels
    ]

    encoded = base64.b64encode(
        path.read_bytes()
    ).decode("ascii")

    return {
        "src": f"data:audio/wav;base64,{encoded}",
        "peaks": heights,
        "duration": len(samples) / 16000,
    }


# ---------- CUSTOM AUDIO PLAYERS ----------

def render_clue_players(mission_id, mission):
    recordings = []

    for label, filename, character in mission["recordings"]:
        path = AUDIO_ROOT / mission_id / filename

        data = load_recording(
            str(path),
            path.stat().st_mtime_ns,
        )

        recordings.append({
            **data,
            "label": label,
            "character": character,
            "storage_key": (
                f"escape_{st.session_state['browser_token']}_"
                f"{mission_id}_{st.session_state['game_number']}_"
                f"{filename}"
            ),
        })

    template = """
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1">

<style>
* {
    box-sizing: border-box;
}

body {
    margin: 0;
    padding: 3px;
    color: #EFF4FF;
    background: transparent;
    font-family: Arial, sans-serif;
}

.summary {
    color: #A8BDE4;
    font-size: 13px;
    margin: 2px 0 14px;
}

.card {
    position: relative;
    min-height: 165px;
    margin-bottom: 15px;
    padding: 17px;
    overflow: hidden;
    border: 1px solid #405688;
    border-radius: 15px;
    background: linear-gradient(
        120deg,
        #111D3CEF,
        #203059D9
    );
}

.heading {
    position: relative;
    z-index: 2;
    max-width: calc(100% - 75px);
    font-size: 16px;
    line-height: 1.4;
    font-weight: 700;
}

.number {
    color: #33BEFF;
    margin-right: 10px;
}

.character {
    position: absolute;
    right: -2px;
    top: -6px;
    width: 112px;
    height: 224px;
    opacity: 0.95;
    background-image: url("__CHARACTERS__");
    background-size: 300% 100%;
    background-repeat: no-repeat;
}

.reception {
    background-position: left center;
}

.employee {
    background-position: center center;
}

.security {
    background-position: right center;
}

.controls {
    display: flex;
    align-items: center;
    gap: 12px;
    position: relative;
    z-index: 2;
    width: calc(100% - 87px);
    margin-top: 25px;
}

.toggle {
    flex-shrink: 0;
    width: 49px;
    height: 49px;
    border: 1.5px solid #9CB9FF;
    border-radius: 50%;
    background: #162649;
    color: white;
    font-size: 21px;
    cursor: pointer;
}

.toggle:hover {
    border-color: #42E5E5;
    background: #223F68;
}

.wave {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 2px;
    flex: 1;
    min-width: 0;
    height: 55px;
    padding: 0;
    border: 0;
    background: transparent;
    cursor: pointer;
}

.bar {
    display: block;
    flex: 1;
    max-width: 4px;
    min-width: 1px;
    border-radius: 5px;
    background: #82B7FB;
}

.bar.progress {
    background: #35E3E0;
    box-shadow: 0 0 7px #35E3E040;
}

.time {
    position: relative;
    z-index: 2;
    color: #B0C5E9;
    font-size: 12px;
    margin-top: 11px;
}

.badge {
    position: absolute;
    right: 12px;
    top: 12px;
    z-index: 3;
    padding: 5px 8px;
    border: 1px solid #3F698D;
    border-radius: 18px;
    background: #1C3A5F;
    color: #78E6DC;
    font-size: 11px;
}

button:focus-visible {
    outline: 2px solid #47E8E4;
    outline-offset: 4px;
}

.error {
    color: #FFB9B9;
    font-size: 12px;
}

@media (max-width: 350px) {
    .character {
        width: 90px;
        height: 180px;
        top: 18px;
    }

    .controls {
        width: calc(100% - 65px);
        gap: 8px;
    }

    .heading {
        font-size: 14px;
    }
}
</style>
</head>

<body>
<div class="summary" id="summary"></div>
<div id="players"></div>

<script>
const recordings = __RECORDINGS__;
const players = [];
const completed = new Set();

function formatTime(seconds) {
    if (!Number.isFinite(seconds)) return "0:00";

    const minutes = Math.floor(seconds / 60);
    const remainder = Math.floor(seconds % 60);

    return minutes + ":" + String(remainder).padStart(2, "0");
}

function updateSummary() {
    document.getElementById("summary").textContent =
        completed.size + " of " + recordings.length +
        " recordings completed";
}

recordings.forEach((recording, index) => {
    const card = document.createElement("article");
    card.className = "card";

    card.innerHTML = `
        <div class="character ${recording.character}"
             aria-hidden="true"></div>

        <div class="heading">
            <span class="number">
                ${String(index + 1).padStart(2, "0")}
            </span>
            <span class="label"></span>
        </div>

        <span class="badge" hidden>✓ Played</span>

        <div class="controls">
            <button class="toggle"
                    aria-label="Play recording">▶</button>

            <button class="wave"
                    aria-label="Seek within recording"></button>
        </div>

        <div class="time"></div>
        <div class="error" role="status"></div>
    `;

    card.querySelector(".label").textContent = recording.label;

    const toggle = card.querySelector(".toggle");
    const waveform = card.querySelector(".wave");
    const time = card.querySelector(".time");
    const badge = card.querySelector(".badge");
    const error = card.querySelector(".error");

    recording.peaks.forEach(height => {
        const bar = document.createElement("span");
        bar.className = "bar";
        bar.style.height = height + "px";
        waveform.appendChild(bar);
    });

    const audio = new Audio(recording.src);
    audio.preload = "metadata";
    players.push(audio);

    time.textContent =
        "0:00 / " + formatTime(recording.duration);

    try {
        if (
            localStorage.getItem(recording.storage_key)
            === "played"
        ) {
            completed.add(index);
            badge.hidden = false;
        }
    } catch (_) {}

    toggle.addEventListener("click", async () => {
        error.textContent = "";

        if (!audio.paused) {
            audio.pause();
            return;
        }

        players.forEach(other => {
            if (other !== audio) other.pause();
        });

        if (audio.ended) audio.currentTime = 0;

        try {
            await audio.play();
        } catch (_) {
            error.textContent =
                "Unable to play this recording. " +
                "Please refresh and try again.";
        }
    });

    audio.addEventListener("play", () => {
        toggle.textContent = "Ⅱ";
        toggle.setAttribute(
            "aria-label",
            "Pause recording"
        );
    });

    audio.addEventListener("pause", () => {
        toggle.textContent = "▶";
        toggle.setAttribute(
            "aria-label",
            "Play recording"
        );
    });

    audio.addEventListener("timeupdate", () => {
        const duration =
            audio.duration || recording.duration;

        const ratio =
            duration > 0
            ? audio.currentTime / duration
            : 0;

        time.textContent =
            formatTime(audio.currentTime) +
            " / " +
            formatTime(duration);

        waveform.querySelectorAll(".bar").forEach(
            (bar, barIndex) => {
                bar.classList.toggle(
                    "progress",
                    barIndex / recording.peaks.length < ratio
                );
            }
        );
    });

    waveform.addEventListener("click", event => {
        if (!Number.isFinite(audio.duration)) return;

        const bounds = waveform.getBoundingClientRect();

        const fraction = Math.max(
            0,
            Math.min(
                1,
                (event.clientX - bounds.left) / bounds.width
            )
        );

        audio.currentTime = fraction * audio.duration;
    });

    waveform.addEventListener("keydown", event => {
        if (!Number.isFinite(audio.duration)) return;

        if (
            event.key === "ArrowRight" ||
            event.key === "ArrowLeft"
        ) {
            event.preventDefault();

            const change =
                event.key === "ArrowRight" ? 2 : -2;

            audio.currentTime = Math.max(
                0,
                Math.min(
                    audio.duration,
                    audio.currentTime + change
                )
            );
        }
    });

    audio.addEventListener("ended", () => {
        completed.add(index);
        badge.hidden = false;

        try {
            localStorage.setItem(
                recording.storage_key,
                "played"
            );
        } catch (_) {}

        updateSummary();
    });

    document.getElementById("players").appendChild(card);
});

updateSummary();
</script>
</body>
</html>
"""

    payload = json.dumps(recordings).replace(
        "<",
        "\\u003c",
    )

    player_html = (
        template
        .replace("__CHARACTERS__", CHARACTERS)
        .replace("__RECORDINGS__", payload)
    )

    player_height = 40 + len(recordings) * 180

    if hasattr(st, "iframe"):
        st.iframe(
            player_html,
            height=player_height,
        )
    else:
        components.html(
            player_html,
            height=player_height,
            scrolling=True,
        )


# ---------- GAME STATE ----------

APP_VERSION = "illustrated_escape_room_harder_key_v3"

if st.session_state.get("game_app_version") != APP_VERSION:
    reset_progress()
    st.session_state["game_app_version"] = APP_VERSION

st.session_state.setdefault(
    "browser_token",
    uuid.uuid4().hex,
)

st.session_state.setdefault("mission_solved", False)
st.session_state.setdefault("attempts", 0)
st.session_state.setdefault("game_number", 0)


# ---------- HEADER ----------

brand_column, selector_column = st.columns([1.8, 1])

with brand_column:
    st.html("""
    <div class="brand">
        <div class="brand-symbol" aria-hidden="true">
            <i style="height:14px"></i>
            <i style="height:30px"></i>
            <i style="height:48px"></i>
            <i style="height:35px"></i>
            <i style="height:17px"></i>
        </div>

        <div>
            <div class="brand-name">
                Audio Escape Room
            </div>
            <div class="brand-tagline">
                Listen. Speak. Solve.
            </div>
        </div>
    </div>
    """)

with selector_column:
    mission_id = st.selectbox(
        "Choose your mission",
        options=list(MISSIONS),
        format_func=lambda value: MISSIONS[value]["title"],
        key="mission_choice",
        on_change=reset_progress,
    )

mission = MISSIONS[mission_id]
mission_number = list(MISSIONS).index(mission_id) + 1

st.html(f"""
<div class="mission-badge">
    ◈ Mission {mission_number:02d}
</div>

<div class="mission-title">
    {html.escape(mission["title"])}
</div>

<div class="mission-description">
    {html.escape(mission["description"])}
</div>
""")


# ---------- CHECK AUDIO FILES ----------

missing_audio = [
    filename
    for _, filename, _ in mission["recordings"]
    if not (AUDIO_ROOT / mission_id / filename).is_file()
]

if missing_audio:
    st.error(
        "Missing recordings for this mission: "
        + ", ".join(missing_audio)
    )
    st.info("Generate the mission recordings first.")
    st.stop()


# ---------- MAIN LAYOUT ----------

left_column, right_column = st.columns(
    [1, 1.7],
    gap="medium",
)


# ---------- LEFT: VOICE CLUES ----------

with left_column:
    with st.container(key="clues_panel"):
        st.html("""
        <div class="panel-heading">
            🎧 Voice clues
        </div>

        <div class="panel-note">
            Listen carefully. Replay in any order.
        </div>
        """)

        try:
            render_clue_players(mission_id, mission)
        except Exception as error:
            st.error(
                f"Could not prepare the recordings: {error}"
            )


# ---------- RIGHT: SECURITY DESK ----------

with right_column:
    with st.container(key="answer_panel"):
        st.html("""
        <div class="panel-heading">
            🛡️ Security desk
        </div>

        <div class="panel-note">
            Connect the details and submit your conclusion.
        </div>
        """)

        st.html(f"""
        <div class="security-stage">
            <div class="character security guard"
                 aria-hidden="true"></div>

            <div class="speech">
                <div class="speech-label">
                    Your mission
                </div>

                <div class="speech-question">
                    {html.escape(mission["question"])}
                </div>
            </div>
        </div>
        """)

        solved = st.session_state["mission_solved"]

        status = (
            "Mission solved"
            if solved
            else "Awaiting conclusion"
        )

        status_class = "solved" if solved else ""

        st.html(f"""
        <div class="status-row">
            <span class="status-pill {status_class}">
                {"✓" if solved else "◌"} {status}
            </span>

            <span>
                {len(mission["recordings"])} recordings
            </span>

            <span>
                Attempts: {st.session_state["attempts"]}
            </span>
        </div>
        """)

        if solved:
            st.success(f"🔓 {mission['success']}")

            st.button(
                "↻ Play this mission again",
                on_click=reset_progress,
                use_container_width=True,
            )

            st.caption(
                "Choose another mission from the dropdown "
                "to explore a new mystery."
            )

        else:
            feedback = st.session_state.get("feedback")

            if feedback:
                level, message = feedback

                if level == "warning":
                    st.warning(message)
                else:
                    st.error(message)

            voice_tab, typing_tab = st.tabs([
                "🎙 Speak your answer",
                "⌨ Type your answer",
            ])

            with voice_tab:
                heights = [
                    12, 22, 35, 18, 45, 30, 58,
                    38, 25, 49, 64, 35, 19, 44,
                    30, 55, 26, 38, 18, 28, 12,
                ]

                wave = "".join(
                    f'<i style="height:{height}px;'
                    f'animation-delay:{index * 0.07:.2f}s"></i>'
                    for index, height in enumerate(heights)
                )

                st.html(f"""
                <div class="voice-decoration">
                    <div class="microphone-ring"
                         aria-hidden="true">

                        <span class="mic-icon">
                            <span class="mic-stem"></span>
                        </span>

                    </div>

                    <div class="ambient-wave"
                         aria-hidden="true">
                        {wave}
                    </div>
                </div>
                """)

                st.caption(
                    "Use the recorder below to start and stop "
                    "your answer."
                )

                if mission["kind"] == "code":
                    st.caption(
                        "Say each code digit separately."
                    )

                recording = st.audio_input(
                    "Record your conclusion",
                    sample_rate=16000,
                    key=(
                        f"recording_{mission_id}_"
                        f"{st.session_state['game_number']}"
                    ),
                    on_change=clear_voice_text,
                )

                transcribe = st.button(
                    "Transcribe answer",
                    disabled=recording is None,
                    use_container_width=True,
                )

                if transcribe and recording is not None:
                    clear_voice_text()

                    try:
                        with st.spinner(
                            "Reading your spoken answer..."
                        ):
                            model = load_whisper()

                            segments, _ = model.transcribe(
                                io.BytesIO(
                                    recording.getvalue()
                                ),
                                language="en",
                                vad_filter=True,
                                condition_on_previous_text=False,
                            )

                            transcript = " ".join(
                                segment.text.strip()
                                for segment in segments
                            ).strip()

                        if transcript:
                            st.session_state["voice_text"] = (
                                transcript
                            )
                        else:
                            st.warning(
                                "No speech detected. "
                                "Please record again."
                            )

                    except Exception as error:
                        st.error(
                            "Could not transcribe your answer: "
                            f"{error}"
                        )

                if "voice_text" in st.session_state:
                    with st.form(
                        f"spoken_answer_{mission_id}"
                    ):
                        reviewed_answer = st.text_input(
                            "Your spoken answer",
                            key="voice_text",
                            help=(
                                "Correct any transcription mistake "
                                "before submitting."
                            ),
                        )

                        submit_voice = st.form_submit_button(
                            "Submit conclusion",
                            type="primary",
                            use_container_width=True,
                        )

                    if submit_voice:
                        check_answer(
                            reviewed_answer,
                            mission,
                        )

            with typing_tab:
                st.caption(
                    "Enter the conclusion you reached "
                    "from the recordings."
                )

                with st.form(
                    f"typed_answer_{mission_id}"
                ):
                    typed_answer = st.text_input(
                        "Your conclusion",
                        placeholder="Enter your answer...",
                        key="typed_answer",
                    )

                    submit_typed = st.form_submit_button(
                        "Submit conclusion",
                        type="primary",
                        use_container_width=True,
                    )

                if submit_typed:
                    check_answer(
                        typed_answer,
                        mission,
                    )


# ---------- FOOTER ----------

st.html("""
<div class="footer">
    Listen carefully. Connect the details. Solve the mystery.
</div>
""")
st.html("""
<style>
/* Make typed answers clearly visible */
[data-testid="stTextInput"] input {
    background-color: #101E3A !important;
    color: #FFFFFF !important;
    -webkit-text-fill-color: #FFFFFF !important;
    caret-color: #39E4DF !important;
}

[data-testid="stTextInput"] [data-baseweb="input"] {
    background-color: #101E3A !important;
    border: 1px solid #5876B3 !important;
    border-radius: 12px !important;
}

[data-testid="stTextInput"] input::placeholder {
    color: #AABCE1 !important;
    -webkit-text-fill-color: #AABCE1 !important;
    opacity: 1 !important;
}
</style>
""")
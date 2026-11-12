# 🔐 Audio Escape Room

**Listen. Speak. Solve.**

An interactive audio puzzle game where players solve office mysteries by listening to recorded messages, connecting information, and submitting their conclusions through voice or text.

🎧 **[Play the Live Demo](https://d6sv5jnxnrnyutyyh9m36w.streamlit.app/)**

## 🎯 Why I Built This

I built Audio Escape Room to explore how **Phonon’s text-to-speech capabilities** can turn written scenarios into an interactive listening game.

Phonon generates the spoken clues, while Faster-Whisper transcribes players’ spoken answers. Together, they create a workflow where players **listen, connect information, and respond by voice**.

The project combines hands-on experimentation with speech technology and a game designed for listening practice, reasoning challenges, and team activities.

## 🎮 How to Play

1. Choose a mission from the dropdown.
2. Listen to the recovered recordings.
3. Connect the details across different messages.
4. Pay attention to corrections, cancellations, and outdated information.
5. Speak or type your conclusion.
6. Submit your answer to check whether you solved the mystery.

You can replay recordings in any order. Clue transcripts and solutions are not displayed on the game screen.

## 🗂️ Available Missions

| Mission | Your Task |
| --- | --- |
| **The Missing Key** | Find the exact location of the office key. |
| **The Locked Archive** | Work out a four-digit archive access code. |
| **The Missing Backup** | Locate a backup drive using project and storage updates. |
| **The Redirected Delivery** | Identify the correct loading bay after allocation changes. |
| **The Supply Safe** | Calculate a safe code using inventory information. |

## ✨ Features

- Five office mystery missions.
- Illustrated office background and character artwork.
- Audio clues with waveform playback controls.
- Replay recordings whenever needed.
- Voice recording and answer transcription.
- Editable transcription before submitting.
- Typed answers as an alternative.
- Answer feedback and attempt tracking.

## 🛠️ Tools and Models

| Technology | Purpose |
| --- | --- |
| **Python** | Game logic, answer checking, and audio processing. |
| **Streamlit** | Web interface and application state. |
| **Phonon through `ptts`** | Generates spoken clues from written scripts. |
| **Faster-Whisper — `base.en`** | Transcribes players’ spoken answers into English text. |
| **NumPy** | Processes audio for waveform visualization. |
| **HTML, CSS, and JavaScript** | Custom styling, animations, and audio controls. |

The clues are generated in advance and saved as audio files. Phonon does not need to run while someone plays the deployed game.

Puzzle scripts and solutions are predefined. Answer checking uses programmed rules; no language model generates puzzles or evaluates the player’s reasoning.

## 🔄 Game Workflow

**Choose a mission → Listen to recordings → Connect the information → Speak or type an answer → Review and submit → Receive feedback**

For spoken answers, Faster-Whisper converts the recording into text. Players can correct transcription mistakes before submitting their conclusion.

## 💡 Possible Uses

- **Team activities:** Solve mysteries together and compare interpretations.
- **Listening practice:** Follow details across several spoken messages.
- **Reasoning challenges:** Distinguish current instructions from outdated information.
- **Speech technology demonstrations:** Explore text-to-speech and speech recognition in one application.

These are intended uses; the prototype has not been evaluated as a formal training or assessment tool.

## 📁 Project Structure

- **`app.py`** — Streamlit interface and game logic.
- **`requirements.txt`** — Libraries needed to run the application.
- **`assets/`** — Office background and character images.
- **`audio/`** — Prerecorded clues organized into mission folders.

Keep the folder names and file locations unchanged so the app can find its artwork and recordings.

## 🚀 Run Locally

Use **Python 3.11**.

Install the dependencies:

```bash
python -m pip install -r requirements.txt
```

Start the application:

```bash
python -m streamlit run app.py
```

Open the local URL displayed in the terminal. Allow microphone access if you want to submit spoken answers.

The Whisper model downloads on first use, so an internet connection is required for that initial download.

## 🌐 Deployment

The project code, artwork, and recordings are stored on **GitHub**, and the application is hosted on **Streamlit Community Cloud**.

Players can access the deployed game through its web link without running Python on their own computers.

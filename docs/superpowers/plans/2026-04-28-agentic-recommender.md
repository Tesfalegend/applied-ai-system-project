# Agentic Music Recommender Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wrap the existing `Recommender` class in a plan/act/check agentic workflow powered by the Anthropic Claude API.

**Architecture:** A `RecommenderAgent` class orchestrates three LLM-backed steps — `_plan` (parse natural-language request into `UserProfile`), `_act` (score via existing `Recommender`), and `_check` (confidence-rate the results). Each step is logged via a thin structured logger. If confidence is below threshold the agent retries once (re-plan + re-act) before returning.

**Tech Stack:** Python 3.11, anthropic SDK (>=0.40.0), python-dotenv (>=1.0.0), pytest + unittest.mock, existing Song/UserProfile/Recommender untouched.

---

## File Map

| Action | Path | Responsibility |
|--------|------|----------------|
| Modify | `requirements.txt` | Add `anthropic>=0.40.0`, `python-dotenv>=1.0.0` |
| Create | `src/logger.py` | Structured console + file logger |
| Create | `src/agent.py` | `RecommenderAgent` class |
| Modify | `src/main.py` | CLI entrypoint using agent |
| Create | `tests/test_agent.py` | 3 mocked agent tests |

---

### Task 1: Update requirements.txt

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: Add new dependencies**

Replace the contents of `requirements.txt` with:

```
pandas
pytest
streamlit
anthropic>=0.40.0
python-dotenv>=1.0.0
```

- [ ] **Step 2: Verify install**

```bash
pip install -r requirements.txt
```

Expected: resolves without conflict. `anthropic` and `python-dotenv` appear in pip list.

- [ ] **Step 3: Commit**

```bash
git add requirements.txt
git commit -m "chore: add anthropic and python-dotenv to requirements"
```

---

### Task 2: Create src/logger.py

**Files:**
- Create: `src/logger.py`

- [ ] **Step 1: Write the logger module**

```python
import logging
import os
from datetime import datetime, timezone

LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "agent.log")

os.makedirs(LOG_DIR, exist_ok=True)

_fmt = "%(asctime)s | %(levelname)s | %(step)s | %(message)s"
_datefmt = "%Y-%m-%dT%H:%M:%S"

_logger = logging.getLogger("agent")
_logger.setLevel(logging.DEBUG)

if not _logger.handlers:
    _fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
    _fh.setFormatter(logging.Formatter(_fmt, datefmt=_datefmt))
    _logger.addHandler(_fh)

    _ch = logging.StreamHandler()
    _ch.setFormatter(logging.Formatter(_fmt, datefmt=_datefmt))
    _logger.addHandler(_ch)


def _log(level: str, step: str, message: str) -> None:
    extra = {"step": step}
    if level == "INFO":
        _logger.info(message, extra=extra)
    elif level == "WARN":
        _logger.warning(message, extra=extra)
    elif level == "ERROR":
        _logger.error(message, extra=extra)


def info(step: str, message: str) -> None:
    _log("INFO", step, message)


def warn(step: str, message: str) -> None:
    _log("WARN", step, message)


def error(step: str, message: str) -> None:
    _log("ERROR", step, message)
```

- [ ] **Step 2: Smoke-test the logger manually**

```bash
python -c "from src.logger import info, warn, error; info('test','hello'); warn('test','careful'); error('test','oops')"
```

Expected: three lines on stdout and in `logs/agent.log`.

- [ ] **Step 3: Commit**

```bash
git add src/logger.py
git commit -m "feat: add structured logger writing to logs/agent.log"
```

---

### Task 3: Create src/agent.py

**Files:**
- Create: `src/agent.py`

- [ ] **Step 1: Write the module**

```python
import json
from typing import Optional
import anthropic

from src.recommender import Recommender, UserProfile
from src import logger

_PLAN_PROMPT = """\
Parse the following music request into a JSON object with EXACTLY these keys:
  favorite_genre (string), favorite_mood (string),
  target_energy (float 0.0-1.0), likes_acoustic (bool).

Valid genres: pop, lofi, rock, ambient, jazz, synthwave, indie pop, world,
  hip-hop, classical, r&b, country, electronic, reggae, metal, folk, blues.
Valid moods: happy, chill, intense, relaxed, moody, focused.

Respond with ONLY the JSON object, no markdown, no explanation.

Request: {request}
"""

_PLAN_RETRY_PROMPT = """\
Your previous response could not be parsed as valid JSON.
Try again. Respond with ONLY a JSON object with keys:
  favorite_genre (string), favorite_mood (string),
  target_energy (float 0.0-1.0), likes_acoustic (bool).

Request: {request}
"""

_CHECK_PROMPT = """\
A user asked: "{request}"

The top recommended songs are:
{song_list}

Rate how well these recommendations match the request on a scale from 0.0 to 1.0,
where 1.0 is a perfect match.

Respond with ONLY a JSON object: {{"confidence": <float>, "reasoning": "<one sentence>"}}
No markdown, no explanation outside the JSON.
"""

_VALID_GENRES = {
    "pop", "lofi", "rock", "ambient", "jazz", "synthwave", "indie pop",
    "world", "hip-hop", "classical", "r&b", "country", "electronic",
    "reggae", "metal", "folk", "blues",
}
_VALID_MOODS = {"happy", "chill", "intense", "relaxed", "moody", "focused"}


class RecommenderAgent:
    def __init__(
        self,
        recommender: Recommender,
        model: str = "claude-haiku-4-5-20251001",
        confidence_threshold: float = 0.6,
    ):
        self.recommender = recommender
        self.model = model
        self.confidence_threshold = confidence_threshold
        self._client = anthropic.Anthropic()

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def run(self, user_request: str) -> dict:
        if not user_request or not user_request.strip():
            raise ValueError("user_request must not be empty or whitespace-only")

        steps: list[dict] = []
        extra_context: Optional[str] = None

        try:
            # --- first attempt ---
            profile, plan_step = self._plan(user_request, extra_context)
            steps.append(plan_step)

            if profile is None:
                return self._error_dict(steps, "Could not parse user request into a profile")

            songs, act_step = self._act(profile)
            steps.append(act_step)

            confidence, reasoning, check_step = self._check(user_request, songs)
            steps.append(check_step)

            # --- retry if confidence too low ---
            if confidence < self.confidence_threshold:
                logger.warn("run", f"Confidence {confidence:.2f} below threshold {self.confidence_threshold}; retrying")
                extra_context = f"Previous attempt scored {confidence:.2f}. Reasoning: {reasoning}"

                profile2, plan_step2 = self._plan(user_request, extra_context)
                steps.append(plan_step2)

                if profile2 is not None:
                    songs, act_step2 = self._act(profile2)
                    steps.append(act_step2)

                    confidence, reasoning, check_step2 = self._check(user_request, songs)
                    steps.append(check_step2)

            return {
                "recommendations": songs,
                "confidence": confidence,
                "reasoning": reasoning,
                "steps": steps,
                "error": None,
            }

        except ValueError:
            raise
        except Exception as exc:
            logger.error("run", str(exc))
            return self._error_dict(steps, str(exc))

    # ------------------------------------------------------------------
    # Internal steps
    # ------------------------------------------------------------------

    def _plan(self, user_request: str, extra_context: Optional[str]) -> tuple[Optional[UserProfile], dict]:
        step_name = "plan"
        logger.info(step_name, f"Parsing request: {user_request!r}")

        prompt = _PLAN_PROMPT.format(request=user_request)
        if extra_context:
            prompt += f"\n\nAdditional context: {extra_context}"

        profile = None
        raw = ""
        try:
            raw = self._call_api(prompt)
            profile = self._parse_profile(raw)
        except (json.JSONDecodeError, KeyError, ValueError):
            logger.warn(step_name, "First parse failed; retrying with corrective prompt")
            try:
                raw = self._call_api(_PLAN_RETRY_PROMPT.format(request=user_request))
                profile = self._parse_profile(raw)
            except Exception as exc:
                logger.error(step_name, f"Retry parse also failed: {exc}")
                profile = None

        step = {"step": step_name, "input": user_request, "output": raw}
        logger.info(step_name, f"Parsed profile: {profile}")
        return profile, step

    def _act(self, profile: UserProfile) -> tuple[list[dict], dict]:
        step_name = "act"
        logger.info(step_name, f"Scoring songs for profile: {profile}")

        songs = self.recommender.recommend(profile, k=5)
        song_dicts = [
            {
                "title": s.title,
                "artist": s.artist,
                "genre": s.genre,
                "mood": s.mood,
                "energy": s.energy,
            }
            for s in songs
        ]

        step = {"step": step_name, "input": str(profile), "output": song_dicts}
        logger.info(step_name, f"Returned {len(song_dicts)} songs")
        return song_dicts, step

    def _check(self, user_request: str, songs: list[dict]) -> tuple[float, str, dict]:
        step_name = "check"
        logger.info(step_name, "Evaluating recommendation quality")

        song_list = "\n".join(
            f"- {s['title']} by {s['artist']} (genre={s['genre']}, mood={s['mood']}, energy={s['energy']})"
            for s in songs
        )
        prompt = _CHECK_PROMPT.format(request=user_request, song_list=song_list)

        confidence = 0.0
        reasoning = "unknown"
        raw = ""
        try:
            raw = self._call_api(prompt)
            data = json.loads(raw)
            confidence = float(data["confidence"])
            confidence = max(0.0, min(1.0, confidence))
            reasoning = str(data.get("reasoning", ""))
        except Exception as exc:
            logger.error(step_name, f"Check parse failed: {exc}")

        step = {"step": step_name, "input": user_request, "output": {"confidence": confidence, "reasoning": reasoning}}
        logger.info(step_name, f"Confidence: {confidence:.2f}")
        return confidence, reasoning, step

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _call_api(self, prompt: str) -> str:
        message = self._client.messages.create(
            model=self.model,
            max_tokens=256,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text.strip()

    def _parse_profile(self, raw: str) -> UserProfile:
        data = json.loads(raw)
        genre = str(data["favorite_genre"]).lower()
        mood = str(data["favorite_mood"]).lower()
        energy = float(data["target_energy"])
        likes_acoustic = bool(data["likes_acoustic"])

        if genre not in _VALID_GENRES:
            raise ValueError(f"Invalid genre: {genre!r}")
        if mood not in _VALID_MOODS:
            raise ValueError(f"Invalid mood: {mood!r}")
        if not (0.0 <= energy <= 1.0):
            raise ValueError(f"target_energy out of range: {energy}")

        return UserProfile(
            favorite_genre=genre,
            favorite_mood=mood,
            target_energy=energy,
            likes_acoustic=likes_acoustic,
        )

    @staticmethod
    def _error_dict(steps: list[dict], message: str) -> dict:
        return {
            "recommendations": [],
            "confidence": 0.0,
            "reasoning": "",
            "steps": steps,
            "error": message,
        }
```

- [ ] **Step 2: Commit**

```bash
git add src/agent.py
git commit -m "feat: add RecommenderAgent with plan/act/check agentic workflow"
```

---

### Task 4: Write tests/test_agent.py (before touching main.py)

**Files:**
- Create: `tests/test_agent.py`

- [ ] **Step 1: Write the three tests**

```python
import json
import pytest
from unittest.mock import MagicMock, patch, call

from src.recommender import Song, Recommender
from src.agent import RecommenderAgent


def _make_recommender():
    songs = [
        Song(id=i, title=f"Track {i}", artist="A", genre="pop", mood="happy",
             energy=0.8, tempo_bpm=120, valence=0.8, danceability=0.7, acousticness=0.2)
        for i in range(1, 6)
    ]
    return Recommender(songs)


def _profile_json():
    return json.dumps({
        "favorite_genre": "pop",
        "favorite_mood": "happy",
        "target_energy": 0.8,
        "likes_acoustic": False,
    })


def _check_json(confidence=0.85):
    return json.dumps({"confidence": confidence, "reasoning": "Good match"})


def _mock_message(text: str):
    msg = MagicMock()
    msg.content = [MagicMock(text=text)]
    return msg


# -----------------------------------------------------------------------

def test_empty_input_raises_value_error():
    rec = _make_recommender()
    agent = RecommenderAgent(rec)
    with pytest.raises(ValueError):
        agent.run("")
    with pytest.raises(ValueError):
        agent.run("   ")


def test_agent_returns_dict_with_required_keys():
    rec = _make_recommender()
    agent = RecommenderAgent(rec)

    with patch.object(agent._client.messages, "create") as mock_create:
        mock_create.side_effect = [
            _mock_message(_profile_json()),   # plan call
            _mock_message(_check_json(0.85)), # check call
        ]

        result = agent.run("I want upbeat pop music")

    required_keys = {"recommendations", "confidence", "reasoning", "steps", "error"}
    assert required_keys == set(result.keys())
    assert result["error"] is None
    assert isinstance(result["recommendations"], list)
    assert isinstance(result["confidence"], float)
    assert isinstance(result["reasoning"], str)
    assert isinstance(result["steps"], list)


def test_low_confidence_triggers_one_retry():
    rec = _make_recommender()
    agent = RecommenderAgent(rec)

    with patch.object(agent._client.messages, "create") as mock_create:
        mock_create.side_effect = [
            _mock_message(_profile_json()),        # plan call 1
            _mock_message(_check_json(0.3)),       # check call 1 → low confidence
            _mock_message(_profile_json()),        # plan call 2 (retry)
            _mock_message(_check_json(0.8)),       # check call 2
        ]

        result = agent.run("chill study vibes")

    # 4 API calls total: plan, check, plan-retry, check-retry
    assert mock_create.call_count == 4
    assert result["confidence"] == pytest.approx(0.8)
    assert result["error"] is None
```

- [ ] **Step 2: Run the tests**

```bash
pytest tests/test_agent.py -v
```

Expected:
```
tests/test_agent.py::test_empty_input_raises_value_error PASSED
tests/test_agent.py::test_agent_returns_dict_with_required_keys PASSED
tests/test_agent.py::test_low_confidence_triggers_one_retry PASSED
3 passed
```

- [ ] **Step 3: Commit**

```bash
git add tests/test_agent.py
git commit -m "test: add mocked agent tests for empty input, keys, and retry logic"
```

---

### Task 5: Update src/main.py

**Files:**
- Modify: `src/main.py`

- [ ] **Step 1: Replace main.py**

```python
"""
Music Recommender — agentic CLI entrypoint.

Usage:
    python -m src.main "I want chill lofi beats"
    python -m src.main                          # interactive prompt
"""
import sys
from dotenv import load_dotenv

load_dotenv()

from src.recommender import load_songs, Recommender
from src.agent import RecommenderAgent


def main() -> None:
    if len(sys.argv) > 1:
        user_request = " ".join(sys.argv[1:])
    else:
        user_request = input("Describe the music you want: ").strip()

    songs_data = load_songs("data/songs.csv")
    from src.recommender import Song
    song_objects = [
        Song(
            id=int(row["id"]),
            title=row["title"],
            artist=row["artist"],
            genre=row["genre"],
            mood=row["mood"],
            energy=float(row["energy"]),
            tempo_bpm=float(row["tempo_bpm"]),
            valence=float(row["valence"]),
            danceability=float(row["danceability"]),
            acousticness=float(row["acousticness"]),
        )
        for row in songs_data
    ]

    recommender = Recommender(song_objects)
    agent = RecommenderAgent(recommender)

    print(f"\nRunning agent for: {user_request!r}\n")
    result = agent.run(user_request)

    if result["error"]:
        print(f"Error: {result['error']}")
        return

    print(f"Confidence: {result['confidence']:.2f}")
    print(f"Reasoning : {result['reasoning']}\n")

    print("Top 5 Recommendations:")
    print("-" * 40)
    for song in result["recommendations"]:
        print(f"  {song['title']} by {song['artist']}")
        print(f"  genre={song['genre']}  mood={song['mood']}  energy={song['energy']}")
        print()

    print("Step Trace:")
    for step in result["steps"][:3]:
        print(f"  [{step['step'].upper()}] done")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Smoke-test (requires ANTHROPIC_API_KEY in .env)**

```bash
python -m src.main "upbeat pop songs for the gym"
```

Expected: structured output with confidence, reasoning, 5 songs, and 3-line step trace. If no API key, set it in `.env` as `ANTHROPIC_API_KEY=sk-ant-...`.

- [ ] **Step 3: Run full test suite**

```bash
pytest -v
```

Expected: all 5 tests pass (2 original + 3 new).

- [ ] **Step 4: Commit**

```bash
git add src/main.py
git commit -m "feat: update main.py to use RecommenderAgent with CLI arg and .env support"
```

---

## Self-Review

**Spec coverage:**
- [x] requirements.txt — Task 1
- [x] src/logger.py with ISO timestamp, level, step, message, auto-create logs/ — Task 2
- [x] RecommenderAgent.__init__ with model + confidence_threshold — Task 3
- [x] run() returns dict with all 5 required keys — Task 3
- [x] _plan, _act, _check each logged as a separate step — Task 3
- [x] _plan: strict JSON prompt, retry once on parse failure — Task 3
- [x] _act: calls existing Recommender top-5 — Task 3
- [x] _check: confidence 0-1 + one-sentence reasoning — Task 3
- [x] retry on low confidence (max one) using previous reasoning as extra context — Task 3
- [x] ValueError on empty/whitespace request — Task 3
- [x] API errors caught, logged ERROR, graceful error dict returned — Task 3
- [x] Field validation before use — Task 3 (_parse_profile)
- [x] main.py: load_dotenv, CLI arg / stdin fallback, Recommender + Agent instantiation, pretty-print — Task 5
- [x] test_empty_input_raises_value_error — Task 4
- [x] test_agent_returns_dict_with_required_keys — Task 4
- [x] test_low_confidence_triggers_one_retry (4 API calls, confidence=0.8) — Task 4

**Placeholder scan:** No TBD, no "add appropriate error handling" stubs found.

**Type consistency:** `UserProfile` fields (favorite_genre, favorite_mood, target_energy, likes_acoustic) consistent across agent.py parse, test_agent.py fixture, and recommender.py dataclass. `Song` fields consistent across recommender.py and main.py construction.

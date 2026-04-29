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
    """
    Agentic wrapper around Recommender that uses the Anthropic API for
    natural-language understanding and quality evaluation.

    Orchestrates three steps — plan (parse request), act (score songs),
    check (rate quality) — and retries once when confidence is too low.
    All Anthropic API errors are caught and returned as graceful error dicts.
    """

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
        """
        Execute the full plan/act/check agentic loop for a music request.

        Raises ValueError for empty input. All other failures (API errors,
        parse errors) are caught and returned as a dict with error set.
        Returns a dict with keys: recommendations, confidence, reasoning,
        steps (list of per-step dicts), and error (None or str).
        """
        if not user_request or not user_request.strip():
            raise ValueError("user_request must not be empty or whitespace-only")

        steps: list[dict] = []
        extra_context: Optional[str] = None

        try:
            profile, plan_step = self._plan(user_request, extra_context)
            steps.append(plan_step)

            if profile is None:
                return self._error_dict(steps, "Could not parse user request into a profile")

            songs, act_step = self._act(profile)
            steps.append(act_step)

            confidence, reasoning, check_step = self._check(user_request, songs)
            steps.append(check_step)

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

    def _plan(self, user_request: str, extra_context: Optional[str]) -> tuple:
        """
        Call the Anthropic API to parse the user request into a UserProfile.

        On JSON parse failure, retries once with a corrective prompt.
        Network and rate-limit errors on the initial call propagate to run()
        for graceful handling; errors on the retry are caught here and logged.
        Returns (UserProfile | None, step_dict).
        """
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

    def _act(self, profile: UserProfile) -> tuple:
        """
        Score all songs against the UserProfile using the existing Recommender.

        No API calls are made here — this step is deterministic and cannot fail
        unless the underlying Recommender raises, which propagates to run().
        Returns (list[song_dict], step_dict) with the top-5 songs.
        """
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

    def _check(self, user_request: str, songs: list) -> tuple:
        """
        Ask the Anthropic API to rate how well the songs match the request.

        Parses a JSON response containing confidence (0.0–1.0) and a one-sentence
        reasoning string. On any API or parse error, logs ERROR and falls back to
        confidence=0.0 so the caller can still return a graceful dict.
        Returns (confidence: float, reasoning: str, step_dict).
        """
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
            data = json.loads(self._extract_json(raw))
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
        try:
            message = self._client.messages.create(
                model=self.model,
                max_tokens=256,
                messages=[{"role": "user", "content": prompt}],
            )
            return message.content[0].text.strip()
        except anthropic.RateLimitError as exc:
            logger.error("api", f"Rate limit hit — back off and retry later: {exc}")
            raise
        except anthropic.APIConnectionError as exc:
            logger.error("api", f"Network error connecting to Anthropic API: {exc}")
            raise
        except anthropic.APIStatusError as exc:
            logger.error("api", f"Anthropic API returned status {exc.status_code}: {exc.message}")
            raise
        except anthropic.APIError as exc:
            logger.error("api", f"Anthropic API error: {exc}")
            raise

    @staticmethod
    def _extract_json(raw: str) -> str:
        """Strip markdown fences and return the innermost {...} block."""
        # Remove ```json ... ``` or ``` ... ``` wrappers the model sometimes adds
        text = raw.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            # drop first and last fence lines
            inner = [l for l in lines[1:] if not l.strip().startswith("```")]
            text = "\n".join(inner).strip()
        # Grab from first '{' to last '}' as a safety net
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end >= start:
            text = text[start : end + 1]
        return text

    def _parse_profile(self, raw: str) -> UserProfile:
        data = json.loads(self._extract_json(raw))
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
    def _error_dict(steps: list, message: str) -> dict:
        return {
            "recommendations": [],
            "confidence": 0.0,
            "reasoning": "",
            "steps": steps,
            "error": message,
        }

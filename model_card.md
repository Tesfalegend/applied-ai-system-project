# Model Card: Music Recommender Simulation
## Applied AI System Final Project

---

## 1. Model Name

**VibeFinder 1.0** (with agentic wrapper for the AI 110 final project)

The deterministic scoring engine underneath is unchanged from the original Module 3 submission. What's new is a `RecommenderAgent` layer that uses Claude Haiku 4.5 to turn natural-language requests into structured queries the recommender can score, and to rate the quality of the resulting picks.

---

## 2. Intended Use

VibeFinder 1.0 suggests up to 5 songs from an 18-track catalog based on a user's declared genre preference, mood, and energy level. With the new agent layer, users can describe what they want in plain English ("chill lofi for studying") instead of filling out a structured profile.

It is designed for classroom exploration of how content-based recommender systems and agentic workflows work, not for real users or production deployment.

The system assumes users either know what they want or can describe it conversationally. It does not learn from listening history, skip patterns, or user behavior of any kind.

---

## 3. How the Model Works

Every song in the catalog has three key attributes: a genre label (like "pop" or "lofi"), a mood label (like "happy" or "chill"), and an energy level on a scale from 0.0 (very calm) to 1.0 (very intense).

When you provide your preferences (or describe them to the agent in natural language, which then parses them into the structured form), the system checks every single song in the catalog against what you said you like. If a song's genre matches yours, it earns 2 points, genre is weighted the most because it is usually the strongest indicator of whether you will enjoy a song. If the mood also matches, the song earns 1 more point. Finally, the system calculates how close the song's energy level is to your target: a perfect match earns a full 1 extra point, and a song that is further away in energy earns proportionally less.

Once every song has been scored, the list is sorted from highest to lowest, and the top 5 are returned along with a plain-language explanation of why each song ranked where it did. The maximum possible score is 4.0.

In the agentic wrapper, two extra LLM calls bracket this scoring step: one to parse natural language into the structured profile, and one afterward to rate confidence in the result on a 0.0 to 1.0 scale. If confidence is below 0.6, the agent re-plans once and tries again.

---

## 4. Data

The catalog contains 18 songs stored in `data/songs.csv`. The original 10 songs covered pop, lofi, rock, ambient, synthwave, jazz, and indie pop. Eight songs were added to expand the catalog into world, electronic, folk, classical, r&b, metal, and funk.

Moods represented include: happy, chill, intense, relaxed, focused, moody, melancholy, romantic, and energetic.

All song data was invented for this simulation, it does not reflect real artists or real streaming statistics. The genre and mood labels follow Western popular music conventions, which means the system implicitly encodes those conventions as a baseline for what "genre" means.

---

## 5. Strengths

- **Transparent**: every recommendation includes a human-readable explanation of exactly why that song scored what it did. There are no hidden factors.
- **Deterministic at the scoring layer**: the same parsed profile always produces the same scored output. There is no randomness in the recommender itself.
- **Calibrated uncertainty in the agent**: the check step is genuinely calibrated. On the deliberately vague test case ("I just want something good"), the agent reports confidence around 0.4 and explains why, rather than pretending it understood.
- **Effective for clear preferences**: users who know exactly what they want (for example, "chill lofi with low energy for studying") get sensible results immediately.
- **Genre weighting is calibrated**: giving genre 2x the weight of mood correctly ensures that a matching genre plus a different mood still beats a non-matching genre with a matching mood.
- **Graceful failure**: API errors, network issues, and JSON parse failures all result in a clear error dict instead of a crash.

---

## 6. Limitations and Bias

- **Catalog size**: 18 songs is too small for real diversity. Profiles that don't match the dominant genres (pop and lofi) will often see the same 2 to 3 songs at the top regardless of their other preferences.
- **Binary genre matching**: "indie pop" and "pop" are treated as completely unrelated. A user who loves pop will never get partial credit for an indie pop song, even though real listeners often enjoy both.
- **No collaborative signal**: the system cannot discover that people who love lofi also tend to enjoy jazz. It treats every genre and mood as independent.
- **Only 3 features scored**: tempo, valence, danceability, and acousticness are stored but not used. A user who specifically wants acoustic music will not see that preference reflected.
- **Original catalog bias**: the starter 10 songs included 3 lofi songs and 2 pop songs, giving those genres an outsized share of the catalog before expansion. Users who prefer lofi had more options to match against from the start.
- **Western pop bias in genre labels**: the catalog over-represents Western pop, rock, and adjacent styles. A user who wants Amharic music, K-pop, Latin music, or anything outside the catalog's narrow band will get bad recommendations no matter what they type.
- **The agent's check step grades its own work.** Asking the same model to judge whether its own recommendations are good has obvious circularity issues. A separate evaluator model (or a human) would be more trustworthy.
- **Confidence is self-reported.** When the model says it's 0.85 confident, that number isn't externally validated. It might be calibrated, it might be optimistic. There's no ground truth to check against.
- **English-only input.** The plan prompt assumes English. Non-English requests would likely produce unpredictable parsing.

---

## 7. Evaluation

Three user profiles were tested directly against the original recommender:

**High-Energy Pop Fan** (`genre: pop, mood: happy, energy: 0.9`): "Sunrise City" ranked above "Gym Hero" because the mood bonus (+1.0 for "happy") outweighed "Gym Hero"'s slightly closer energy. This was the expected and correct result, mood alignment should matter. Songs from other genres fell 2+ points behind.

**Chill Lofi Studier** (`genre: lofi, mood: chill, energy: 0.4`): The three lofi/chill songs (Midnight Coding, Library Rain, Focus Flow) dominated the top results. "Focus Flow" ranked third rather than first because its mood is "focused," not "chill", the system correctly penalized the mood mismatch. Songs from other genres scored far lower.

**Deep Intense Rock Listener** (`genre: rock, mood: intense, energy: 0.95`): "Storm Runner" ranked first as expected. Surprisingly, "Adrenaline Rush" (metal, not rock) ranked second, ahead of other rock songs, because its mood ("intense") matched and its energy (0.96) was nearly identical to the user's target (0.95). This revealed that a strong mood + energy match can outrank a weak genre match.

**Agent unit tests:** 5 of 5 passing. Two original Module 3 tests for the Recommender still pass after the agent was added on top. Three new tests cover the agent's control flow: empty input raises ValueError, the returned dict has all required keys, low confidence triggers exactly one retry.

**Agent live evaluation harness:** 7 of 8 cases passing (87.5%). Average confidence 0.81 across all 8 cases. Total runtime ~17.5 seconds. The 8 cases cover: high-energy workout, calm study, sad introspection, road trip, party, deep focus, falling asleep, and one deliberately ambiguous case ("I just want something good"). The single failure was the sad-introspection case, which produced average song energy of 0.46 against a tight 0.45 threshold. Defensible picks, intentionally strict threshold.

---

## 8. Future Work

1. **Score `tempo_bpm`**: allow users to specify a target BPM range. Songs within the range earn bonus points; songs outside lose points. This would help distinguish "intense rock at 150 BPM" from "intense pop at 130 BPM."

2. **Use `likes_acoustic`**: the `UserProfile` class already stores this boolean. Songs with `acousticness > 0.7` could earn +0.5 for users who prefer acoustic music, rewarding songs like "Mountain Echo" and "Coffee Shop Stories" for acoustic listeners.

3. **Genre similarity matrix**: define partial matches between related genres (e.g., "indie pop" is 70% similar to "pop") instead of binary 0/1 matching. This would surface more relevant songs for users and reduce the all-or-nothing effect of genre.

4. **Diversity penalty**: the current system can return five nearly identical songs from the same genre. A diversity bonus could reduce the score of a song that is too similar to one already selected, forcing a more varied top-5 list.

5. **Add a vector-based retrieval step**: turn the agent into a proper RAG system so it can handle requests that mention specific artists, lyric themes, or attributes the simple scoring rule misses.

6. **Separate evaluator model**: break the circularity in the agent's check step by using a different prompt or a different model entirely to judge the recommendations.

7. **Streamlit or Next.js UI**: so the demo doesn't require a terminal.

---

## 9. Personal Reflection

The most surprising moment in building the original recommender was realizing how much the *weights*, not the algorithm itself, determine what users see. Changing genre from +2.0 to +0.5 completely reshuffled the results: songs that had never appeared in recommendations suddenly moved to the top, not because anything changed about the songs, but because the definition of "relevant" shifted. Real music platforms face this same decision at massive scale, and their weight choices invisibly determine which artists get discovered and which stay buried.

Building the agent extension on top taught me a related lesson at a different layer: the hardest part of agentic workflows isn't the AI part. It's the boundaries. Where should the agent retry? What counts as recoverable? When should it fail loud vs fail graceful? Every "yes" you give to a retry adds robustness but also adds cost and latency. Mocked tests passing in milliseconds gave me false confidence. The first live eval run failed entirely on bugs the mocks couldn't catch.

What surprised me most was how valuable the deliberately vague test case turned out to be. It would have been easy to make the agent always sound confident, because confidence reads as competence. Watching it honestly report 0.4 on a vague request, and explain *why* it was uncertain, felt like the system actually understanding its own limits. That feels like the more responsible default, even when it makes the demo less impressive.

Using AI tools to brainstorm the scoring formula and identify edge cases saved time, but the most important decisions, how much genre should count, whether mood or energy matters more, where retries should happen, what to call recoverable, required human judgment. No amount of AI assistance could answer those questions without understanding what a "good recommendation" means to a real listener, or what level of confidence is acceptable to surface to a user. That gap between math and meaning is exactly where human oversight stays necessary, even in systems that feel fully automated.

---

## 10. AI Collaboration

This section is about how I worked with AI tools to build this project, including specific cases where the AI helped and where it got things wrong.

### Tools used

I used Claude (in Claude.ai) to plan the architecture, write the prompts I would feed to Claude Code, and draft documentation. I used Claude Code (CLI) to actually write and edit the source files in the repo. The Anthropic API itself is what powers the agent at runtime.

### One helpful AI suggestion

When the eval harness first failed on the live API, I noticed the model kept wrapping its JSON output in markdown code fences even though the prompt explicitly said not to. Claude Code suggested I stop trying to make the model behave and instead add a small `_extract_json` helper that strips ` ``` ` fences and grabs the innermost `{ ... }` block before parsing. This was the right call. Fighting model behavior with stricter prompts is fragile. Defensive parsing on the consuming end is robust. The fix was about 10 lines and made the parser tolerant of the model's actual output instead of brittle to it.

### One flawed AI suggestion

When Claude Code wrote the eval harness summary table, it used a Unicode arrow character (`→`) in the per-case status line. On my Windows terminal (CP1252 encoding), this crashed the script the moment it tried to print. The fix was trivial (`->` instead of `→`), but the suggestion was a real flaw. The AI didn't account for my actual environment, even though I was working on Windows the whole time. It's a reminder that AI suggestions optimize for the most common case, not necessarily for my specific case, and reviewing output with an eye on environmental assumptions is part of the job.

### How I think about working with AI now

The tools are genuinely useful as accelerators. They produce a working first draft faster than I can write one. But the design judgment, the trade-off decisions, the choice of where to be strict and where to be lenient, that all still falls on me. The most valuable habit I'm building is reading AI output with the same skepticism I'd give to a teammate's pull request: helpful, willing to merge most of it, but never just rubber-stamping.

### Could this system be misused?

In its current form, no, it's an 18-song demo. But the pattern (LLM agent calling a deterministic tool with self-reported confidence) absolutely could be misused at scale: confidently wrong recommendations in higher-stakes domains (medical, legal, financial), prompt injection through user requests, gaming the confidence score by tuning the check prompt to always rate highly. If I built this for real users, I'd separate the evaluator from the agent, log everything for audit, and probably gate any high-stakes action behind a human review step.

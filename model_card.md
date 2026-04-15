# Model Card: Music Recommender Simulation

## 1. Model Name

**VibeFinder 1.0**

---

## 2. Intended Use

VibeFinder 1.0 suggests up to 5 songs from an 18-track catalog based on a user's declared genre preference, mood, and energy level. It is designed for classroom exploration of how content-based recommender systems work — not for real users or production deployment.

The system assumes users can clearly state what they want. It does not learn from listening history, skip patterns, or user behavior of any kind.

---

## 3. How the Model Works

Every song in the catalog has three key attributes: a genre label (like "pop" or "lofi"), a mood label (like "happy" or "chill"), and an energy level on a scale from 0.0 (very calm) to 1.0 (very intense).

When you provide your preferences, the system checks every single song in the catalog against what you said you like. If a song's genre matches yours, it earns 2 points — genre is weighted the most because it is usually the strongest indicator of whether you will enjoy a song. If the mood also matches, the song earns 1 more point. Finally, the system calculates how close the song's energy level is to your target: a perfect match earns a full 1 extra point, and a song that is further away in energy earns proportionally less.

Once every song has been scored, the list is sorted from highest to lowest, and the top 5 are returned along with a plain-language explanation of why each song ranked where it did. The maximum possible score is 4.0.

---

## 4. Data

The catalog contains 18 songs stored in `data/songs.csv`. The original 10 songs covered pop, lofi, rock, ambient, synthwave, jazz, and indie pop. Eight songs were added to expand the catalog into world, electronic, folk, classical, r&b, metal, and funk.

Moods represented include: happy, chill, intense, relaxed, focused, moody, melancholy, romantic, and energetic.

All song data was invented for this simulation — it does not reflect real artists or real streaming statistics. The genre and mood labels follow Western popular music conventions, which means the system implicitly encodes those conventions as a baseline for what "genre" means.

---

## 5. Strengths

- **Transparent**: every recommendation includes a human-readable explanation of exactly why that song scored what it did. There are no hidden factors.
- **Deterministic**: the same inputs always produce the same outputs. There is no randomness.
- **Effective for clear preferences**: users who know exactly what they want (for example, "chill lofi with low energy for studying") get sensible results immediately.
- **Genre weighting is calibrated**: giving genre 2x the weight of mood correctly ensures that a matching genre plus a different mood still beats a non-matching genre with a matching mood.

---

## 6. Limitations and Bias

- **Catalog size**: 18 songs is too small for real diversity. Profiles that don't match the dominant genres (pop and lofi) will often see the same 2–3 songs at the top regardless of their other preferences.
- **Binary genre matching**: "indie pop" and "pop" are treated as completely unrelated. A user who loves pop will never get a partial credit for an indie pop song, even though real listeners often enjoy both.
- **No collaborative signal**: the system cannot discover that people who love lofi also tend to enjoy jazz. It treats every genre and mood as independent.
- **Only 3 features scored**: tempo, valence, danceability, and acousticness are stored but not used. A user who specifically wants acoustic music will not see that preference reflected.
- **Declarative preferences required**: the system cannot infer what you like from your listening history — you must tell it exactly what you want, which real users often cannot do.
- **Original catalog bias**: the starter 10 songs included 3 lofi songs and 2 pop songs, giving those genres an outsized share of the catalog before expansion. Users who prefer lofi had more options to match against from the start.

---

## 7. Evaluation

Three user profiles were tested to evaluate the system's behavior:

**High-Energy Pop Fan** (`genre: pop, mood: happy, energy: 0.9`): "Sunrise City" ranked above "Gym Hero" because the mood bonus (+1.0 for "happy") outweighed "Gym Hero"'s slightly closer energy. This was the expected and correct result — mood alignment should matter. Songs from other genres fell 2+ points behind.

**Chill Lofi Studier** (`genre: lofi, mood: chill, energy: 0.4`): The three lofi/chill songs (Midnight Coding, Library Rain, Focus Flow) dominated the top results. "Focus Flow" ranked third rather than first because its mood is "focused," not "chill" — the system correctly penalized the mood mismatch. Songs from other genres scored far lower.

**Deep Intense Rock Listener** (`genre: rock, mood: intense, energy: 0.95`): "Storm Runner" ranked first as expected. Surprisingly, "Adrenaline Rush" (metal, not rock) ranked second, ahead of other rock songs, because its mood ("intense") matched and its energy (0.96) was nearly identical to the user's target (0.95). This revealed that a strong mood + energy match can outrank a weak genre match.

The automated test suite (`pytest`) confirms that the OOP Recommender class correctly sorts songs by score (pop/happy song ranks above lofi/chill song for a pop/happy user profile) and that all explanations return non-empty strings.

---

## 8. Future Work

1. **Score `tempo_bpm`**: allow users to specify a target BPM range. Songs within the range earn bonus points; songs outside lose points. This would help distinguish "intense rock at 150 BPM" from "intense pop at 130 BPM."

2. **Use `likes_acoustic`**: the `UserProfile` class already stores this boolean. Songs with `acousticness > 0.7` could earn +0.5 for users who prefer acoustic music, rewarding songs like "Mountain Echo" and "Coffee Shop Stories" for acoustic listeners.

3. **Genre similarity matrix**: define partial matches between related genres (e.g., "indie pop" is 70% similar to "pop") instead of binary 0/1 matching. This would surface more relevant songs for users and reduce the all-or-nothing effect of genre.

4. **Diversity penalty**: the current system can return five nearly identical songs from the same genre. A diversity bonus could reduce the score of a song that is too similar to one already selected, forcing a more varied top-5 list.

---

## 9. Personal Reflection

The most surprising moment in building this system was realizing how much the *weights* — not the algorithm itself — determine what users see. Changing genre from +2.0 to +0.5 completely reshuffled the results: songs that had never appeared in recommendations suddenly moved to the top, not because anything changed about the songs, but because the definition of "relevant" shifted. Real music platforms face this same decision at massive scale, and their weight choices invisibly determine which artists get discovered and which stay buried.

Using AI tools to brainstorm the scoring formula and identify edge cases saved time, but the most important decisions — how much genre should count, whether mood or energy matters more, which songs to add to the catalog — required human judgment. No amount of AI assistance could answer those questions without understanding what a "good recommendation" means to a real listener. That gap between math and meaning is exactly where human oversight stays necessary, even in systems that feel fully automated.

# Reflection: Profile Comparisons and System Behavior

## Profile 1 vs Profile 2: High-Energy Pop Fan vs Chill Lofi Studier

These two profiles are essentially opposites. The pop fan wants high energy (0.9), upbeat mood, and mainstream genre. The lofi studier wants low energy (0.4), a calm mood, and a genre built for background listening.

The results split cleanly between the two catalogs. The pop fan's top 5 were entirely from pop, indie pop, and high-energy genres. The lofi studier's top 5 were dominated by lofi/chill songs. Almost none of the same songs appeared in both lists.

What this tells us: when genre and energy pull in opposite directions this strongly, the system correctly segments users. It does what a content-based filter is supposed to do — serve clear, distinct taste profiles with distinct results. The energy scoring was the key differentiator in the middle of the ranking, where multiple songs had no genre match. A song like "Gym Hero" (energy 0.93) that scores well for the pop fan earns almost no energy points from the lofi studier because the energy gap is 0.53.

**What surprised me**: "Rooftop Lights" (indie pop, happy, energy 0.76) appeared in the pop fan's list despite being a different genre. The mood match (+1.0) and close energy (+0.86 similarity) compensated for missing the genre match. This is the system working as intended, but seeing it in practice made it concrete.

---

## Profile 2 vs Profile 3: Chill Lofi Studier vs Deep Intense Rock Listener

Both profiles want genre-specific results, but their energy targets are at opposite ends of the spectrum: 0.4 for lofi, 0.95 for rock.

The lofi studier's list was predictable and valid — three lofi songs plus two chill-adjacent low-energy songs filled the top 5. The rock listener's list had one surprise: "Adrenaline Rush" (metal, intense, energy 0.96) ranked second, above all other songs that weren't "Storm Runner."

**Why it makes sense**: "Adrenaline Rush" matched the mood ("intense" = +1.0) and had energy only 0.01 away from the rock listener's target (energy similarity ≈ 0.99). That combination (1.0 + 0.99 = 1.99 points) was enough to beat out songs that had neither a genre nor a mood match, even with a better energy score. The scoring logic rewarded total alignment across multiple features, not just one dominant feature.

**What this reveals about the algorithm**: the system can surface cross-genre recommendations when enough non-genre attributes align. A metal song beating out rock songs for a rock listener feels unexpected at first, but it makes sense once you see the math. This is the same kind of cross-genre discovery that real recommendation platforms use — they surface "you might also like X" outside your stated genre because other attributes match strongly.

---

## Profile 1 vs Profile 3: High-Energy Pop Fan vs Deep Intense Rock Listener

Both users want high-energy music, but their genre and mood preferences differ. The pop fan wants happy, the rock listener wants intense.

The overlap was minimal. "Gym Hero" (pop, intense, energy 0.93) appeared near the top for both — it earned genre + energy points for the pop fan, and mood + energy points for the rock listener. This is the only song that scored well for both because it bridges high energy and the "intense" mood.

"Sunrise City" (pop, happy, energy 0.82) ranked highly for the pop fan but dropped significantly for the rock listener because neither genre nor mood matched.

**What this tells us about the mood weight**: even though mood is only worth +1.0 (half of genre), it had a real effect on ranking when two high-energy songs were otherwise comparable. This confirmed that the relative weights produce reasonable behavior — genre dominates, but mood is the tiebreaker.

---

## Overall Takeaway

The system behaves consistently and predictably across all three profiles. Its results are explainable because every score is derived from the same three rules. The main limitation I observed is that profiles for underrepresented genres (like "world" or "folk") would get much weaker top results because there are only 1–2 songs per genre in the catalog. A real system would need hundreds of songs per genre before content-based filtering becomes genuinely useful.

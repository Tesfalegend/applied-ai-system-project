"""
Evaluation harness for RecommenderAgent — makes real Anthropic API calls.

Run with:
    python -m tests.eval_harness
"""
import os
import sys
import time
from datetime import datetime, timezone

from dotenv import load_dotenv

load_dotenv()

# Allow running as `python -m tests.eval_harness` from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.recommender import load_songs, Recommender, Song
from src.agent import RecommenderAgent

# ---------------------------------------------------------------------------
# Evaluation cases
# Each dict has:
#   request          – natural-language input
#   expected_mood    – informational label (not used in pass/fail logic)
#   energy_check     – "min" (avg energy >= threshold) or "max" (<= threshold)
#   energy_threshold – the cutoff float
#   conf_threshold   – minimum confidence to pass (default 0.6; case 8 uses 0.4)
# ---------------------------------------------------------------------------
EVAL_CASES = [
    {
        "request": "I need high-energy workout music to push through the last mile",
        "expected_mood": "energetic",
        "energy_check": "min",
        "energy_threshold": 0.70,
        "conf_threshold": 0.6,
    },
    {
        "request": "Something calm and relaxing for a quiet study session at home",
        "expected_mood": "calm",
        "energy_check": "max",
        "energy_threshold": 0.50,
        "conf_threshold": 0.6,
    },
    {
        "request": "Late night sad songs for introspection and reflection",
        "expected_mood": "sad",
        "energy_check": "max",
        "energy_threshold": 0.45,
        "conf_threshold": 0.6,
    },
    {
        "request": "Upbeat road trip music for a long drive with friends",
        "expected_mood": "happy",
        "energy_check": "min",
        "energy_threshold": 0.55,
        "conf_threshold": 0.6,
    },
    {
        "request": "High tempo party bangers to keep the dance floor alive all night",
        "expected_mood": "energetic",
        "energy_check": "min",
        "energy_threshold": 0.75,
        "conf_threshold": 0.6,
    },
    {
        "request": "Deep focus instrumentals for coding a complex algorithm",
        "expected_mood": "focused",
        "energy_check": "max",
        "energy_threshold": 0.55,
        "conf_threshold": 0.6,
    },
    {
        "request": "Gentle ambient music to help me fall asleep",
        "expected_mood": "calm",
        "energy_check": "max",
        "energy_threshold": 0.40,
        "conf_threshold": 0.6,
    },
    {
        # Deliberately vague — agent should return something reasonable but
        # honestly low confidence. Pass threshold lowered to 0.4.
        "request": "I just want something good",
        "expected_mood": "happy",
        "energy_check": "min",
        "energy_threshold": 0.0,  # energy check always passes (any avg >= 0.0)
        "conf_threshold": 0.4,
    },
]


def _build_recommender() -> Recommender:
    songs_data = load_songs("data/songs.csv")
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
    return Recommender(song_objects)


def _avg_energy(songs: list[dict]) -> float:
    if not songs:
        return 0.0
    return sum(s["energy"] for s in songs) / len(songs)


def _energy_passes(avg: float, check: str, threshold: float) -> bool:
    if check == "min":
        return avg >= threshold
    return avg <= threshold


def _run_case(agent: RecommenderAgent, case: dict) -> dict:
    t0 = time.perf_counter()
    result = agent.run(case["request"])
    elapsed = time.perf_counter() - t0

    songs = result.get("recommendations", [])
    confidence = result.get("confidence", 0.0)
    avg_eng = _avg_energy(songs)

    conf_ok = confidence >= case["conf_threshold"]
    energy_ok = _energy_passes(avg_eng, case["energy_check"], case["energy_threshold"])
    passed = conf_ok and energy_ok and result.get("error") is None

    return {
        "passed": passed,
        "confidence": confidence,
        "avg_energy": avg_eng,
        "runtime": elapsed,
        "error": result.get("error"),
        "reasoning": result.get("reasoning", ""),
    }


def _format_table(results: list[dict], cases: list[dict]) -> str:
    lines = []

    # Header
    lines.append(f"{'#':<4} {'STATUS':<6} {'CONF':>6} {'AVG_E':>6} {'RT(s)':>7}  REQUEST (truncated to 45 chars)")
    lines.append("-" * 85)

    total_conf = 0.0
    passes = 0
    total_rt = 0.0

    for i, (res, case) in enumerate(zip(results, cases), start=1):
        status = "PASS" if res["passed"] else "FAIL"
        conf = res["confidence"]
        avg_e = res["avg_energy"]
        rt = res["runtime"]
        req = case["request"][:45]

        lines.append(f"{i:<4} {status:<6} {conf:>6.2f} {avg_e:>6.2f} {rt:>7.2f}s  {req}")
        if res["error"]:
            lines.append(f"     ERROR: {res['error']}")

        total_conf += conf
        total_rt += rt
        if res["passed"]:
            passes += 1

    n = len(results)
    pass_pct = 100.0 * passes / n if n else 0.0
    avg_conf = total_conf / n if n else 0.0

    lines.append("-" * 85)
    lines.append(f"OVERALL  Pass rate: {passes}/{n} = {pass_pct:.1f}%   "
                 f"Avg confidence: {avg_conf:.2f}   Total runtime: {total_rt:.2f}s")

    return "\n".join(lines)


def main() -> None:
    recommender = _build_recommender()
    agent = RecommenderAgent(recommender)

    print("\n=== RecommenderAgent Evaluation Harness ===\n")
    print(f"Running {len(EVAL_CASES)} cases against the live Anthropic API...\n")

    results = []
    for i, case in enumerate(EVAL_CASES, start=1):
        print(f"[{i}/{len(EVAL_CASES)}] {case['request'][:60]}...")
        res = _run_case(agent, case)
        status = "PASS" if res["passed"] else "FAIL"
        print(f"      -> {status}  conf={res['confidence']:.2f}  avg_energy={res['avg_energy']:.2f}  {res['runtime']:.2f}s")
        results.append(res)

    table = _format_table(results, EVAL_CASES)

    print("\n" + "=" * 85)
    print(table)
    print("=" * 85 + "\n")

    # Save to logs/
    os.makedirs("logs", exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    out_path = os.path.join("logs", "eval_results.txt")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(f"Evaluation run: {ts}\n\n")
        f.write(table + "\n")

    print(f"Results saved to {out_path}")


if __name__ == "__main__":
    main()

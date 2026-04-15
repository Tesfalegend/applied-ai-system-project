"""
Command line runner for the Music Recommender Simulation.

This file helps you quickly run and test your recommender.

You will implement the functions in recommender.py:
- load_songs
- score_song
- recommend_songs
"""

from src.recommender import load_songs, recommend_songs


def main() -> None:
    songs = load_songs("data/songs.csv")

    profiles = [
        {
            "name": "High-Energy Pop Fan",
            "prefs": {"genre": "pop", "mood": "happy", "energy": 0.9}
        },
        {
            "name": "Chill Lofi Studier",
            "prefs": {"genre": "lofi", "mood": "chill", "energy": 0.4}
        },
        {
            "name": "Deep Intense Rock Listener",
            "prefs": {"genre": "rock", "mood": "intense", "energy": 0.95}
        },
    ]

    for profile in profiles:
        print(f"\n{'=' * 50}")
        print(f"User Profile: {profile['name']}")
        print(f"{'=' * 50}")
        recommendations = recommend_songs(profile['prefs'], songs, k=5)
        print(f"\nTop {len(recommendations)} recommendations:\n")
        for song, score, explanation in recommendations:
            print(f"  {song['title']} by {song['artist']}")
            print(f"  Score: {score:.2f}")
            print(f"  Because: {explanation}")
            print()


if __name__ == "__main__":
    main()

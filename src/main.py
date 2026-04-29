"""
Music Recommender — agentic CLI entrypoint.

Usage:
    python -m src.main "I want chill lofi beats"
    python -m src.main                          # interactive prompt
"""
import sys
from dotenv import load_dotenv

load_dotenv()

from src.recommender import load_songs, Recommender, Song
from src.agent import RecommenderAgent


def main() -> None:
    if len(sys.argv) > 1:
        user_request = " ".join(sys.argv[1:])
    else:
        user_request = input("Describe the music you want: ").strip()

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

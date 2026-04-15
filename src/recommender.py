import csv
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

@dataclass
class Song:
    """
    Represents a song and its attributes.
    Required by tests/test_recommender.py
    """
    id: int
    title: str
    artist: str
    genre: str
    mood: str
    energy: float
    tempo_bpm: float
    valence: float
    danceability: float
    acousticness: float

@dataclass
class UserProfile:
    """
    Represents a user's taste preferences.
    Required by tests/test_recommender.py
    """
    favorite_genre: str
    favorite_mood: str
    target_energy: float
    likes_acoustic: bool

class Recommender:
    """
    OOP implementation of the recommendation logic.
    Required by tests/test_recommender.py
    """
    def __init__(self, songs: List[Song]):
        self.songs = songs

    def recommend(self, user: UserProfile, k: int = 5) -> List[Song]:
        """Returns the top-k songs ranked by score against the user's preferences."""
        def song_score(song: Song) -> float:
            score = 0.0
            if song.genre == user.favorite_genre:
                score += 2.0
            if song.mood == user.favorite_mood:
                score += 1.0
            score += 1.0 - abs(song.energy - user.target_energy)
            return score

        return sorted(self.songs, key=song_score, reverse=True)[:k]

    def explain_recommendation(self, user: UserProfile, song: Song) -> str:
        """Returns a human-readable explanation of why a song was recommended."""
        reasons = []
        if song.genre == user.favorite_genre:
            reasons.append("genre match (+2.0)")
        if song.mood == user.favorite_mood:
            reasons.append("mood match (+1.0)")
        energy_similarity = 1.0 - abs(song.energy - user.target_energy)
        reasons.append(f"energy similarity ({energy_similarity:.2f})")
        return " | ".join(reasons)

def load_songs(csv_path: str) -> List[Dict]:
    """Loads songs from a CSV file and returns a list of dicts with typed numeric values."""
    songs = []
    with open(csv_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            row['id'] = int(row['id'])
            row['energy'] = float(row['energy'])
            row['tempo_bpm'] = int(row['tempo_bpm'])
            row['valence'] = float(row['valence'])
            row['danceability'] = float(row['danceability'])
            row['acousticness'] = float(row['acousticness'])
            songs.append(row)
    return songs

def score_song(user_prefs: Dict, song: Dict) -> Tuple[float, List[str]]:
    """Scores a single song against user preferences using genre, mood, and energy matching."""
    score = 0.0
    reasons = []

    if song['genre'] == user_prefs.get('genre', ''):
        score += 2.0
        reasons.append("genre match (+2.0)")

    if song['mood'] == user_prefs.get('mood', ''):
        score += 1.0
        reasons.append("mood match (+1.0)")

    energy_similarity = 1.0 - abs(float(song['energy']) - float(user_prefs.get('energy', 0.5)))
    score += energy_similarity
    reasons.append(f"energy similarity ({energy_similarity:.2f})")

    return score, reasons

def recommend_songs(user_prefs: Dict, songs: List[Dict], k: int = 5) -> List[Tuple[Dict, float, str]]:
    """Returns the top-k recommended songs as (song, score, explanation) tuples, sorted by score."""
    scored = []
    for song in songs:
        score, reasons = score_song(user_prefs, song)
        explanation = " | ".join(reasons)
        scored.append((song, score, explanation))

    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:k]

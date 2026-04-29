import json
import pytest
from unittest.mock import MagicMock, patch

from src.recommender import Song, Recommender
from src.agent import RecommenderAgent


def _make_recommender():
    songs = [
        Song(
            id=i, title=f"Track {i}", artist="A", genre="pop", mood="happy",
            energy=0.8, tempo_bpm=120, valence=0.8, danceability=0.7, acousticness=0.2,
        )
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
            _mock_message(_profile_json()),    # plan call
            _mock_message(_check_json(0.85)),  # check call
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

from unittest.mock import patch

from api import recommendations


class DummySession:
    def __init__(self, rows):
        self.rows = rows

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

    def run(self, _query, **_kwargs):
        return self.rows


class DummyDriver:
    def __init__(self, rows):
        self.rows = rows

    def session(self):
        return DummySession(self.rows)


def _record(**kwargs):
    return kwargs


def test_recommend_projects_uses_driver_output():
    rows = [
        _record(project_id="p1", title="Proyecto 1", matching_skills=3),
        _record(project_id="p2", title="Proyecto 2", matching_skills=1),
    ]
    with patch("api.recommendations.GraphDatabase.driver", return_value=DummyDriver(rows)):
        result = recommendations.recommend_projects(user_id=10)

    assert result == [
        {"id": "p1", "title": "Proyecto 1", "matches": 3},
        {"id": "p2", "title": "Proyecto 2", "matches": 1},
    ]


def test_recommend_peers_and_skills_formats_payload():
    peer_rows = [_record(peer_id=2, name="Ana", similarity=4)]
    skill_rows = [_record(skill="python", demand=5)]

    with patch("api.recommendations.GraphDatabase.driver", side_effect=[DummyDriver(peer_rows), DummyDriver(skill_rows)]):
        peers = recommendations.recommend_peers(user_id=1)
        skills = recommendations.recommend_skills(user_id=1)

    assert peers == [{"id": 2, "name": "Ana", "similarity": 4}]
    assert skills == [{"skill": "python", "demand": 5}]

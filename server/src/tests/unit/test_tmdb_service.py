import logging
from unittest.mock import MagicMock

from services.tmdb import TMDB


def _mock_json_response(payload):
    response = MagicMock()
    response.json.return_value = payload
    response.raise_for_status.return_value = None
    return response


def test_movie_search_attaches_v3_api_key_param(caplog):
    tmdb = TMDB("v3-api-key")
    tmdb.session.request = MagicMock(
        return_value=_mock_json_response({"results": [{"id": 550, "title": "Fight Club"}]})
    )

    caplog.set_level(logging.DEBUG, logger="services.tmdb")

    result = tmdb.lookup_media("Fight Club", "movie")

    assert result["id"] == 550
    tmdb.session.request.assert_called_once()
    _, endpoint = tmdb.session.request.call_args.args
    params = tmdb.session.request.call_args.kwargs["params"]

    assert endpoint == "https://api.themoviedb.org/3/search/movie"
    assert params["query"] == "Fight Club"
    assert params["api_key"] == "v3-api-key"
    assert "has_api_key_param=True" in caplog.text
    assert "v3-api-key" not in caplog.text


def test_tv_search_attaches_v3_api_key_param():
    tmdb = TMDB("v3-api-key")
    tmdb.session.request = MagicMock(
        return_value=_mock_json_response({"results": [{"id": 1399, "name": "Game of Thrones"}]})
    )

    result = tmdb.lookup_media("Game of Thrones", "tv")

    assert result["id"] == 1399
    tmdb.session.request.assert_called_once()
    _, endpoint = tmdb.session.request.call_args.args
    params = tmdb.session.request.call_args.kwargs["params"]

    assert endpoint == "https://api.themoviedb.org/3/search/tv"
    assert params["query"] == "Game of Thrones"
    assert params["api_key"] == "v3-api-key"


def test_media_detail_attaches_v3_api_key_param():
    tmdb = TMDB("v3-api-key")
    tmdb.session.request = MagicMock(
        return_value=_mock_json_response({"id": 550, "title": "Fight Club"})
    )

    result = tmdb.get_media_detail("550", "movie")

    assert result["id"] == 550
    tmdb.session.request.assert_called_once()
    _, endpoint = tmdb.session.request.call_args.args
    params = tmdb.session.request.call_args.kwargs["params"]

    assert endpoint == "https://api.themoviedb.org/3/movie/550"
    assert params["api_key"] == "v3-api-key"


def test_bearer_token_uses_authorization_header_without_api_key_param():
    tmdb = TMDB("eyJ.fake.token")
    tmdb.session.request = MagicMock(
        return_value=_mock_json_response({"results": [{"id": 603, "title": "The Matrix"}]})
    )

    result = tmdb.lookup_media("The Matrix", "movie")

    assert result["id"] == 603
    tmdb.session.request.assert_called_once()
    params = tmdb.session.request.call_args.kwargs["params"]

    assert "api_key" not in params
    assert tmdb.session.headers["Authorization"] == "Bearer eyJ.fake.token"

import requests
import logging
import json
from typing import Any, Dict, Optional

class TMDB:
    """
    A class to interact with the TMDB API for retrieving media information, such as poster art.
    """
    BASE_URL = "https://api.themoviedb.org/3"
    REQUEST_TIMEOUT = 15

    def __init__(self, tmdb_api_key: str):
        """
        Initializes the Tmdb class with the API key.

        Args:
            tmdb_api_key (str): The API key for TMDB.
        """
        # Setup Logging
        self.logger = logging.getLogger(__name__)

        self.tmdb_api_key = tmdb_api_key.strip() if tmdb_api_key else None
        self.session = requests.Session()
        self.auth_mode = self._detect_auth_mode(self.tmdb_api_key)

        if not self.tmdb_api_key:
            self.logger.error("TMDB API key is not configured.")
        elif self.auth_mode == "bearer":
            self.session.headers.update({"Authorization": f"Bearer {self.tmdb_api_key}"})

        self.logger.debug(
            "TMDB client initialized. auth_configured=%s auth_mode=%s has_authorization_header=%s",
            bool(self.tmdb_api_key),
            self.auth_mode,
            bool(self.session.headers.get("Authorization")),
        )

    def _detect_auth_mode(self, tmdb_api_key: Optional[str]) -> Optional[str]:
        """
        TMDB supports v3 API keys as an api_key query parameter and v4 read
        access tokens as a bearer header. The setting is named TMDB_API_KEY, so
        accept both forms and attach authentication correctly for each.
        """
        if not tmdb_api_key:
            return None

        if tmdb_api_key.startswith("eyJ") or tmdb_api_key.count(".") >= 2:
            return "bearer"

        return "api_key"

    def _build_params(self, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        request_params = dict(params or {})
        if self.auth_mode == "api_key" and self.tmdb_api_key:
            request_params.setdefault("api_key", self.tmdb_api_key)
        return request_params

    def _auth_attached(self, params: Dict[str, Any]) -> bool:
        return bool(self.session.headers.get("Authorization")) or bool(params.get("api_key"))

    def _request(self, method: str, path: str, params: Optional[Dict[str, Any]] = None) -> Optional[requests.Response]:
        if not self.tmdb_api_key:
            self.logger.error("TMDB API key is not configured.")
            return None

        endpoint = f"{self.BASE_URL}/{path.lstrip('/')}"
        request_params = self._build_params(params)
        has_auth_header = bool(self.session.headers.get("Authorization"))
        has_api_key_param = bool(request_params.get("api_key"))

        self.logger.debug(
            "TMDB request auth attached. method=%s path=%s auth_mode=%s has_authorization_header=%s has_api_key_param=%s",
            method,
            path,
            self.auth_mode,
            has_auth_header,
            has_api_key_param,
        )

        try:
            response = self.session.request(
                method,
                endpoint,
                params=request_params,
                timeout=self.REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            status_code = e.response.status_code if getattr(e, "response", None) is not None else None
            self.logger.error(
                "TMDB request failed. method=%s path=%s status_code=%s auth_attached=%s error_type=%s",
                method,
                path,
                status_code,
                self._auth_attached(request_params),
                e.__class__.__name__,
            )
            return None

    def _request_json(self, method: str, path: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        response = self._request(method, path, params=params)
        if response is None:
            return None

        try:
            return response.json()
        except json.JSONDecodeError:
            self.logger.error("Error decoding JSON response from TMDB for path: %s", path)
            return None

    def get_media_detail(self, tmdb_id: str, media_type: str) -> Optional[Dict[str, Any]]:
        if not self.tmdb_api_key:
            self.logger.error("TMDB API key is not configured.")
            return None

        if media_type not in ['tv', 'movie']:
            self.logger.error(f"Invalid media type: {media_type}. Must be 'tv' or 'movie'")
            return None

        params = {
            "language": "en-US",
        }

        try:
            return self._request_json("GET", f"{media_type}/{tmdb_id}", params=params)
        except Exception as e:
            self.logger.exception(f"An unexpected error occurred while fetching {tmdb_id}: {e}")
            return None

    def lookup_media(self, query: str, media_type: str) -> Optional[dict]:
        """
        Searches for media (TV show or movie) using the TMDB search API.

        Args:
            query (str): The search query (title of movie or TV show)
            media_type (str): Type of media to search for ('tv' or 'movie')

        Returns:
            Optional[dict]: First search result containing media details or None if not found
                Returns fields like:
                - id: TMDB ID
                - title/name: Title of movie/show
                - overview: Plot description
                - first_air_date/release_date: Release date
                - poster_path: Poster image path
        """
        if not self.tmdb_api_key:
            self.logger.error("TMDB API key is not configured.")
            return None

        if media_type not in ['tv', 'movie']:
            self.logger.error(f"Invalid media type: {media_type}. Must be 'tv' or 'movie'")
            return None

        params = {
            "query": query,
            "language": "en-US",
            "page": 1,
            "include_adult": False
        }

        try:
            data = self._request_json("GET", f"search/{media_type}", params=params)
            if data is None:
                return None

            results = data.get('results', [])
            if not results:
                self.logger.warning(f"No {media_type} found for query: {query}")
                return None

            # Return the first result
            return results[0]

        except Exception as e:
            self.logger.exception(f"An unexpected error occurred while searching {media_type}: {e}")
            return None

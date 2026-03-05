"""
TMDB API client.

This module provides functionality for interacting with The Movie Database API.
"""

import os
import requests
from typing import List, Dict, Any, Optional

from src.config import TMDB_API_KEY, TMDB_BASE_URL
from src.utils.logger import get_logger

logger = get_logger(__name__)

def _is_debug_enabled() -> bool:
    return os.environ.get("SCANLY_DEBUG", "").lower() in ("1", "true", "yes", "on")

def _redact_params(params: Dict[str, Any]) -> Dict[str, Any]:
    redacted = dict(params or {})
    if 'api_key' in redacted and redacted['api_key']:
        redacted['api_key'] = '***REDACTED***'
    return redacted


class TMDB:
    """
    Client for The Movie Database API.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the TMDB client.
        
        Args:
            api_key: TMDB API key. If None, uses the value from settings.
        """
        self.api_key = api_key or TMDB_API_KEY
        self.base_url = TMDB_BASE_URL
        
        if not self.api_key:
            logger.warning("TMDB API key not set. API requests will fail.")
    
    def _request(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Make a request to the TMDB API.
        
        Args:
            endpoint: API endpoint
            params: Query parameters
            
        Returns:
            JSON response as a dictionary
        """
        url = f"{self.base_url}/{endpoint}"
        
        # Ensure params is a dictionary
        if params is None:
            params = {}
        
        # Add API key
        params['api_key'] = self.api_key
        debug_enabled = _is_debug_enabled()
        safe_params = _redact_params(params)
        if debug_enabled:
            print(f"[TMDB DEBUG] Request: GET {url} params={safe_params}")
            logger.debug(f"TMDB request GET {url} params={safe_params}")
        
        try:
            response = requests.get(url, params=params, timeout=10)
            if debug_enabled:
                print(f"[TMDB DEBUG] Response: status={response.status_code} endpoint={endpoint}")
                logger.debug(f"TMDB response status={response.status_code} endpoint={endpoint}")
            response.raise_for_status()  # Raise exception for non-200 status codes
            data = response.json()
            if debug_enabled:
                if isinstance(data, dict):
                    results_count = len(data.get("results", [])) if isinstance(data.get("results"), list) else "n/a"
                    keys_preview = list(data.keys())[:8]
                    print(f"[TMDB DEBUG] Response JSON keys={keys_preview} results_count={results_count}")
                    logger.debug(f"TMDB response json keys={keys_preview} results_count={results_count}")
                else:
                    print(f"[TMDB DEBUG] Response JSON type={type(data).__name__}")
                    logger.debug(f"TMDB response json type={type(data).__name__}")
            return data
        except requests.exceptions.RequestException as e:
            if debug_enabled:
                status = getattr(getattr(e, "response", None), "status_code", "n/a")
                body = ""
                if getattr(e, "response", None) is not None:
                    body = (e.response.text or "")[:500]
                print(f"[TMDB DEBUG] Error: endpoint={endpoint} status={status} error={e}")
                if body:
                    print(f"[TMDB DEBUG] Error body (truncated): {body}")
            logger.error(f"Error making TMDB API request to {endpoint}: {e}")
            return {"results": []}
    
    def search_movie(self, query: str, year: Optional[str] = None, limit: int = 3) -> List[Dict[str, Any]]:
        """
        Search for movies.
        
        Args:
            query: Search query
            year: Optional year to filter results
            limit: Maximum number of results to return
            
        Returns:
            List of movie results
        """
        params = {'query': query}
        if year:
            params['year'] = year
        results = self._request('search/movie', params)
        return results.get('results', [])[:limit]
    
    def search_tv(self, query: str, year: Optional[str] = None, limit: int = 3) -> List[Dict[str, Any]]:
        """
        Search for TV shows.
        
        Args:
            query: Search query
            year: Optional year to filter results (uses first_air_date_year)
            limit: Maximum number of results to return
            
        Returns:
            List of TV show results
        """
        params = {'query': query}
        if year:
            params['first_air_date_year'] = year
        results = self._request('search/tv', params)
        return results.get('results', [])[:limit]
    
    def get_movie_details(self, movie_id: int) -> Dict[str, Any]:
        """
        Get details for a movie.
        
        Args:
            movie_id: TMDB movie ID
            
        Returns:
            Movie details
        """
        return self._request(f'movie/{movie_id}')
    
    def get_tv_details(self, show_id: int) -> Dict[str, Any]:
        """
        Get details for a TV show.
        
        Args:
            show_id: TMDB show ID
            
        Returns:
            TV show details
        """
        return self._request(f'tv/{show_id}')
    
    def get_tv_season(self, show_id: int, season_number: int) -> Dict[str, Any]:
        """
        Get details for a TV season.
        
        Args:
            show_id: TMDB show ID
            season_number: Season number
            
        Returns:
            Season details
        """
        return self._request(f'tv/{show_id}/season/{season_number}')
    
    def get_movie_external_ids(self, movie_id: int) -> Dict[str, Any]:
        """
        Get external IDs for a movie.
        
        Args:
            movie_id: TMDB movie ID
            
        Returns:
            External IDs (IMDb, etc.)
        """
        return self._request(f'movie/{movie_id}/external_ids')
    
    def get_tv_external_ids(self, show_id: int) -> Dict[str, Any]:
        """
        Get external IDs for a TV show.
        
        Args:
            show_id: TMDB show ID
            
        Returns:
            External IDs (IMDb, TVDb, etc.)
        """
        return self._request(f'tv/{show_id}/external_ids')


def format_movie_result(movie: Dict[str, Any]) -> str:
    """
    Format a movie result for display to the user.
    
    Args:
        movie: Movie data from TMDB API
        
    Returns:
        Formatted string with movie information
    """
    title = movie.get("title", "Unknown Title")
    year = movie.get("release_date", "")[:4] if movie.get("release_date") else "Unknown Year"
    
    return f"{title} ({year})"


def format_tv_result(show: Dict[str, Any]) -> str:
    """
    Format a TV show result for display to the user.
    
    Args:
        show: TV show data from TMDB API
        
    Returns:
        Formatted string with TV show information
    """
    name = show.get("name", "Unknown Title")
    year = show.get("first_air_date", "")[:4] if show.get("first_air_date") else "Unknown Year"
    
    return f"{name} ({year})"

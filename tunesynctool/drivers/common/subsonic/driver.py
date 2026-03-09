from typing import List, Optional
import time

from tunesynctool.exceptions import PlaylistNotFoundException, ServiceDriverException, TrackNotFoundException
from tunesynctool.models import Playlist, Configuration, Track
from tunesynctool.drivers import ServiceDriver
from .mapper import SubsonicMapper

from libsonic.connection import Connection
from libsonic.errors import DataNotFoundError

class SubsonicDriver(ServiceDriver):
    """
    Subsonic service driver.
    
    Uses libsonic (py-sonic) as its backend:
    https://github.com/crustymonkey/py-sonic
    """
    
    def __init__(self, config: Configuration) -> None:
        super().__init__(
            service_name='subsonic',
            config=config,
            mapper=SubsonicMapper(),
            supports_musicbrainz_id_querying=True
        )

        self.__subsonic = self.__get_connection()

    def __get_connection(self) -> Connection:
        """Configures and returns a Connection object."""

        if not self._config.subsonic_base_url:
            raise ValueError('Subsonic base URL is required for this service to work but was not set.')
        elif not self._config.subsonic_port:
            raise ValueError('Subsonic port is required for this service to work but was not set.')
        elif not self._config.subsonic_username:
            raise ValueError('Subsonic username is required for this service to work but was not set.')
        elif not self._config.subsonic_password:
            raise ValueError('Subsonic password is required for this service to work but was not set.')

        return Connection(
            baseUrl=self._config.subsonic_base_url,
            port=self._config.subsonic_port,
            username=self._config.subsonic_username,
            password=self._config.subsonic_password,
            legacyAuth=self._config.subsonic_legacy_auth
        )
    
    def get_user_playlists(self, limit: int = 25) -> List['Playlist']:
        try:
            response = self.__subsonic.getPlaylists()
            fetched_playlists = response['playlists'].get('playlist', [])

            if isinstance(fetched_playlists, dict):
                fetched_playlists = [fetched_playlists]

            mapped_playlists = [self._mapper.map_playlist(playlist) for playlist in fetched_playlists[:limit]]

            for playlist in mapped_playlists:
                playlist.service_name = self.service_name

            return mapped_playlists
        except DataNotFoundError as e:
            raise PlaylistNotFoundException(e)
        except Exception as e:
            raise ServiceDriverException(e)
    
    def get_playlist_tracks(self, playlist_id: str, limit: int = 100) -> List['Track']:
        try:
            response = self.__subsonic.getPlaylist(
                pid=playlist_id
            )

            fetched_tracks = response['playlist'].get('entry', [])
            if limit > 0:
                fetched_tracks = fetched_tracks[:min(limit, len(fetched_tracks))]
        
            mapped_tracks = [self._mapper.map_track(track) for track in fetched_tracks]

            for track in mapped_tracks:
                track.service_name = self.service_name

            return mapped_tracks
        except DataNotFoundError as e:
            raise PlaylistNotFoundException(e)
        except Exception as e:
            raise ServiceDriverException(e)
        
    def create_playlist(self, name: str) -> 'Playlist':
        try:
            response = self.__subsonic.createPlaylist(
                name=name
            )

            return self._mapper.map_playlist(response['playlist'])
        except Exception as e:
            raise ServiceDriverException(e)
        
    def add_tracks_to_playlist(self, playlist_id: str, track_ids: List[str]) -> None:
        try:
            self.__subsonic.updatePlaylist(
                lid=playlist_id,
                songIdsToAdd=track_ids
            )
        except Exception as e:
            raise ServiceDriverException(e)

    def remove_tracks_from_playlist(self, playlist_id: str, track_ids: List[str]) -> None:
        if not track_ids:
            return

        try:
            # Get current playlist to find track indices
            response = self.__subsonic.getPlaylist(pid=playlist_id)
            current_tracks = response['playlist'].get('entry', [])
            
            # Find indices of tracks to remove
            indices_to_remove = []
            for i, track in enumerate(current_tracks):
                if track.get('id') in track_ids:
                    indices_to_remove.append(i)
            
            if indices_to_remove:
                self.__subsonic.updatePlaylist(
                    lid=playlist_id,
                    songIndexesToRemove=indices_to_remove
                )
        except Exception as e:
            raise ServiceDriverException(e)
        
    def get_random_track(self) -> Optional['Track']:
        try:
            response = self.__subsonic.getRandomSongs(
                size=1
            )
            fetched_tracks = response['randomSongs'].get('song', [])
            mapped_tracks = [self._mapper.map_track(track) for track in fetched_tracks]

            for track in mapped_tracks:
                track.service_name = self.service_name

            return mapped_tracks[0] if mapped_tracks else None
        except Exception as e:
            raise ServiceDriverException(e)
    
    def get_playlist(self, playlist_id: str) -> 'Playlist':
        try:
            response = self.__subsonic.getPlaylist(
                pid=playlist_id
            )
            return self._mapper.map_playlist(response['playlist'])
        except DataNotFoundError as e:
            raise PlaylistNotFoundException(e)
        except Exception as e:
            raise ServiceDriverException(e)
        
    def get_track(self, track_id: str) -> 'Track':
        try:
            response = self.__subsonic.getSong(
                id=track_id
            )
            return self._mapper.map_track(response['song'])
        except DataNotFoundError as e:
            raise TrackNotFoundException(e)
        except Exception as e:
            raise ServiceDriverException(e)
        
    def search_tracks(self, query: str, limit: int = 10) -> List['Track']:
        if not query or len(query) == 0:
            return []

        try:
            response = self.__subsonic.search2(
                query=query,
                artistCount=0,
                albumCount=0,
                songCount=limit,
            )

            fetched_tracks = response['searchResult2'].get('song', [])
            mapped_tracks = [self._mapper.map_track(track) for track in fetched_tracks]

            for track in mapped_tracks:
                track.service_name = self.service_name

            return mapped_tracks
        except Exception as e:
            raise ServiceDriverException(e)
    
    def search_tracks_with_octo_fiesta_retry(self, query: str, limit: int = 10) -> List['Track']:
        """
        Enhanced search that uses octo-fiesta's global search and retries to allow downloads.
        
        When octo-fiesta mode is enabled, this method will:
        1. Perform search3 (global search) which includes external provider results in octo-fiesta
        2. If results found from external providers, wait for octo-fiesta to download them
        3. Retry local search to find the downloaded tracks
        4. Return results once tracks are available or max retries reached
        
        :param query: Search query string
        :param limit: Maximum number of results to return
        :return: List of found tracks
        """
        if not self._config.subsonic_octo_fiesta_mode:
            return self.search_tracks(query=query, limit=limit)
        
        max_retries = self._config.subsonic_octo_fiesta_max_retries
        retry_delay = self._config.subsonic_octo_fiesta_retry_delay
        
        # First try: use search3 (global search) which in octo-fiesta includes external providers
        try:
            response = self.__subsonic.search3(
                query=query,
                artistCount=0,
                albumCount=0,
                songCount=limit,
            )
            
            # Check if we got results from search3
            fetched_tracks = response.get('searchResult3', {}).get('song', [])
            if fetched_tracks:
                mapped_tracks = [self._mapper.map_track(track) for track in fetched_tracks]
                for track in mapped_tracks:
                    track.service_name = self.service_name
                return mapped_tracks
        except Exception:
            pass
        
        # If search3 didn't work or no results, try search2 with retries
        for attempt in range(max_retries + 1):
            results = self.search_tracks(query=query, limit=limit)
            
            if results:
                return results
            
            if attempt < max_retries:
                time.sleep(retry_delay)
        
        return []
        
    def get_track_by_isrc(self, isrc: str) -> 'Track':
        raise NotImplementedError('Subsonic does not support fetching tracks by ISRC.')

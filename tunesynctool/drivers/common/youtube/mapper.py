from tunesynctool.drivers import ServiceMapper
from tunesynctool.models import Playlist, Track

from typing import List

class YouTubeMapper(ServiceMapper):
    """Maps Youtube API DTOs to internal models."""

    def map_playlist(self, data: dict) -> 'Playlist':  
        if isinstance(data, type(None)):
            raise ValueError('Input data cannot be None')
                
        return Playlist(
            name=data.get('title', None),
            description=data.get('description', None),
            service_id=data.get('id', data.get('playlistId', None)), # Youtube uses both 'id' and 'playlistId' keys depending on the endpoint
            is_public=data.get('privacy', None) == 'PUBLIC',
            service_name='youtube',
            service_data=data
        )

    def map_track(self, data: dict, additional_data: dict = {}) -> 'Track':
        if isinstance(data, type(None)) or isinstance(additional_data, type(None)):
            raise ValueError('Input data or additional_data cannot be None')
        
        # YouTube API returns different structures:
        # 1. Playlist tracks: {title, artists, videoId, album, duration, ...} directly
        # 2. Song details: {videoDetails: {title, videoId, lengthSeconds, ...}, ...}
        
        # Check if this is a song detail response (has videoDetails) or playlist track (direct fields)
        video_details: dict = data.get('videoDetails', {})
        is_song_detail = bool(video_details)
        
        # Extract metadata based on response structure
        if is_song_detail:
            # Song detail structure (from get_song)
            service_id = video_details.get('videoId', None)
            title = video_details.get('title', None)
            duration_seconds = int(video_details.get('lengthSeconds', None)) if video_details.get('lengthSeconds', None) else None
            
            # Artists come from additional_data for song details
            _raw_artists: List[dict] = additional_data.get('artists', [])
            album: dict = additional_data.get('album', {}) or {}
            release_year = int(additional_data.get('year')) if additional_data.get('year', None) else None
        else:
            # Playlist track structure (from get_playlist)
            service_id = data.get('videoId', None)
            title = data.get('title', None)
            
            # Duration can be in seconds or as duration_seconds
            duration = data.get('duration_seconds') or data.get('duration')
            if duration:
                # If duration is a string like "3:45", convert to seconds
                if isinstance(duration, str) and ':' in duration:
                    parts = duration.split(':')
                    if len(parts) == 2:
                        duration_seconds = int(parts[0]) * 60 + int(parts[1])
                    elif len(parts) == 3:
                        duration_seconds = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
                    else:
                        duration_seconds = None
                else:
                    duration_seconds = int(duration) if duration else None
            else:
                duration_seconds = None
            
            # Artists come from data for playlist tracks
            _raw_artists: List[dict] = data.get('artists', [])
            album: dict = data.get('album', {}) or {}
            release_year = int(data.get('year')) if data.get('year', None) else None
        
        # Extract artist names
        _artist_names = [artist.get('name', None) for artist in _raw_artists] if _raw_artists else []
        
        album_name = album.get('name', None)
        primary_artist = _artist_names[0] if len(_artist_names) > 0 else None
        
        track_number = None # Youtube does not provide track numbers as far as I know
        isrc = None # Youtube does not provide ISRCs as far as I know
        
        additional_artists = []
        if len(_artist_names) > 1:
            additional_artists = [artist for artist in _artist_names[1:]]
        
        return Track(
            title=title,
            album_name=album_name,
            primary_artist=primary_artist,
            additional_artists=additional_artists,
            duration_seconds=duration_seconds,
            track_number=track_number,
            release_year=release_year,
            isrc=isrc,
            service_id=service_id,
            service_name='youtube',
            service_data={
                'track': data,
                'search': additional_data
            }
        )

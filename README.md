# tunesynctool (formerly Navify)

A Python package and CLI to transfer music between your local/commercial streaming services. Supports intelligent track matching across platforms.

## Supported Services

- **Spotify** - Commercial streaming service
- **Deezer** - Commercial streaming service
- **YouTube Music** - Google's music streaming platform
- **Subsonic-compatible servers** - Navidrome, Airsonic, Subsonic, etc.
- **[octo-fiesta](https://github.com/V1ck3s/octo-fiesta)** - Subsonic proxy with automatic music provider integration

Support for other services will be added in the future.

## Installation

Install the latest release via PyPI:

```bash
pip install tunesynctool
```

## Quick Start

### Basic Transfer (YouTube → Subsonic)

```bash
tunesynctool \
  --subsonic-base-url "http://IP" \
  --subsonic-port "4533" \
  --subsonic-username "your_username" \
  --subsonic-password "your_password" \
  --youtube-request-headers "your_headers" \
  transfer --from "youtube" --to "subsonic" "PLAYLIST_ID"
```

### With octo-fiesta Integration

When using [octo-fiesta](https://github.com/V1ck3s/octo-fiesta), enable automatic download mode to let octo-fiesta fetch missing tracks from streaming providers:

```bash
tunesynctool \
  --subsonic-base-url "http://IP" \
  --subsonic-port "5274" \
  --subsonic-username "your_username" \
  --subsonic-password "your_password" \
  --youtube-request-headers "your_headers" \
  --subsonic-octo-fiesta-mode \
  transfer --from "youtube" --to "subsonic" "PLAYLIST_ID"
```

**octo-fiesta mode features:**
- Automatically triggers downloads for missing tracks
- Retries searches to find newly downloaded tracks
- Configurable retry delays and attempts
- Works with Deezer, Qobuz, and SquidWTF providers

**Optional parameters:**
- `--subsonic-octo-fiesta-retry-delay <seconds>` - Delay between retries (default: 3)
- `--subsonic-octo-fiesta-max-retries <count>` - Maximum retry attempts (default: 3)

### Preview Mode

Test transfers without making changes by using the `--preview` flag:

```bash
tunesynctool ... transfer --from "youtube" --to "subsonic" --preview "PLAYLIST_ID"
```

## Configuration

Configuration options can be loaded from environment variables or specified via CLI flags.

### Environment Variables

```bash
export SUBSONIC_BASE_URL="http://IP"
export SUBSONIC_PORT="4533"
export SUBSONIC_USERNAME="your_username"
export SUBSONIC_PASSWORD="your_password"
export SUBSONIC_OCTO_FIESTA_MODE="true"
export YOUTUBE_REQUEST_HEADERS="your_headers"
```

For more configuration options, [check the wiki](https://github.com/WilliamNT/tunesynctool/wiki/Configuration).

### YouTube Request Headers

YouTube Music requires authentication headers to access your playlists. You need to extract these headers from your browser while logged into YouTube Music.

**Required headers format:**

The `--youtube-request-headers` parameter accepts headers in the following format (paste them line-by-line):

```
accept: */*
accept-encoding: gzip, deflate
authorization: SAPISIDHASH 1234567890_abcdef...
content-encoding: gzip
content-type: application/json
cookie: VISITOR_INFO1_LIVE=...; SID=...; HSID=...; SSID=...; APISID=...; SAPISID=...
origin: https://music.youtube.com
user-agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:88.0) Gecko/20100101 Firefox/88.0
x-goog-authuser: 0
x-goog-visitor-id: ID
x-origin: https://music.youtube.com
```
If you use PowerShell, you can use the following command:
```powershell
tunesynctool `
  --subsonic-base-url "IP" `
  --subsonic-port "5274" `
  --subsonic-username "your_username" `
  --subsonic-password "your_password" `
  --youtube-request-headers "accept: */*
accept-encoding: gzip, deflate
authorization: YOUR_AUTHORIZATION_HEADER
cookie: YOUR_COOKIE
x-goog-authuser: YOUR_AUTHUSER
x-goog-visitor-id: YOUR_VISITOR_ID" `
  --subsonic-octo-fiesta-mode `
  transfer --from "youtube" --to "subsonic" --preview "PLAYLIST_ID"
```


**How to obtain headers:**

1. Open [YouTube Music](https://music.youtube.com) in your browser
2. Make sure you're logged in
3. Open Developer Tools (F12)
4. Go to the **Network** tab
5. Navigate to any playlist or browse page
6. Find a POST request by filtering `browse`
7. Paste the headers and use them directly with the `--youtube-request-headers` flag

**Note:** Headers expire after some time. If you get authentication errors, refresh your headers.

Alternatively, you can save headers to a JSON file (see `browser.json` example in the repository) and reference it in your code.

## Features

- **Intelligent Track Matching** - Uses multiple strategies including ISRC, MusicBrainz ID, and fuzzy text matching
- **Multi-Provider Support** - Transfer playlists between different streaming services
- **octo-fiesta Integration** - Automatic downloads from streaming providers when tracks aren't in your local library
- **Playlist Synchronization** - Keep playlists in sync across services
- **Preview Mode** - Test transfers before committing changes

## FAQ

### Is there a way to use tunesynctool from the CLI?
Yes, the CLI is the primary interface. See examples above or check the [wiki](https://github.com/WilliamNT/tunesynctool/wiki).

### Does this package offer functionality to download or stream music?
**No**, tunesynctool only transfers playlist metadata and matches tracks. Use official clients or [octo-fiesta](https://github.com/V1ck3s/octo-fiesta) for downloads.

### How does matching work?
Tunesynctool uses multiple matching strategies in order of reliability:
1. ISRC (International Standard Recording Code)
2. MusicBrainz ID
3. Text-based matching (artist + title with fuzzy matching)
4. Lenient matching with lower thresholds

Learn more about matching [here](https://github.com/WilliamNT/tunesynctool/wiki/Track-matching).

### What is octo-fiesta and why should I use it?
[octo-fiesta](https://github.com/V1ck3s/octo-fiesta) is a Subsonic API proxy that automatically downloads tracks from streaming providers (Deezer, Qobuz, SquidWTF) when they're not in your local library. When used with tunesynctool's `--subsonic-octo-fiesta-mode` flag, it enables automatic playlist transfers even when tracks don't exist locally.

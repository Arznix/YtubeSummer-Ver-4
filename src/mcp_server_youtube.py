import feedparser
import requests
import time
import os
import threading
import itertools
import random
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
import re
from xml.etree import ElementTree as ET


USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
]


class RateLimiter:
    def __init__(self, min_interval: float = 60.0, max_interval: float = 240.0):
        self.min_interval = min_interval
        self.max_interval = max_interval
        self._last_request = 0.0
        self._lock = threading.Lock()

    def wait(self):
        with self._lock:
            now = time.time()
            elapsed = now - self._last_request
            target = random.uniform(self.min_interval, self.max_interval)
            if elapsed < target:
                wait = target - elapsed
                time.sleep(wait)
            self._last_request = time.time()


class ProxyRotator:
    def __init__(self, proxy_list: Optional[List[str]] = None):
        self._proxies = proxy_list or []
        self._cycle = itertools.cycle(self._proxies) if self._proxies else None

    def get_proxies(self) -> Optional[Dict[str, str]]:
        if not self._cycle:
            return None
        proxy = next(self._cycle)
        return {"http": proxy, "https": proxy}


class YouTubeMCPServer:
    """YouTube MCP Server for RSS feed parsing and transcript extraction."""
    
    def __init__(self, timeout: int = 30, request_delay_min: float = 60.0, request_delay_max: float = 240.0, proxy_list: Optional[List[str]] = None, api_key: str = ""):
        """
        Initialize YouTube MCP Server.

        Args:
            timeout: HTTP request timeout in seconds
            request_delay_min: Minimum seconds between YouTube requests
            request_delay_max: Maximum seconds between YouTube requests (random jitter)
            proxy_list: List of proxy URLs to rotate through
            api_key: YouTube Data API v3 key (optional, enables API-based video fetching)
        """
        self.timeout = timeout
        self.request_delay_min = request_delay_min
        self.request_delay_max = request_delay_max
        self.api_key = api_key
        self.logger = logging.getLogger(__name__)
        self.rate_limiter = RateLimiter(request_delay_min, request_delay_max)
        self.proxy_rotator = ProxyRotator(proxy_list)
        self._ua_cycle = itertools.cycle(USER_AGENTS)
        self._proxy_fallback = False

        # YouTube RSS feed base URL
        self.rss_base_url = "https://www.youtube.com/feeds/videos.xml"

        # YouTube video URL pattern
        self.video_url_pattern = re.compile(
            r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})'
        )

    def _get_headers(self) -> Dict[str, str]:
        return {"User-Agent": next(self._ua_cycle)}

    def _request_url(self, url: str, method: str = "GET", **kwargs) -> requests.Response:
        self.rate_limiter.wait()
        if "headers" not in kwargs:
            kwargs["headers"] = self._get_headers()
        if "timeout" not in kwargs:
            kwargs["timeout"] = self.timeout

        max_retries = 3
        attempt = 0
        has_proxies = bool(self.proxy_rotator._proxies)
        local_kwargs = kwargs.copy()

        while attempt < max_retries:
            try:
                proxies = None
                if self._proxy_fallback:
                    proxies = self.proxy_rotator.get_proxies()
                if proxies:
                    local_kwargs["proxies"] = proxies
                elif "proxies" in local_kwargs:
                    local_kwargs.pop("proxies", None)

                if method == "GET":
                    response = requests.get(url, **local_kwargs)
                elif method == "POST":
                    response = requests.post(url, **local_kwargs)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")

                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 30))
                    self.logger.warning(
                        f"Rate limited (429) on {url}. Waiting {retry_after}s "
                        f"(attempt {attempt+1}/{max_retries})"
                    )
                    attempt += 1
                    if attempt < max_retries:
                        time.sleep(retry_after)
                        continue
                    if not self._proxy_fallback and has_proxies:
                        self._proxy_fallback = True
                        attempt = 0
                        self.logger.info("Falling back to proxy rotation after repeated 429s")
                        continue
                    raise RuntimeError(f"Rate limited after {max_retries} attempts on {url}")

                response.raise_for_status()
                return response

            except (requests.RequestException, ConnectionError) as e:
                attempt += 1
                if attempt < max_retries:
                    backoff = (2 ** (attempt - 1)) * 5 + random.uniform(0, 2)
                    self.logger.warning(
                        f"Request failed ({e}). Retrying in {backoff:.0f}s "
                        f"(attempt {attempt}/{max_retries})"
                    )
                    time.sleep(backoff)
                elif not self._proxy_fallback and has_proxies:
                    self._proxy_fallback = True
                    attempt = 0
                    self.logger.info(f"Falling back to proxy rotation after: {e}")
                else:
                    self.logger.error(f"Request to {url} failed after all attempts: {e}")
                    raise

        raise RuntimeError(f"Failed to fetch {url} after all attempts")

    @staticmethod
    def _channel_id_to_playlist_id(channel_id: str) -> str:
        """Convert a YouTube channel ID (UC...) to its uploads playlist ID (UU...).
        The uploads playlist contains all public videos from the channel.
        """
        if channel_id.startswith("UC"):
            return "UU" + channel_id[2:]
        return channel_id

    def fetch_latest_videos_from_api(self, channel_id: str) -> Optional[List[Dict[str, Any]]]:
        """
        Fetch latest videos using the YouTube Data API v3 playlistItems endpoint.

        Uses the uploads playlist ID derived from the channel ID (UC -> UU).
        Requires a valid YOUTUBE_API_KEY. Returns None if no key is configured.

        Args:
            channel_id: YouTube channel ID (UC prefix)

        Returns:
            List of video info dicts, or None if API key is missing
        """
        if not self.api_key:
            return None

        playlist_id = self._channel_id_to_playlist_id(channel_id)
        url = ("https://www.googleapis.com/youtube/v3/playlistItems"
               f"?part=snippet&playlistId={playlist_id}&maxResults=50&key={self.api_key}")

        self.logger.info(f"Fetching videos from API for channel {channel_id}")
        try:
            resp = self._request_url(url)
            data = resp.json()
        except Exception as e:
            self.logger.warning(f"YouTube API request failed for {channel_id}: {e}")
            return []

        items = data.get('items', [])
        if not items:
            self.logger.info(f"No videos returned by API for channel {channel_id}")
            return []

        videos = []
        for item in items:
            snippet = item.get('snippet', {})
            vid = snippet.get('resourceId', {}).get('videoId', '')
            if not vid:
                continue
            title = snippet.get('title', 'Unknown Title')
            published = snippet.get('publishedAt', '')
            thumbnails = snippet.get('thumbnails', {})
            thumb = ''
            for quality in ('maxres', 'high', 'medium', 'default'):
                if quality in thumbnails:
                    thumb = thumbnails[quality].get('url', '')
                    break
            channel_name = snippet.get('channelTitle', '') or channel_id
            description = snippet.get('description', '')
            videos.append({
                'video_id': vid, 'title': title,
                'channel': channel_name,
                'published': published, 'updated': '',
                'link': f'https://www.youtube.com/watch?v={vid}',
                'summary': description,
                'media_thumbnail': thumb,
                'yt_channel_id': channel_id
            })

        self.logger.info(f"API returned {len(videos)} videos for channel {channel_id}")
        return videos

    def _scrape_channel_videos(self, channel_id: str) -> List[Dict[str, Any]]:
        """Fallback: scrape channel videos page for video IDs, titles, and thumbnails.

        Extracts data from ytInitialData JSON embedded in the page HTML.
        Handles YouTube's new lockupViewModel format.
        """
        try:
            page_url = f"https://www.youtube.com/channel/{channel_id}/videos"
            self.logger.info(f"Scraping channel videos page: {channel_id}")
            resp = self._request_url(page_url)
            text = resp.text

            m = re.search(r'ytInitialData\s*=\s*(\{.+?\});', text, re.DOTALL)
            if not m:
                return self._scrape_channel_videos_fallback(text, channel_id)

            import json
            data = json.loads(m.group(1))

            videos = []
            try:
                br = data['contents']['twoColumnBrowseResultsRenderer']
                # Find the Videos tab (looks for richGridRenderer with lockupViewModels)
                for tab in br.get('tabs', []):
                    content = tab.get('tabRenderer', {}).get('content', {})
                    rg = content.get('richGridRenderer', {})
                    if not rg:
                        continue
                    for item in rg.get('contents', []):
                        ri = item.get('richItemRenderer', {})
                        if not ri:
                            continue
                        lockup = ri.get('content', {}).get('lockupViewModel', {})
                        if not lockup:
                            continue
                        if lockup.get('contentType') != 'LOCKUP_CONTENT_TYPE_VIDEO':
                            continue
                        vid = lockup.get('contentId', '')
                        if not vid or len(vid) != 11:
                            continue
                        meta = lockup.get('metadata', {}).get('lockupMetadataViewModel', {})
                        title = meta.get('title', {}).get('content', '') or 'Unknown Title'
                        # Extract date from metadata rows
                        date_str = ''
                        meta_rows = (meta.get('metadata', {})
                                     .get('contentMetadataViewModel', {})
                                     .get('metadataRows', []))
                        for row in meta_rows:
                            parts = row.get('metadataParts', [])
                            if len(parts) > 1:
                                date_str = parts[1].get('text', {}).get('content', '')
                                break
                        # Thumbnail
                        thumb = ''
                        sources = (lockup.get('contentImage', {})
                                   .get('thumbnailViewModel', {})
                                   .get('image', {})
                                   .get('sources', []))
                        if sources:
                            thumb = sources[0].get('url', '')
                        videos.append({
                            'video_id': vid, 'title': title,
                            'channel': channel_id,
                            'published': date_str, 'updated': '',
                            'link': f'https://www.youtube.com/watch?v={vid}',
                            'summary': '',
                            'media_thumbnail': thumb,
                            'yt_channel_id': channel_id
                        })
            except (KeyError, IndexError, TypeError) as exc:
                self.logger.warning(f"ytInitialData navigation failed: {exc}")

            if not videos:
                return self._scrape_channel_videos_fallback(text, channel_id)

            self.logger.info(f"Scraped {len(videos)} videos for channel {channel_id}")
            return videos[:50]
        except Exception as e:
            self.logger.error(f"Error scraping channel {channel_id}: {e}")
            return self._scrape_channel_videos_fallback(text if 'text' in dir() else '', channel_id)

    def _scrape_channel_videos_fallback(self, text: str, channel_id: str) -> List[Dict[str, Any]]:
        """Fallback for _scrape_channel_videos — extract video IDs from raw HTML."""
        video_ids = list(dict.fromkeys(
            re.findall(r'"videoId":"([a-zA-Z0-9_-]{11})"', text)
        ))
        return [{
            'video_id': vid, 'title': 'Unknown Title',
            'channel': channel_id, 'published': '', 'updated': '',
            'link': f'https://www.youtube.com/watch?v={vid}',
            'summary': '',
            'media_thumbnail': f'https://i.ytimg.com/vi/{vid}/hqdefault.jpg',
            'yt_channel_id': channel_id
        } for vid in video_ids[:50]]

    def fetch_latest_videos_from_rss(self, channel_id: str) -> List[Dict[str, Any]]:
        """
        Fetch latest videos from YouTube channel RSS feed, with HTML scraping fallback.

        Args:
            channel_id: YouTube channel ID (UC prefix)

        Returns:
            List of video information dictionaries
        """
        try:
            feed_url = f"{self.rss_base_url}?channel_id={channel_id}"
            self.logger.info(f"Fetching RSS feed for channel: {channel_id}")

            response = self._request_url(feed_url)
            feed = feedparser.parse(response.text)

            if feed.bozo and not feed.entries:
                self.logger.error(f"Error parsing RSS feed for channel {channel_id}: {feed.bozo_exception}")
                return self._scrape_channel_videos(channel_id)
            
            videos = []
            
            for entry in feed.entries:
                try:
                    # Extract video ID from link
                    video_id = self._extract_video_id_from_url(entry.get('link', ''))
                    if not video_id:
                        continue
                    
                    # Extract video information
                    video_info = {
                        'video_id': video_id,
                        'title': entry.get('title', 'Unknown Title'),
                        'channel': self._extract_channel_name_from_feed(feed),
                        'published': entry.get('published', ''),
                        'updated': entry.get('updated', ''),
                        'link': entry.get('link', ''),
                        'summary': entry.get('summary', ''),
                        'media_thumbnail': self._extract_thumbnail(entry),
                        'yt_channel_id': channel_id
                    }
                    
                    videos.append(video_info)
                    
                except Exception as e:
                    self.logger.warning(f"Error processing entry: {e}")
                    continue
            
            self.logger.info(f"Found {len(videos)} videos for channel {channel_id}")
            return videos
            
        except Exception as e:
            self.logger.warning(f"RSS feed failed for channel {channel_id}, falling back to scrape: {e}")
            return self._scrape_channel_videos(channel_id)
    
    def _extract_video_id_from_url(self, url: str) -> Optional[str]:
        """
        Extract video ID from YouTube URL.
        
        Args:
            url: YouTube video URL
            
        Returns:
            Video ID or None if not found
        """
        match = self.video_url_pattern.search(url)
        if match:
            return match.group(1)
        
        # Try to extract from other URL formats
        if 'youtube.com' in url or 'youtu.be' in url:
            # Simple extraction for other formats
            if 'v=' in url:
                return url.split('v=')[1].split('&')[0]
        
        return None
    
    def _extract_channel_name_from_feed(self, feed: Any) -> str:
        """
        Extract channel name from feed data.
        
        Args:
            feed: Parsed feed object
            
        Returns:
            Channel name or 'Unknown Channel'
        """
        try:
            # Try to get from feed title
            if hasattr(feed, 'feed') and hasattr(feed.feed, 'title'):
                return feed.feed.title
            
            # Try to get from first entry
            if feed.entries:
                entry = feed.entries[0]
                if hasattr(entry, 'author'):
                    return entry.author
            
            return 'Unknown Channel'
            
        except Exception:
            return 'Unknown Channel'
    
    def _extract_thumbnail(self, entry: Any) -> Optional[str]:
        """
        Extract thumbnail URL from feed entry.
        
        Args:
            entry: Feed entry object
            
        Returns:
            Thumbnail URL or None
        """
        try:
            # Look for media_thumbnail
            if hasattr(entry, 'media_thumbnail'):
                thumbnails = entry.media_thumbnail
                if thumbnails and len(thumbnails) > 0:
                    return thumbnails[0].get('url', None)
            
            # Look for media_content
            if hasattr(entry, 'media_content'):
                media = entry.media_content
                for item in media:
                    if item.get('medium') == 'image':
                        return item.get('url', None)
            
            return None
            
        except Exception:
            return None
    
    def get_video_transcript(self, video_id: str, languages: List[str] = None) -> Optional[str]:
        """
        Extract video transcript using youtube-transcript-api.

        Args:
            video_id: YouTube video ID
            languages: List of preferred languages (default: ['en'])

        Returns:
            Transcript text or None if not available
        """
        if languages is None:
            languages = ['en']

        try:
            from youtube_transcript_api import YouTubeTranscriptApi
        except ImportError:
            self.logger.error("youtube-transcript-api not installed. Install with: pip install youtube-transcript-api")
            return None

        self.logger.info(f"Fetching transcript for video: {video_id}")
        self.rate_limiter.wait()

        has_proxies = bool(self.proxy_rotator._proxies)
        _saved_http = None
        _saved_https = None

        def _apply_proxy_env():
            nonlocal _saved_http, _saved_https
            _saved_http = os.environ.pop("HTTP_PROXY", None)
            _saved_https = os.environ.pop("HTTPS_PROXY", None)
            if self._proxy_fallback:
                proxies = self.proxy_rotator.get_proxies()
                if proxies:
                    if proxies.get("http"):
                        os.environ["HTTP_PROXY"] = proxies["http"]
                    if proxies.get("https"):
                        os.environ["HTTPS_PROXY"] = proxies["https"]

        def _restore_proxy_env():
            nonlocal _saved_http, _saved_https
            if _saved_http is not None:
                os.environ["HTTP_PROXY"] = _saved_http
            elif "HTTP_PROXY" in os.environ:
                os.environ.pop("HTTP_PROXY", None)
            if _saved_https is not None:
                os.environ["HTTPS_PROXY"] = _saved_https
            elif "HTTPS_PROXY" in os.environ:
                os.environ.pop("HTTPS_PROXY", None)

        def _do_fetch(api, vid, langs):
            transcript = api.fetch(vid, languages=langs)
            return ' '.join([snippet.text for snippet in transcript.snippets])

        try:
            _apply_proxy_env()

            max_retries = 3
            attempt = 0

            while attempt < max_retries:
                try:
                    ytt_api = YouTubeTranscriptApi()
                    transcript_text = _do_fetch(ytt_api, video_id, languages)
                    self.logger.info(f"Successfully fetched transcript for video {video_id}")
                    return transcript_text

                except Exception as e:
                    error_str = str(e).lower()
                    is_rate_limit = "429" in error_str or "too many requests" in error_str
                    attempt += 1

                    if attempt < max_retries:
                        backoff = (2 ** (attempt - 1)) * 10 + random.uniform(0, 5)
                        reason = "rate limited" if is_rate_limit else str(e)
                        self.logger.warning(
                            f"Transcript {reason} for {video_id}. "
                            f"Retrying in {backoff:.0f}s (attempt {attempt}/{max_retries})"
                        )
                        time.sleep(backoff)
                        continue

                    # All retries exhausted — fall back to proxies if available
                    if not self._proxy_fallback and has_proxies:
                        self._proxy_fallback = True
                        attempt = 0
                        self.logger.info(f"Falling back to proxy rotation for transcript: {video_id}")
                        _restore_proxy_env()
                        _apply_proxy_env()
                        continue

                    self.logger.warning(f"Transcript fetch failed for {video_id} after all attempts: {e}")

                    # Final fallback: try listing available transcripts
                    try:
                        ytt_api = YouTubeTranscriptApi()
                        transcript_list = ytt_api.list(video_id)
                        for transcript in transcript_list:
                            try:
                                fetched = transcript.fetch()
                                text = ' '.join([s.text for s in fetched.snippets])
                                self.logger.info(f"Fetched transcript in alternative language for {video_id}")
                                return text
                            except Exception:
                                continue
                        self.logger.warning(f"No transcript available for {video_id}")
                        return None
                    except Exception as inner_e:
                        self.logger.error(f"Error listing transcripts for {video_id}: {inner_e}")
                        return None

            return None

        except Exception as e:
            self.logger.error(f"Unexpected error fetching transcript for video {video_id}: {e}")
            return None
        finally:
            _restore_proxy_env()
    
    def get_video_metadata(self, video_id: str) -> Optional[Dict[str, Any]]:
        """
        Get video metadata from YouTube page.

        Args:
            video_id: YouTube video ID

        Returns:
            Video metadata dictionary or None
        """
        try:
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            response = self._request_url(video_url)
            
            # Extract basic metadata from page
            # Note: This is a simple extraction and may not work for all videos
            # For production use, consider using YouTube Data API or yt-dlp
            
            metadata = {
                'video_id': video_id,
                'url': video_url,
                'title': self._extract_title_from_html(response.text),
                'description': self._extract_description_from_html(response.text),
                'duration': self._extract_duration_from_html(response.text),
                'view_count': self._extract_view_count_from_html(response.text),
                'like_count': self._extract_like_count_from_html(response.text),
                'channel_name': self._extract_channel_from_html(response.text)
            }
            
            return metadata
            
        except Exception as e:
            self.logger.error(f"Error fetching metadata for video {video_id}: {e}")
            return None
    
    def _extract_title_from_html(self, html: str) -> Optional[str]:
        """Extract title from YouTube page HTML."""
        try:
            # Simple regex extraction
            title_match = re.search(r'"title":"([^"]*)"', html)
            if title_match:
                return title_match.group(1)
            
            # Alternative pattern
            title_match = re.search(r'<title>([^<]*)</title>', html)
            if title_match:
                return title_match.group(1).replace(' - YouTube', '')
            
            return None
            
        except Exception:
            return None
    
    def _extract_description_from_html(self, html: str) -> Optional[str]:
        """Extract description from YouTube page HTML."""
        try:
            # Simple regex extraction
            desc_match = re.search(r'"shortDescription":"([^"]*)"', html)
            if desc_match:
                description = desc_match.group(1)
                # Unescape JSON string
                description = description.replace('\\n', '\n').replace('\\"', '"')
                return description
            
            return None
            
        except Exception:
            return None
    
    def _extract_duration_from_html(self, html: str) -> Optional[str]:
        """Extract duration from YouTube page HTML."""
        try:
            # Look for duration in metadata
            duration_match = re.search(r'"lengthSeconds":"(\d+)"', html)
            if duration_match:
                seconds = int(duration_match.group(1))
                minutes = seconds // 60
                remaining_seconds = seconds % 60
                return f"{minutes}:{remaining_seconds:02d}"
            
            return None
            
        except Exception:
            return None
    
    def _extract_view_count_from_html(self, html: str) -> Optional[str]:
        """Extract view count from YouTube page HTML."""
        try:
            view_match = re.search(r'"viewCount":"(\d+)"', html)
            if view_match:
                return view_match.group(1)
            
            return None
            
        except Exception:
            return None
    
    def _extract_like_count_from_html(self, html: str) -> Optional[str]:
        """Extract like count from YouTube page HTML."""
        try:
            like_match = re.search(r'"likeCount":"(\d+)"', html)
            if like_match:
                return like_match.group(1)
            
            return None
            
        except Exception:
            return None
    
    def _extract_channel_from_html(self, html: str) -> Optional[str]:
        """Extract channel name from YouTube page HTML."""
        try:
            channel_match = re.search(r'"ownerChannelName":"([^"]*)"', html)
            if channel_match:
                return channel_match.group(1)
            
            return None
            
        except Exception:
            return None
    
    def find_channel_id(self, channel_handle: str) -> Optional[str]:
        """
        Find channel ID from channel handle.

        Args:
            channel_handle: YouTube channel handle (e.g., '@channelname')

        Returns:
            Channel ID or None if not found
        """
        try:
            if channel_handle.startswith('@'):
                channel_handle = channel_handle[1:]

            channel_url = f"https://www.youtube.com/@{channel_handle}"
            response = self._request_url(channel_url)
            
            # Extract channel ID from page
            channel_id_match = re.search(r'"channelId":"([^"]*)"', response.text)
            if channel_id_match:
                return channel_id_match.group(1)
            
            # Alternative pattern
            channel_id_match = re.search(r'channel_id=([a-zA-Z0-9_-]+)', response.text)
            if channel_id_match:
                return channel_id_match.group(1)
            
            self.logger.warning(f"Could not find channel ID for handle: {channel_handle}")
            return None
            
        except Exception as e:
            self.logger.error(f"Error finding channel ID for handle {channel_handle}: {e}")
            return None
    
    def test_connection(self) -> bool:
        """
        Test connection to YouTube.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            test_url = "https://www.youtube.com/feeds/videos.xml?channel_id=UC-lHJZR3Gqxm24_Vd_AJ5Yw"
            self._request_url(test_url)
            self.logger.info("YouTube connection test successful")
            return True
        except Exception as e:
            self.logger.error(f"YouTube connection test failed: {e}")
            return False
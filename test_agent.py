#!/usr/bin/env python3
"""
Automated tests for YouTube Summarizer pipeline.

This module contains tests for the core functionality including
state management, YouTube RSS parsing, Ollama integration,
and Telegram notifications.
"""

import unittest
import tempfile
import os
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, PropertyMock
from datetime import datetime, timedelta

# Add src directory to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent / "src"))

from state_manager import StateManager
from config import Config, ConfigError


class TestStateManager(unittest.TestCase):
    """Tests for StateManager class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = tempfile.mkdtemp()
        self.db_path = Path(self.test_dir) / "test.db"
        self.state_manager = StateManager(self.db_path)
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_initialization(self):
        """Test database initialization."""
        self.assertTrue(self.db_path.exists())
        
        # Check table exists
        import sqlite3
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='videos'")
            result = cursor.fetchone()
            self.assertIsNotNone(result)
    
    def test_add_video(self):
        """Test adding a video to the database."""
        result = self.state_manager.add_video(
            video_id="test123",
            channel_name="Test Channel",
            video_title="Test Video",
            published_timestamp="2024-01-01T00:00:00"
        )
        
        self.assertTrue(result)
        self.assertTrue(self.state_manager.video_exists("test123"))
    
    def test_add_duplicate_video(self):
        """Test adding a duplicate video."""
        # Add first time
        self.state_manager.add_video(
            video_id="test123",
            channel_name="Test Channel",
            video_title="Test Video",
            published_timestamp="2024-01-01T00:00:00"
        )
        
        # Try to add again
        result = self.state_manager.add_video(
            video_id="test123",
            channel_name="Test Channel",
            video_title="Test Video",
            published_timestamp="2024-01-01T00:00:00"
        )
        
        self.assertFalse(result)
    
    def test_update_status(self):
        """Test updating video status."""
        # Add video
        self.state_manager.add_video(
            video_id="test123",
            channel_name="Test Channel",
            video_title="Test Video",
            published_timestamp="2024-01-01T00:00:00"
        )
        
        # Update status
        result = self.state_manager.update_video_status("test123", "PROCESSING")
        self.assertTrue(result)
        
        # Verify status
        video = self.state_manager.get_video("test123")
        self.assertEqual(video["summary_status"], "PROCESSING")
    
    def test_get_video(self):
        """Test getting video information."""
        # Add video
        self.state_manager.add_video(
            video_id="test123",
            channel_name="Test Channel",
            video_title="Test Video",
            published_timestamp="2024-01-01T00:00:00"
        )
        
        # Get video
        video = self.state_manager.get_video("test123")
        self.assertIsNotNone(video)
        self.assertEqual(video["video_id"], "test123")
        self.assertEqual(video["channel_name"], "Test Channel")
        self.assertEqual(video["video_title"], "Test Video")
    
    def test_get_nonexistent_video(self):
        """Test getting a video that doesn't exist."""
        video = self.state_manager.get_video("nonexistent")
        self.assertIsNone(video)
    
    def test_get_videos_by_status(self):
        """Test getting videos by status."""
        # Add videos with different statuses
        self.state_manager.add_video(
            video_id="test1",
            channel_name="Channel 1",
            video_title="Video 1",
            published_timestamp="2024-01-01T00:00:00"
        )
        
        self.state_manager.add_video(
            video_id="test2",
            channel_name="Channel 2",
            video_title="Video 2",
            published_timestamp="2024-01-02T00:00:00"
        )
        
        # Update one video status
        self.state_manager.update_video_status("test1", "COMPLETED")
        
        # Get by status
        pending_videos = self.state_manager.get_videos_by_status("PENDING")
        completed_videos = self.state_manager.get_videos_by_status("COMPLETED")
        
        self.assertEqual(len(pending_videos), 1)
        self.assertEqual(len(completed_videos), 1)
        self.assertEqual(pending_videos[0]["video_id"], "test2")
        self.assertEqual(completed_videos[0]["video_id"], "test1")
    
    def test_delete_video(self):
        """Test deleting a video."""
        # Add video
        self.state_manager.add_video(
            video_id="test123",
            channel_name="Test Channel",
            video_title="Test Video",
            published_timestamp="2024-01-01T00:00:00"
        )
        
        # Delete video
        result = self.state_manager.delete_video("test123")
        self.assertTrue(result)
        self.assertFalse(self.state_manager.video_exists("test123"))
    
    def test_statistics(self):
        """Test getting database statistics."""
        # Add some videos
        for i in range(5):
            self.state_manager.add_video(
                video_id=f"test{i}",
                channel_name=f"Channel {i % 2}",
                video_title=f"Video {i}",
                published_timestamp=f"2024-01-0{i+1}T00:00:00"
            )
        
        # Update some statuses
        self.state_manager.update_video_status("test0", "COMPLETED")
        self.state_manager.update_video_status("test1", "FAILED")
        
        # Get statistics
        stats = self.state_manager.get_statistics()
        
        self.assertEqual(stats["total_videos"], 5)
        self.assertEqual(stats["completed"], 1)
        self.assertEqual(stats["failed"], 1)
        self.assertEqual(stats["pending"], 3)


class TestConfig(unittest.TestCase):
    """Tests for Config class."""

    @classmethod
    def setUpClass(cls):
        cls._keyring_patcher = patch("config.keyring.get_password", return_value=None)
        cls._mock_keyring = cls._keyring_patcher.start()

    @classmethod
    def tearDownClass(cls):
        cls._keyring_patcher.stop()

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.env_file = Path(self.test_dir) / ".env"
        
        # Store original environment variables
        self.original_env = {}
        for var in ['TELEGRAM_BOT_TOKEN', 'TELEGRAM_CHAT_ID', 'OLLAMA_HOST', 'OLLAMA_MODEL', 'YOUTUBE_CHANNEL_IDS']:
            self.original_env[var] = os.environ.get(var)
    
    def tearDown(self):
        """Clean up test fixtures."""
        # Restore original environment variables
        for var, value in self.original_env.items():
            if value is None:
                os.environ.pop(var, None)
            else:
                os.environ[var] = value
        
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def _set_env_vars(self, env_content):
        """Helper to set environment variables from content."""
        for line in env_content.strip().split('\n'):
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip()
    
    def test_valid_config(self):
        """Test loading valid configuration."""
        # Set environment variables
        env_content = """
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_ID=123456789
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=qwen2.5:1.5b
YOUTUBE_CHANNEL_IDS=UC-lHJZR3Gqxm24_Vd_AJ5Yw,UCaXkpc6S7t4Kl3M3bX8m6Bw
"""
        self._set_env_vars(env_content)
        
        # Load config
        config = Config()
        
        self.assertEqual(config.telegram_bot_token, "123456789:ABCdefGHIjklMNOpqrsTUVwxyz")
        self.assertEqual(config.telegram_chat_id, "123456789")
        self.assertEqual(config.ollama_host, "http://localhost:11434")
        self.assertEqual(config.ollama_model, "qwen2.5:1.5b")
        self.assertEqual(len(config.youtube_channel_ids), 2)
    
    def test_missing_required_vars(self):
        """Test missing required environment variables."""
        # Clear all environment variables
        for var in ['TELEGRAM_BOT_TOKEN', 'TELEGRAM_CHAT_ID', 'OLLAMA_HOST']:
            os.environ.pop(var, None)
        
        # Try to load config
        with self.assertRaises(ConfigError) as context:
            Config()
        
        self.assertIn("Missing required environment variables", str(context.exception))
    
    def test_invalid_telegram_token(self):
        """Test invalid Telegram bot token format."""
        env_content = """
TELEGRAM_BOT_TOKEN=invalid_token_format
TELEGRAM_CHAT_ID=123456789
OLLAMA_HOST=http://localhost:11434
"""
        self._set_env_vars(env_content)
        
        with self.assertRaises(ConfigError) as context:
            Config()
        
        self.assertIn("Invalid Telegram bot token format", str(context.exception))
    
    def test_invalid_ollama_host(self):
        """Test invalid Ollama host URL."""
        env_content = """
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_ID=123456789
OLLAMA_HOST=invalid-url
"""
        self._set_env_vars(env_content)
        
        with self.assertRaises(ConfigError) as context:
            Config()
        
        self.assertIn("OLLAMA_HOST must start with http:// or https://", str(context.exception))
    
    def test_config_properties(self):
        """Test configuration properties."""
        env_content = """
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_ID=123456789
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=qwen2.5:1.5b
YOUTUBE_CHANNEL_IDS=UC-lHJZR3Gqxm24_Vd_AJ5Yw
"""
        self._set_env_vars(env_content)
        
        config = Config()
        
        # Test database path
        self.assertTrue(config.database_path.name == "subscriptions_state.db")
        
        # Test get_all_config masks sensitive values
        all_config = config.get_all_config()
        self.assertEqual(all_config["telegram_bot_token"], "***")
        self.assertEqual(all_config["telegram_chat_id"], "123456789")


class TestYouTubeMCPServer(unittest.TestCase):
    """Tests for YouTubeMCPServer class."""
    
    def setUp(self):
        """Set up test fixtures."""
        from mcp_server_youtube import YouTubeMCPServer
        self.youtube_server = YouTubeMCPServer()
    
    @patch('mcp_server_youtube.feedparser.parse')
    def test_fetch_latest_videos_from_rss(self, mock_parse):
        """Test fetching latest videos from RSS feed."""
        # Mock feed response
        mock_feed = Mock()
        mock_feed.bozo = False
        mock_feed.entries = [
            Mock(
                get=lambda x, default: {
                    'title': 'Test Video 1',
                    'link': 'https://www.youtube.com/watch?v=test123',
                    'published': '2024-01-01T00:00:00Z',
                    'updated': '2024-01-01T00:00:00Z',
                    'summary': 'Test summary'
                }.get(x, default)
            ),
            Mock(
                get=lambda x, default: {
                    'title': 'Test Video 2',
                    'link': 'https://www.youtube.com/watch?v=test456',
                    'published': '2024-01-02T00:00:00Z',
                    'updated': '2024-01-02T00:00:00Z',
                    'summary': 'Test summary 2'
                }.get(x, default)
            )
        ]
        mock_feed.feed.title = "Test Channel"
        
        mock_parse.return_value = mock_feed
        
        # Test fetch
        videos = self.youtube_server.fetch_latest_videos_from_rss("UC-lHJZR3Gqxm24_Vd_AJ5Yw")
        
        self.assertEqual(len(videos), 2)
        self.assertEqual(videos[0]['video_id'], 'test123')
        self.assertEqual(videos[1]['video_id'], 'test456')
    
    def test_extract_video_id_from_url(self):
        """Test extracting video ID from URL."""
        test_cases = [
            ("https://www.youtube.com/watch?v=dQw4f9dGZmc", "dQw4f9dGZmc"),
            ("https://youtube.com/watch?v=dQw4f9dGZmc", "dQw4f9dGZmc"),
            ("https://youtu.be/dQw4f9dGZmc", None),  # Not matched by current regex
            ("https://www.youtube.com/embed/dQw4f9dGZmc", None),  # Not matched
        ]
        
        for url, expected in test_cases:
            result = self.youtube_server._extract_video_id_from_url(url)
            self.assertEqual(result, expected, f"Failed for URL: {url}")


class TestOllamaClient(unittest.TestCase):
    """Tests for OllamaClient class."""
    
    def setUp(self):
        """Set up test fixtures."""
        from ollama_client import OllamaClient
        self.ollama_client = OllamaClient()
    
    @patch('ollama_client.requests.post')
    def test_generate_summary(self, mock_post):
        """Test generating summary with Ollama."""
        # Mock response
        mock_response = Mock()
        mock_response.json.return_value = {
            "response": "This is a test summary of the video transcript."
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        # Test summary generation
        summary = self.ollama_client.generate_summary(
            transcript="This is a test transcript.",
            video_title="Test Video",
            channel_name="Test Channel"
        )
        
        self.assertIsNotNone(summary)
        self.assertIn("test summary", summary.lower())
    
    @patch('ollama_client.requests.post')
    def test_is_available(self, mock_post):
        """Test checking Ollama availability."""
        # Mock successful response
        mock_response = Mock()
        mock_response.json.return_value = {
            "models": [
                {"name": "qwen2.5:1.5b"},
                {"name": "llama2"}
            ]
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        # Test availability
        available = self.ollama_client.is_available()
        self.assertTrue(available)
    
    def test_is_available_integration(self):
        """Integration test for Ollama availability (requires running Ollama)."""
        # This test will fail if Ollama is not running
        # Skip if Ollama is not available
        try:
            import requests
            response = requests.get("http://localhost:11434/api/tags", timeout=2)
            if response.status_code != 200:
                self.skipTest("Ollama is not running")
        except:
            self.skipTest("Ollama is not running")
        
        # Test availability with real Ollama
        available = self.ollama_client.is_available()
        # We can't assert True because the model might not be pulled
        # Just ensure it doesn't crash
        self.assertIsInstance(available, bool)


class TestTelegramMCPServer(unittest.TestCase):
    """Tests for TelegramMCPServer class."""
    
    def setUp(self):
        """Set up test fixtures."""
        from mcp_server_notifier import TelegramMCPServer
        self.telegram_server = TelegramMCPServer(
            bot_token="123456789:ABCdefGHIjklMNOpqrsTUVwxyz",
            chat_id="123456789"
        )
    
    @patch('mcp_server_notifier.requests.post')
    def test_send_message(self, mock_post):
        """Test sending a message."""
        # Mock successful response
        mock_response = Mock()
        mock_response.json.return_value = {"ok": True}
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        # Test sending message
        result = self.telegram_server.send_message("Test message")
        
        self.assertTrue(result)
        mock_post.assert_called_once()
    
    @patch('mcp_server_notifier.requests.post')
    def test_send_telegram_summary(self, mock_post):
        """Test sending video summary."""
        # Mock successful response
        mock_response = Mock()
        mock_response.json.return_value = {"ok": True}
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        # Test sending summary
        result = self.telegram_server.send_telegram_summary(
            title="Test Video",
            channel="Test Channel",
            summary_body="This is a test summary.",
            video_url="https://www.youtube.com/watch?v=test123"
        )
        
        self.assertTrue(result)
    
    def test_escape_markdown(self):
        """Test Markdown escaping."""
        test_cases = [
            ("Hello World", "Hello World"),
            ("Hello_World", "Hello\\_World"),
            ("Hello*World", "Hello\\*World"),
            ("Hello[World]", "Hello\\[World\\]"),
        ]
        
        for input_text, expected in test_cases:
            result = self.telegram_server._escape_markdown(input_text)
            self.assertEqual(result, expected, f"Failed for input: {input_text}")


class TestIntegration(unittest.TestCase):
    """Integration tests for the complete pipeline."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = tempfile.mkdtemp()
        self.db_path = Path(self.test_dir) / "test.db"
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_video_processing_flow(self):
        """Test complete video processing flow."""
        from state_manager import StateManager
        
        state_manager = StateManager(self.db_path)
        
        # Add video
        state_manager.add_video(
            video_id="integration_test",
            channel_name="Test Channel",
            video_title="Integration Test Video",
            published_timestamp=datetime.now().isoformat()
        )
        
        # Verify initial state
        video = state_manager.get_video("integration_test")
        self.assertEqual(video["summary_status"], "PENDING")
        
        # Update to processing
        state_manager.update_video_status("integration_test", "PROCESSING")
        video = state_manager.get_video("integration_test")
        self.assertEqual(video["summary_status"], "PROCESSING")
        
        # Update to completed
        state_manager.update_video_status("integration_test", "COMPLETED")
        video = state_manager.get_video("integration_test")
        self.assertEqual(video["summary_status"], "COMPLETED")
        
        # Verify statistics
        stats = state_manager.get_statistics()
        self.assertEqual(stats["total_videos"], 1)
        self.assertEqual(stats["completed"], 1)


def run_tests():
    """Run all tests."""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestStateManager))
    suite.addTests(loader.loadTestsFromTestCase(TestConfig))
    suite.addTests(loader.loadTestsFromTestCase(TestYouTubeMCPServer))
    suite.addTests(loader.loadTestsFromTestCase(TestOllamaClient))
    suite.addTests(loader.loadTestsFromTestCase(TestTelegramMCPServer))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
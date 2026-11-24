"""
macOS Notification & Alert Integration
Provides native macOS Notification Center alerts, sound effects, and badge signals using osascript.
"""

import os
import platform
import subprocess
import logging

logger = logging.getLogger("BulkScraper.macOS")

SYSTEM_SOUNDS = {
    "default": "Glass",
    "success": "Hero",
    "alert": "Ping",
    "error": "Basso",
    "complete": "Purr",
    "warning": "Sosumi",
    "pop": "Pop",
    "bottle": "Bottle",
    "submarine": "Submarine",
}


class MacOSNotifier:
    """Handles native macOS desktop notifications and system sounds."""

    def __init__(self, enabled: bool = True, default_sound: str = "Glass"):
        self.enabled = enabled
        self.is_macos = platform.system() == "Darwin"
        self.default_sound = default_sound

    def notify(
        self,
        title: str,
        message: str,
        subtitle: str = "Bulk Social Media Scraper",
        sound: str = "default",
    ) -> bool:
        """
        Display a native macOS Notification Center notification.
        Uses AppleScript via osascript.
        """
        if not self.enabled:
            return False

        # Clean strings for AppleScript
        safe_title = title.replace('"', '\\"').replace("'", "\\'")
        safe_subtitle = subtitle.replace('"', '\\"').replace("'", "\\'")
        safe_message = message.replace('"', '\\"').replace("'", "\\'")
        sound_name = SYSTEM_SOUNDS.get(sound, self.default_sound)

        if self.is_macos:
            try:
                script = (
                    f'display notification "{safe_message}" '
                    f'with title "{safe_title}" '
                    f'subtitle "{safe_subtitle}" '
                    f'sound name "{sound_name}"'
                )
                subprocess.run(
                    ["osascript", "-e", script],
                    check=False,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                logger.debug("macOS notification sent: %s - %s", title, message)
                return True
            except Exception as e:
                logger.warning("Failed to trigger macOS notification: %s", e)

        # Fallback terminal bell
        print("\a", end="", flush=True)
        return False

    def alert_dialog(self, title: str, message: str, buttons: list = None) -> str:
        """
        Display a native macOS pop-up dialog box.
        Returns the clicked button name.
        """
        if not self.is_macos:
            return ""

        buttons = buttons or ["OK"]
        button_str = ", ".join(f'"{b}"' for b in buttons)
        default_btn = buttons[-1]

        safe_title = title.replace('"', '\\"')
        safe_message = message.replace('"', '\\"')

        script = (
            f'display dialog "{safe_message}" with title "{safe_title}" '
            f'buttons {{{button_str}}} default button "{default_btn}" with icon note'
        )

        try:
            res = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                check=False,
            )
            out = res.stdout.strip()
            # output format: button returned:OK
            if "button returned:" in out:
                return out.split("button returned:")[-1].strip()
        except Exception as e:
            logger.warning("Failed to display macOS dialog: %s", e)

        return ""

    def play_sound(self, sound_name: str = "Hero"):
        """Plays a native macOS system sound from /System/Library/Sounds."""
        if not self.is_macos:
            return
        sound_file = f"/System/Library/Sounds/{sound_name}.aiff"
        if os.path.exists(sound_file):
            try:
                subprocess.run(
                    ["afplay", sound_file],
                    check=False,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            except Exception:
                pass


# Global singleton instance
notifier = MacOSNotifier()

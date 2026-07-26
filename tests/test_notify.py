from unittest.mock import patch

from hades.commands.watch import _send_notification

SESSION = {"tool": "claude", "project_path": "/foo/bar"}


def test_notify_darwin_uses_osascript():
    with patch("hades.commands.watch.platform.system", return_value="Darwin"), \
         patch("hades.commands.watch.subprocess.run") as run:
        _send_notification(SESSION)
    assert run.call_args[0][0][0] == "osascript"


def test_notify_linux_uses_notify_send():
    with patch("hades.commands.watch.platform.system", return_value="Linux"), \
         patch("hades.commands.watch.subprocess.run") as run:
        _send_notification(SESSION)
    assert run.call_args[0][0][0] == "notify-send"


def test_notify_linux_missing_binary_is_silent():
    with patch("hades.commands.watch.platform.system", return_value="Linux"), \
         patch("hades.commands.watch.subprocess.run", side_effect=FileNotFoundError):
        _send_notification(SESSION)  # must not raise


def test_notify_other_platform_is_noop():
    with patch("hades.commands.watch.platform.system", return_value="Windows"), \
         patch("hades.commands.watch.subprocess.run") as run:
        _send_notification(SESSION)
    run.assert_not_called()

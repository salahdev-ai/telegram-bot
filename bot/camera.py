"""
camera.py -- IMX519 camera interface for PocketScan.

Strategy (best-to-fallback):
  1. picamera2  — native libcamera stack (best quality, hardware AF)
  2. OpenCV V4L2 — generic V4L2 driver (works if camera appears as /dev/videoX)

For A4 document scanning we capture at full 16MP (4656x3496) with:
  - Hardware autofocus (AF) triggered before every shot
  - 2-second warm-up for AE/AWB settling
  - JPEG quality 95
"""
import logging
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# IMX519 native resolution
CAPTURE_WIDTH  = 4656
CAPTURE_HEIGHT = 3496
JPEG_QUALITY   = 95

# ─── Camera backend detection ─────────────────────────────────────────────────

def _picamera2_available() -> bool:
    try:
        import picamera2  # noqa: F401
        return True
    except ImportError:
        return False


# ─── Backend 1: picamera2 (libcamera) ────────────────────────────────────────

def _capture_picamera2(output_path: str) -> bool:
    """Capture via picamera2 with hardware AF and full IMX519 resolution."""
    try:
        from picamera2 import Picamera2
        from libcamera import controls as lc

        logger.info("Using picamera2 backend")
        cam = Picamera2()

        cfg = cam.create_still_configuration(
            main={"size": (CAPTURE_WIDTH, CAPTURE_HEIGHT), "format": "RGB888"},
            controls={
                "AfMode":    lc.AfModeEnum.Continuous,
                "AeEnable":  True,
                "AwbEnable": True,
                "Sharpness": 2.0,
                "Saturation": 1.2,
                "Contrast":  1.1,
            },
        )
        cam.configure(cfg)
        cam.start()

        logger.info("Sensor warm-up (2 s)...")
        time.sleep(2)

        # Trigger one-shot AF cycle and wait for lens to lock
        logger.info("Triggering hardware autofocus...")
        cam.set_controls({
            "AfMode":    lc.AfModeEnum.Auto,
            "AfTrigger": lc.AfTriggerEnum.Start,
        })
        time.sleep(3)  # typical IMX519 AF settle time

        logger.info(f"Capturing → {output_path}")
        cam.capture_file(output_path)
        cam.stop()
        cam.close()
        logger.info("picamera2 capture OK")
        return True

    except ImportError:
        logger.warning("picamera2 not available")
        return False
    except Exception as exc:
        logger.error(f"picamera2 capture failed: {exc}")
        return False


# ─── Backend 2: OpenCV / V4L2 ────────────────────────────────────────────────

def _v4l2_autofocus() -> None:
    """Try to trigger AF via v4l2-ctl."""
    try:
        result = subprocess.run(
            ["v4l2-ctl", "--set-ctrl=focus_auto=1"],
            capture_output=True, timeout=5,
        )
        if result.returncode == 0:
            logger.info("V4L2 AF triggered via v4l2-ctl")
            time.sleep(2)
        else:
            logger.warning("v4l2-ctl AF not available, using fixed focus")
    except FileNotFoundError:
        logger.warning("v4l2-ctl not found, skipping AF")
    except subprocess.TimeoutExpired:
        logger.warning("v4l2-ctl timed out")


def _capture_v4l2(output_path: str) -> bool:
    """Capture via OpenCV + V4L2 with best possible settings."""
    try:
        import cv2

        logger.info("Using OpenCV/V4L2 backend")
        _v4l2_autofocus()

        cap: Optional[cv2.VideoCapture] = None
        for dev_id in range(4):                       # try /dev/video0..3
            test = cv2.VideoCapture(dev_id, cv2.CAP_V4L2)
            if test.isOpened():
                cap = test
                logger.info(f"Opened /dev/video{dev_id}")
                break
            test.release()

        if cap is None or not cap.isOpened():
            logger.error("No V4L2 camera device found (checked /dev/video0-3)")
            return False

        # Request full resolution
        cap.set(cv2.CAP_PROP_FRAME_WIDTH,  CAPTURE_WIDTH)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAPTURE_HEIGHT)
        cap.set(cv2.CAP_PROP_AUTOFOCUS, 1)
        cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1)

        logger.info("Letting AE/AWB settle (2 s)...")
        for _ in range(10):                           # drain stale frames
            cap.grab()
        time.sleep(2)

        ret, frame = cap.read()
        cap.release()

        if not ret or frame is None:
            logger.error("V4L2 frame read failed")
            return False

        cv2.imwrite(output_path, frame, [
            cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY,
            cv2.IMWRITE_JPEG_OPTIMIZE, 1,
        ])
        logger.info(f"V4L2 capture saved → {output_path}")
        return True

    except ImportError:
        logger.error("opencv-python-headless not installed")
        return False
    except Exception as exc:
        logger.error(f"V4L2 capture failed: {exc}")
        return False


# ─── Public API ───────────────────────────────────────────────────────────────

def capture_photo(photo_dir: Path) -> str:
    """
    Capture a full-resolution photo using the best available backend.

    Args:
        photo_dir: Directory where the photo will be saved.

    Returns:
        Absolute path to the saved JPEG file.

    Raises:
        RuntimeError: When all capture backends fail.
    """
    timestamp   = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = str(photo_dir / f"scan_{timestamp}.jpg")

    if _capture_picamera2(output_path):
        return output_path

    if _capture_v4l2(output_path):
        return output_path

    raise RuntimeError(
        "Camera capture failed.\n"
        "Check: camera ribbon connection, dtoverlay in /boot/firmware/config.txt, "
        "and that the camera is not in use by another process."
    )

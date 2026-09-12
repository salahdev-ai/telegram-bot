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


def _capture_libcamera(output_path: str) -> bool:
    """Capture via native libcamera-still / rpicam-still CLI.
    This is the most reliable way to capture on modern Pi OS."""
    logger.info("Using libcamera-still backend")
    
    # Try rpicam-still (Bookworm) first, fallback to libcamera-still (Bullseye)
    cmds = ["rpicam-still", "libcamera-still"]
    
    for cmd in cmds:
        try:
            # -n: no preview
            # -t 2000: 2 second warmup
            # --autofocus-mode auto: trigger AF
            # -o: output file
            # --width/--height: force full res
            
            # The Arducam drivers are now installed, so true Autofocus works!
            # We use a 2s warmup and tell libcamera to lock focus before snapping.
            logger.info(f"Running: {cmd} with Autofocus...")
            result = subprocess.run([
                cmd,
                "-n",
                "-t", "2000",
                "--autofocus-mode", "auto",
                "--autofocus-on-capture",
                "--width", str(CAPTURE_WIDTH),
                "--height", str(CAPTURE_HEIGHT),
                "-q", str(JPEG_QUALITY),
                "-o", output_path
            ], capture_output=True, text=True, timeout=15)
            
            if result.returncode == 0 and Path(output_path).exists():
                logger.info(f"Capture OK -> {output_path}")
                return True
            else:
                logger.error(f"{cmd} failed with code {result.returncode}")
                logger.error(f"stderr: {result.stderr}")
                
        except FileNotFoundError:
            continue # Try next command
        except subprocess.TimeoutExpired:
            logger.error(f"{cmd} timed out")
            return False
            
    logger.error("No libcamera capture tools found or all failed")
    return False


# ─── Public API ───────────────────────────────────────────────────────────────

def check_camera() -> dict:
    """
    Probe available camera backends and return a status report.

    Returns a dict with keys:
        ok          bool   — True if at least one backend found a camera
        backend     str    — 'picamera2', 'v4l2', or 'none'
        details     list   — human-readable lines describing what was found
        errors      list   — any error/warning messages
    """
    details = []
    errors  = []

    # ── picamera2 probe ───────────────────────────────────────
    picam_ok = False
    try:
        from picamera2 import Picamera2
        cams = Picamera2.global_camera_info()
        if cams:
            picam_ok = True
            for i, c in enumerate(cams):
                model = c.get("Model", "unknown")
                loc   = c.get("Location", "")
                details.append(f"picamera2  cam[{i}]: {model}  {loc}")
        else:
            errors.append("picamera2 loaded but no cameras detected")
    except ImportError:
        errors.append("picamera2 not installed (using V4L2 mode)")
    except Exception as exc:
        errors.append(f"picamera2 probe error: {exc}")

    # ── V4L2 probe ────────────────────────────────────────────
    v4l2_ok    = False
    v4l2_devs  = []
    try:
        # list-devices gives human-readable names
        result = subprocess.run(
            ["v4l2-ctl", "--list-devices"],
            capture_output=True, text=True, timeout=5,
        )
        if result.stdout.strip():
            v4l2_ok = True
            for line in result.stdout.strip().splitlines():
                v4l2_devs.append(line.strip())
            details.append("V4L2 devices:\n    " + "\n    ".join(v4l2_devs))
        else:
            errors.append("v4l2-ctl found no devices")
    except FileNotFoundError:
        errors.append("v4l2-utils not installed (run: sudo apt install v4l-utils)")
    except subprocess.TimeoutExpired:
        errors.append("v4l2-ctl timed out")
    except Exception as exc:
        errors.append(f"V4L2 probe error: {exc}")

    # ── libcamera-hello quick probe ───────────────────────────
    try:
        result = subprocess.run(
            ["libcamera-hello", "--list-cameras"],
            capture_output=True, text=True, timeout=5,
        )
        output = (result.stdout + result.stderr).strip()
        if output:
            details.append("libcamera:\n    " + "\n    ".join(output.splitlines()[:6]))
    except FileNotFoundError:
        pass  # libcamera-apps not installed, not critical
    except subprocess.TimeoutExpired:
        errors.append("libcamera-hello timed out")
    except Exception:
        pass

    ok = picam_ok or v4l2_ok
    backend = "picamera2" if picam_ok else ("v4l2" if v4l2_ok else "none")
    return {"ok": ok, "backend": backend, "details": details, "errors": errors}


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

    if _capture_libcamera(output_path):
        return output_path

    raise RuntimeError(
        "Camera capture failed.\n"
        "Check: camera ribbon connection, dtoverlay in /boot/firmware/config.txt, "
        "and that the camera is not in use by another process."
    )


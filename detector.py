import argparse
from pathlib import Path
import cv2
import torch
from ultralytics import YOLO

DEVICE = "mps" if torch.backends.mps.is_available() else "cpu"

class RoomDetector:
    def __init__(self, model_name: str = "yolov8n.pt", brightness_threshold: float = 75.0):
        self.model = YOLO(model_name)
        self.brightness_threshold = brightness_threshold
        self.device = DEVICE

    def analyze_frame(self, frame):
        """Analyzes a single frame for person count and lighting status."""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        mean_brightness = float(cv2.mean(gray)[0])
        lights_on = mean_brightness >= self.brightness_threshold

        # Lower conf + higher imgsz picks up seated/partially occluded people
        results = self.model.predict(
            source=frame,
            classes=[0],
            device=self.device,
            verbose=False,
            conf=0.20,
            imgsz=1280,
            agnostic_nms=True
        )
        person_count = len(results[0].boxes)

        return {
            "person_count": person_count,
            "mean_brightness": round(mean_brightness, 2),
            "lights_on": lights_on
        }

    def process_clip(self, video_path: str, display: bool = False):
        """Processes a local video file frame by frame."""
        path = Path(video_path)
        if not path.is_file():
            raise FileNotFoundError(f"Video file not found at: {video_path}")

        cap = cv2.VideoCapture(str(path))
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0

        print(f"[*] Processing: {path.name} on device='{self.device}' (Threshold: {self.brightness_threshold})")

        frame_idx = 0
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            if frame_idx % 10 == 0:
                stats = self.analyze_frame(frame)
                timestamp = round(frame_idx / fps, 2)
                print(f"[{timestamp}s] People: {stats['person_count']} | Brightness: {stats['mean_brightness']} | Lights ON: {stats['lights_on']}")

                if display:
                    color = (0, 255, 0) if stats["lights_on"] else (0, 0, 255)
                    text = f"People: {stats['person_count']} | Light: {'ON' if stats['lights_on'] else 'OFF'}"
                    cv2.putText(frame, text, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2)
                    cv2.imshow("Room Detector Stream", frame)
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break

            frame_idx += 1

        cap.release()
        if display:
            cv2.destroyAllWindows()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run occupancy & light detection on a video clip.")
    parser.add_argument("--clip", type=str, default="clips/sample.mp4", help="Path to input video file")
    parser.add_argument("--threshold", type=float, default=75.0, help="Brightness threshold for light on/off")
    parser.add_argument("--view", action="store_true", help="Display visual cv2 window preview")

    args = parser.parse_args()
    detector = RoomDetector(brightness_threshold=args.threshold)
    detector.process_clip(video_path=args.clip, display=args.view)
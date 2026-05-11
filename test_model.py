import cv2
import sys
import os

# Add current directory to path so it can find 'services'
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.ai_service import AIService

def test_image(img_path):
    print(f"Loading image: {img_path}")
    frame = cv2.imread(img_path)
    if frame is None:
        print("Error: Could not load image. Please check the path.")
        return

    print("Initializing AI Service and loading best.onnx...")
    svc = AIService()
    if not svc.model_loaded:
        print("Error: Failed to load the model!")
        return

    print("Running inference...")
    result = svc.run_inference(frame)
    
    print("-" * 40)
    print(f"Inference time : {result.inference_time_ms:.1f} ms")
    print(f"Defects found  : {result.defect_count}")
    print(f"Is Simulated   : {result.is_simulated}")
    print("-" * 40)
    
    for i, box in enumerate(result.boxes):
        print(f"[{i+1}] {box.label} (Conf: {box.confidence:.2f}) -> Bounding Box: (X1: {box.x1:.1f}, Y1: {box.y1:.1f}, X2: {box.x2:.1f}, Y2: {box.y2:.1f})")
    
    print("-" * 40)

if __name__ == '__main__':
    if len(sys.argv) > 1:
        test_image(sys.argv[1])
    else:
        print("Usage: python test_model.py <path_to_image>")

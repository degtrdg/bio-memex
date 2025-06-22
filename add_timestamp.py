import cv2
import numpy as np

def add_timestamp_to_video(input_path, output_path):
    cap = cv2.VideoCapture(input_path)
    
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    # Use lossless codec for maximum quality
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height), isColor=True)
    
    frame_count = 0
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
            
        current_time_seconds = frame_count / fps
        minutes = int(current_time_seconds // 60)
        seconds = int(current_time_seconds % 60)
        
        timestamp_text = f"{minutes:02d}:{seconds:02d}"
        
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 1.2
        color = (255, 255, 255)
        thickness = 2
        
        text_size = cv2.getTextSize(timestamp_text, font, font_scale, thickness)[0]
        text_x = width - text_size[0] - 20
        text_y = 40
        
        cv2.rectangle(frame, (text_x - 10, text_y - text_size[1] - 10), 
                     (text_x + text_size[0] + 10, text_y + 10), (0, 0, 0), -1)
        
        cv2.putText(frame, timestamp_text, (text_x, text_y), font, font_scale, color, thickness)
        
        out.write(frame)
        frame_count += 1
        
        if frame_count % 100 == 0:
            print(f"Processed {frame_count} frames ({current_time_seconds:.1f}s)")
    
    cap.release()
    out.release()
    print(f"Video with timestamp saved to: {output_path}")

if __name__ == "__main__":
    input_video = "videos/output_long_again_2.mp4"
    output_video = "videos/output_long_again_2_timestamped.mp4"
    
    add_timestamp_to_video(input_video, output_video)
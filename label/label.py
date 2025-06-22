from inference_sdk import InferenceHTTPClient
import sys
import cv2
import json
import os

# Create data directories if they don't exist
def ensure_data_directories():
    """Ensure the data directory structure exists."""
    directories = ['data/json', 'data/original', 'data/annotated']
    for directory in directories:
        os.makedirs(directory, exist_ok=True)

def find_source_prediction_with_smallest_y(result):
    """Find the source prediction with the smallest y coordinate from the result."""
    # Handle if result is a list (as from Roboflow API)
    if isinstance(result, list):
        if len(result) == 0:
            return None
        result = result[0]

    if not result or 'predictions' not in result:
        return None
    
    predictions_container = result['predictions']
    predictions = predictions_container.get('predictions', None)
    if not predictions:
        return None
    
    # Find prediction with smallest y coordinate
    min_y_prediction = None
    min_y = float('inf')
    
    for i, prediction in enumerate(predictions):
        y_coord = None
        
        # Handle different prediction formats
        if 'x' in prediction and 'y' in prediction and 'width' in prediction and 'height' in prediction:
            if prediction['height'] > 500:
                continue
            y_coord = prediction['y']
        elif 'bbox' in prediction:
            bbox = prediction['bbox']
            if len(bbox) >= 4:
                y_coord = bbox[1]
        
        if y_coord is not None and y_coord < min_y:
            min_y = y_coord
            min_y_prediction = prediction
    
    return min_y_prediction

def get_destination_predictions_above_confidence(result, confidence_threshold=0.1):
    """Get all destination predictions above the confidence threshold."""
    # Handle if result is a list (as from Roboflow API)
    if isinstance(result, list):
        if len(result) == 0:
            return []
        result = result[0]

    if not result or 'predictions' not in result:
        return []
    
    predictions_container = result['predictions']
    predictions = predictions_container.get('predictions', None)
    if not predictions:
        return []
    
    # Filter predictions above confidence threshold
    high_confidence_predictions = []
    
    for prediction in predictions:
        confidence = prediction.get('confidence', 0)
        if confidence >= confidence_threshold:
            high_confidence_predictions.append(prediction)
    
    return high_confidence_predictions

def draw_single_bounding_box(image, prediction, color=(0, 255, 0), thickness=2):
    """Draw a single bounding box on the image."""
    # Extract bounding box coordinates (treating x, y as center points)
    if 'bbox' in prediction:
        # Format: [x, y, width, height] where x, y are center coordinates
        bbox = prediction['bbox']
        center_x, center_y, w, h = int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])
        # Convert center coordinates to top-left coordinates
        x = center_x - w // 2
        y = center_y - h // 2
    elif 'x' in prediction and 'y' in prediction and 'width' in prediction and 'height' in prediction:
        # Format: separate x, y, width, height fields where x, y are center coordinates
        center_x, center_y = int(prediction['x']), int(prediction['y'])
        w, h = int(prediction['width']), int(prediction['height'])
        # Convert center coordinates to top-left coordinates
        x = center_x - w // 2
        y = center_y - h // 2
    else:
        print("Error: Could not extract bounding box coordinates from prediction")
        return False
    
    # Draw the bounding box
    cv2.rectangle(image, (x, y), (x + w, y + h), color, thickness)
    
    # Add label if available
    if 'class' in prediction:
        label = prediction['class']
        confidence = prediction.get('confidence', 0)
        label_text = f"{label} ({confidence:.2f})"
        cv2.putText(image, label_text, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
    
    return True

def draw_source_bounding_box(image_path, prediction, output_path):
    """Draw source bounding box on image and save it."""
    # Read the image
    image = cv2.imread(image_path)
    if image is None:
        print(f"Error: Could not read image {image_path}")
        return False
    
    # Draw the bounding box
    success = draw_single_bounding_box(image, prediction, color=(0, 255, 0), thickness=2)
    
    if success:
        # Save the annotated image
        cv2.imwrite(output_path, image)
        print(f"Source annotated image saved to: {output_path}")
        return True
    else:
        return False

def draw_destination_bounding_boxes(image_path, predictions, output_path):
    """Draw all destination bounding boxes on image and save it."""
    # Read the image
    image = cv2.imread(image_path)
    if image is None:
        print(f"Error: Could not read image {image_path}")
        return False
    
    # Draw all bounding boxes
    success_count = 0
    for prediction in predictions:
        success = draw_single_bounding_box(image, prediction, color=(255, 0, 0), thickness=2)
        if success:
            success_count += 1
    
    # Save the annotated image
    cv2.imwrite(output_path, image)
    print(f"Destination annotated image saved to: {output_path}")
    print(f"Drew {success_count} bounding boxes out of {len(predictions)} predictions")
    return True

def draw_combined_annotations(image_path, source_prediction, destination_predictions, output_path):
    """Draw both source and destination annotations on the same image."""
    # Read the image
    image = cv2.imread(image_path)
    if image is None:
        print(f"Error: Could not read image {image_path}")
        return False
    
    success_count = 0
    
    # Draw source bounding box in green
    if source_prediction:
        success = draw_single_bounding_box(image, source_prediction, color=(0, 255, 0), thickness=2)
        if success:
            success_count += 1
            print("Drew source bounding box (green)")
    
    # Draw destination bounding boxes in red
    for prediction in destination_predictions:
        success = draw_single_bounding_box(image, prediction, color=(255, 0, 0), thickness=2)
        if success:
            success_count += 1
    
    # Save the combined annotated image
    cv2.imwrite(output_path, image)
    print(f"Combined annotated image saved to: {output_path}")
    print(f"Drew {success_count} total bounding boxes (1 source + {len(destination_predictions)} destinations)")
    return True

def run_source_workflow(client, image_path, base_name):
    """Run the source workflow (custom-workflow-2) and process results."""
    print("Running source workflow (custom-workflow-2)...")
    
    result = client.run_workflow(
        workspace_name="test-ymb2o",
        workflow_id="custom-workflow-2",
        images={"image": image_path},
        use_cache=True
    )

    # Save raw results to JSON file in data/json directory
    json_output_path = f"data/json/{base_name}_source_results.json"
    
    try:
        with open(json_output_path, 'w') as f:
            json.dump(result, f, indent=2)
        print(f"Source results saved to: {json_output_path}")
    except Exception as e:
        print(f"Warning: Could not save source results to JSON file: {e}")

    # Find prediction with smallest y coordinate
    min_y_prediction = find_source_prediction_with_smallest_y(result)
    
    if min_y_prediction:
        # Extract y coordinate
        if 'y' in min_y_prediction:
            y_coord = min_y_prediction['y']
        elif 'bbox' in min_y_prediction:
            bbox = min_y_prediction['bbox']
            y_coord = bbox[1]  # y (top of bbox)
        else:
            y_coord = "N/A"
        
        print(f"Source - Smallest y coordinate: {y_coord}")
        
        # Print bounding box information
        if 'bbox' in min_y_prediction:
            bbox = min_y_prediction['bbox']
            print(f"Source bounding box: x={bbox[0]}, y={bbox[1]}, width={bbox[2]}, height={bbox[3]}")
        elif 'x' in min_y_prediction and 'y' in min_y_prediction and 'width' in min_y_prediction and 'height' in min_y_prediction:
            print(f"Source bounding box: x={min_y_prediction['x']}, y={min_y_prediction['y']}, width={min_y_prediction['width']}, height={min_y_prediction['height']}")
        else:
            print("Source bounding box: Not available")
    else:
        print("No source predictions found or could not determine smallest y coordinate")
    
    return result, min_y_prediction

def run_destination_workflow(client, image_path, base_name):
    """Run the destination workflow (custom-workflow-3) and process results."""
    print("Running destination workflow (custom-workflow-3)...")
    
    result = client.run_workflow(
        workspace_name="test-ymb2o",
        workflow_id="custom-workflow-3",
        images={"image": image_path},
        use_cache=True
    )

    # Save raw results to JSON file in data/json directory
    json_output_path = f"data/json/{base_name}_destination_results.json"
    
    try:
        with open(json_output_path, 'w') as f:
            json.dump(result, f, indent=2)
        print(f"Destination results saved to: {json_output_path}")
    except Exception as e:
        print(f"Warning: Could not save destination results to JSON file: {e}")

    # Get all predictions above confidence threshold
    high_confidence_predictions = get_destination_predictions_above_confidence(result, confidence_threshold=0.1)
    
    if high_confidence_predictions:
        print(f"Found {len(high_confidence_predictions)} destination predictions above confidence 0.1")
        
        # Print information about each prediction
        for i, prediction in enumerate(high_confidence_predictions):
            confidence = prediction.get('confidence', 0)
            class_name = prediction.get('class', 'Unknown')
            print(f"Destination prediction {i+1}: {class_name} (confidence: {confidence:.3f})")
            
            if 'bbox' in prediction:
                bbox = prediction['bbox']
                print(f"  Bounding box: x={bbox[0]}, y={bbox[1]}, width={bbox[2]}, height={bbox[3]}")
            elif 'x' in prediction and 'y' in prediction and 'width' in prediction and 'height' in prediction:
                print(f"  Bounding box: x={prediction['x']}, y={prediction['y']}, width={prediction['width']}, height={prediction['height']}")
    else:
        print("No destination predictions found above confidence threshold 0.1")
    
    return result, high_confidence_predictions

def main(image_path):
    # Ensure data directories exist
    ensure_data_directories()
    
    client = InferenceHTTPClient(
        api_url="https://serverless.roboflow.com",
        api_key="DSd1LnH4byKZqx8JekgA"
    )

    base_name = os.path.splitext(os.path.basename(image_path))[0]
    
    # Run source workflow
    source_result, source_prediction = run_source_workflow(client, image_path, base_name)
    
    # Run destination workflow
    destination_result, destination_predictions = run_destination_workflow(client, image_path, base_name)
    
    # Draw combined annotations on single image and save to data/annotated directory
    output_path = f"data/annotated/{base_name}_combined_annotated.jpg"
    success = draw_combined_annotations(image_path, source_prediction, destination_predictions, output_path)
    
    if success:
        print(f"Successfully created combined annotated image: {output_path}")
    else:
        print("Failed to create combined annotated image")
    
    return {
        'source_result': source_result,
        'destination_result': destination_result,
        'source_prediction': source_prediction,
        'destination_predictions': destination_predictions
    }

if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) != 1:
        print("Usage: python final_label.py <image_path>")
        sys.exit(1)
    image_path = args[0]
    results = main(image_path)



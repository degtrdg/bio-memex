import cv2
from pathlib import Path
from typing import List
from PIL import Image


class MovieGenerator:
    """Handles creation of GIF files from image batches"""
    
    def __init__(self, output_dir: str = "batch_cache"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
    
    def create_batch_movie(self, batch_files: List[str], batch_num: int, duration: int = 800) -> None:
        """Create a GIF file from the current batch of images (overwrites same filename)"""
        if not batch_files:
            return
        
        # Create both: current_batch.gif (overwriting) and batch_XXX_movie.gif (persistent)
        current_gif_path = self.output_dir / "current_batch.gif"
        batch_gif_path = self.output_dir / f"batch_{batch_num:03d}_movie.gif"
        
        # Load images with PIL for GIF creation
        images = []
        for img_path in batch_files:
            try:
                img = Image.open(img_path)
                # Resize to reasonable size for GIF
                img.thumbnail((800, 600), Image.Resampling.LANCZOS)
                images.append(img)
            except Exception as e:
                print(f"Warning: Could not load image {img_path}: {e}")
        
        if not images:
            print("No valid images found for GIF creation")
            return
        
        # Create both GIFs
        try:
            # Current batch (overwriting)
            images[0].save(
                current_gif_path,
                save_all=True,
                append_images=images[1:],
                duration=duration,
                loop=0,
                optimize=True
            )
            
            # Persistent batch GIF
            images[0].save(
                batch_gif_path,
                save_all=True,
                append_images=images[1:],
                duration=duration,
                loop=0,
                optimize=True
            )
            
            print(f"Created GIFs: {current_gif_path} and {batch_gif_path} ({len(images)} frames)")
        except Exception as e:
            print(f"Error creating GIF: {e}")
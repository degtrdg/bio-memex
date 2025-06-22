import glob
import os
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv
from google import genai
from google.genai import types

from video_understanding.models import SimpleVideoAnalysis
from video_understanding.prompts import create_stateful_prompt

load_dotenv()


class StatefulTester:
    """Handles loading images in batches and maintaining state across iterations"""

    def __init__(self, images_folder: str, batch_size: int = 5):
        self.client = genai.Client(api_key=os.getenv("GOOGLE_GENERATIVE_AI_API_KEY"))
        self.images_folder = Path(images_folder)
        self.batch_size = batch_size
        self.current_batch = 0
        self.current_state = None  # Will hold the latest SimpleVideoAnalysis output
        # Get all image files sorted by name
        image_extensions = ["*.jpg", "*.jpeg", "*.png", "*.bmp"]
        self.image_files = []
        for ext in image_extensions:
            self.image_files.extend(glob.glob(str(self.images_folder / ext)))
        self.image_files.sort()

        print(f"Found {len(self.image_files)} images in {images_folder}")
        print(f"Will process in batches of {batch_size}")
        print(f"Total batches: {len(self.image_files) // batch_size}")

    def get_current_batch_files(self) -> List[str]:
        """Get the current batch of image file paths"""
        start_idx = self.current_batch * self.batch_size
        end_idx = start_idx + self.batch_size
        return self.image_files[start_idx:end_idx]

    def has_next_batch(self) -> bool:
        """Check if there are more batches to process"""
        return (self.current_batch * self.batch_size) < len(self.image_files)

    def create_batch_blobs(self, batch_files: List[str]) -> List[types.Part]:
        """Create inline blobs for batch of images"""
        image_parts = []
        for file_path in batch_files:
            if os.path.exists(file_path):
                with open(file_path, "rb") as f:
                    image_data = f.read()
                    # Determine MIME type based on file extension
                    ext = Path(file_path).suffix.lower()
                    mime_type = {
                        ".jpg": "image/jpeg",
                        ".jpeg": "image/jpeg",
                        ".png": "image/png",
                        ".bmp": "image/bmp",
                    }.get(ext, "image/jpeg")

                    blob = types.Blob(data=image_data, mime_type=mime_type)
                    part = types.Part(inline_data=blob)
                    image_parts.append(part)
            else:
                print(f"Warning: File not found: {file_path}")
        return image_parts

    def process_current_batch(self) -> Optional[SimpleVideoAnalysis]:
        """Process the current batch and update state"""
        if not self.has_next_batch():
            print("No more batches to process!")
            return None

        # Get current batch files
        batch_files = self.get_current_batch_files()
        print(f"\n=== BATCH {self.current_batch + 1} ===")
        print(f"Processing files: {[Path(f).name for f in batch_files]}")

        import time

        start_time = time.perf_counter()
        # Create inline blobs
        image_parts = self.create_batch_blobs(batch_files)
        end_time = time.perf_counter()
        print(f"Time taken to create image blobs: {end_time - start_time} seconds")

        if len(image_parts) != self.batch_size:
            print(f"Warning: Expected {self.batch_size} files, got {len(image_parts)}")

        # Create prompt with current state
        current_goal_state = (
            self.current_state.goal_state if self.current_state else None
        )
        current_current_state = (
            self.current_state.current_state if self.current_state else None
        )
        current_protocol_log = (
            self.current_state.protocol_log if self.current_state else None
        )
        current_warnings = self.current_state.warnings if self.current_state else None

        prompt = create_stateful_prompt(
            current_goal_state,
            current_current_state,
            current_protocol_log,
            current_warnings,
        )

        # Send to GenAI
        contents = types.Content(parts=image_parts + [types.Part(text=prompt)])

        start_time = time.perf_counter()
        response = self.client.models.generate_content(
            model="models/gemini-2.5-flash",
            contents=contents,
            config={
                "response_mime_type": "application/json",
                "response_schema": SimpleVideoAnalysis,
            },
        )
        end_time = time.perf_counter()
        print(f"Time taken to generate response: {end_time - start_time} seconds")

        # Update state with new output
        self.current_state = response.parsed
        self.current_batch += 1

        return response.parsed

    def print_current_state(self) -> None:
        """Print the current state in a readable format"""
        if not self.current_state:
            print("No state yet - run process_current_batch() first")
            return

        state: SimpleVideoAnalysis = self.current_state
        print(f"\n📝 THINKING: {state.thinking}")
        print(
            f"🎯 GOAL STATE: {state.goal_state if state.goal_state else 'Not defined'}"
        )
        print(
            f"🧪 CURRENT STATE: {state.current_state if state.current_state else 'Empty'}"
        )
        print(
            f"📋 PROTOCOL LOG: {state.protocol_log if state.protocol_log else 'No events'}"
        )
        print(f"⚠️  WARNINGS: {state.warnings if state.warnings else 'None'}")


def process_all_batches(tester: StatefulTester) -> None:
    """Process all remaining batches and show final state"""
    batch_count = 0
    while tester.has_next_batch():
        result = tester.process_current_batch()
        batch_count += 1
        print(f"Processed batch {batch_count}")

    print(f"\n🎉 Processed {batch_count} total batches!")
    print("\n=== FINAL STATE ===")
    tester.print_current_state()

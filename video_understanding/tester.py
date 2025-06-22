import glob
import os
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv
from google import genai
from google.genai import types

from video_understanding.batch_cache import BatchCache
from video_understanding.models import VideoAnalysis
from video_understanding.movie_generator import MovieGenerator
from video_understanding.prompts import create_stateful_prompt

load_dotenv()


class StatefulTester:
    """Handles loading images in batches and maintaining state across iterations"""

    def __init__(
        self,
        images_folder: str,
        batch_size: int = 5,
        downsample_rate: int = 5,
        start_batch: int = 0,
        cache_dir: str = "batch_cache",
    ):
        self.client = genai.Client(api_key=os.getenv("GOOGLE_GENERATIVE_AI_API_KEY"))
        self.images_folder = Path(images_folder)
        self.batch_size = batch_size
        self.downsample_rate = downsample_rate
        self.current_batch = start_batch
        self.cache = BatchCache(cache_dir)
        self.movie_gen = MovieGenerator(cache_dir)
        self.current_state = None  # Will hold the latest VideoAnalysis output
        self.persistent_goal_state = None  # Tracks goal state across batches
        self.persistent_current_state = None  # Accumulates current state across batches
        self.persistent_protocol_log = None  # Accumulates protocol log across batches
        self.persistent_warnings = None  # Accumulates warnings across batches
        # Get all image files sorted by name
        image_extensions = ["*.jpg", "*.jpeg", "*.png", "*.bmp"]
        all_image_files = []
        for ext in image_extensions:
            all_image_files.extend(glob.glob(str(self.images_folder / ext)))
        all_image_files.sort()

        # Downsample by taking every nth image
        self.image_files = all_image_files[:: self.downsample_rate]

        print(
            f"Found {len(all_image_files)} total images, downsampled to {len(self.image_files)} (every {downsample_rate})"
        )
        print(f"Will process in batches of {batch_size}")
        print(f"Total batches: {len(self.image_files) // batch_size}")
        print(f"Starting from batch: {start_batch}")

        # Load previous state if starting from a specific batch
        self._load_cached_state(start_batch)

    def get_current_batch_files(self) -> List[str]:
        """Get the current batch of image file paths"""
        start_idx = self.current_batch * self.batch_size
        end_idx = start_idx + self.batch_size
        return self.image_files[start_idx:end_idx]

    def has_next_batch(self) -> bool:
        """Check if there are more batches to process"""
        return (self.current_batch * self.batch_size) < len(self.image_files)

    def create_batch_blobs(self, batch_files: List[str]) -> List[types.Part]:
        """Create inline blobs for batch of images and print total bytes"""
        image_parts = []
        total_bytes = 0
        per_file_bytes = []
        for file_path in batch_files:
            if os.path.exists(file_path):
                with open(file_path, "rb") as f:
                    image_data = f.read()
                    file_size = len(image_data)
                    total_bytes += file_size
                    per_file_bytes.append((file_path, file_size))
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
        print(f"Total image bytes in batch: {total_bytes} bytes")
        for fname, fbytes in per_file_bytes:
            print(f"  {Path(fname).name}: {fbytes} bytes")
        return image_parts

    def _load_cached_state(self, target_batch: int) -> None:
        """Load accumulated state up to the target batch from cache"""
        cached_state = self.cache.load_state_up_to_batch(target_batch)
        if cached_state:
            self.persistent_goal_state = cached_state["persistent_goal_state"]
            self.persistent_current_state = cached_state["persistent_current_state"]
            self.persistent_protocol_log = cached_state["persistent_protocol_log"]
            self.persistent_warnings = cached_state["persistent_warnings"]

    def process_current_batch(self) -> Optional[VideoAnalysis]:
        """Process the current batch and update state"""
        if not self.has_next_batch():
            print("No more batches to process!")
            return None

        # Get current batch files
        batch_files = self.get_current_batch_files()
        batch_num = self.current_batch
        print(f"\n=== BATCH {batch_num + 1} ===")
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
        # Use persistent states for prompt (preserves/accumulates across batches)

        prompt = create_stateful_prompt(
            self.persistent_goal_state,
            self.persistent_current_state,
            self.persistent_protocol_log,
            self.persistent_warnings,
            len(batch_files),
        )
        with open("prompt.txt", "w") as f:
            f.write(prompt)
        print(f"Prompt saved to prompt.txt")

        # Send to GenAI
        contents = types.Content(parts=image_parts + [types.Part(text=prompt)])

        # Save debug info before making the call
        prompt_length = len(prompt)
        print(f"Prompt length: {prompt_length} characters")

        debug_file = f"debug_batch_{batch_num:03d}.txt"
        with open(debug_file, "w") as f:
            f.write(f"BATCH {batch_num} DEBUG INFO\n")
            f.write(f"Prompt length: {prompt_length}\n")
            f.write(
                f"Persistent goal state length: {len(str(self.persistent_goal_state)) if self.persistent_goal_state else 0}\n"
            )
            f.write(
                f"Persistent current state length: {len(str(self.persistent_current_state)) if self.persistent_current_state else 0}\n"
            )
            f.write(
                f"Persistent protocol log length: {len(str(self.persistent_protocol_log)) if self.persistent_protocol_log else 0}\n"
            )
            f.write(
                f"Persistent warnings length: {len(str(self.persistent_warnings)) if self.persistent_warnings else 0}\n"
            )
            f.write(f"\n--- FULL PROMPT ---\n{prompt}")
        print(
            self.client.models.count_tokens(
                model="models/gemini-2.5-pro", contents=contents
            )
        )
        # count
        start_time = time.perf_counter()
        response = self.client.models.generate_content(
            model="models/gemini-2.5-pro",
            contents=contents,
            config={
                "response_mime_type": "application/json",
                "response_schema": VideoAnalysis,
            },
        )
        print(response.usage_metadata)
        end_time = time.perf_counter()
        print(f"Time taken to generate response: {end_time - start_time} seconds")

        # Update state with new output
        self.current_state = response.parsed

        # Update persistent states based on response (with defensive type checking)
        parsed = response.parsed

        # Goal state: only update if provided (preserve previous)
        if (
            hasattr(parsed, "goal_state")
            and getattr(parsed, "goal_state", None) is not None
        ):
            self.persistent_goal_state = parsed.goal_state

        # Current state: merge/update wells if provided (accumulate)
        if (
            hasattr(parsed, "current_state")
            and getattr(parsed, "current_state", None) is not None
        ):
            new_current_state = parsed.current_state
            if self.persistent_current_state is None:
                self.persistent_current_state = new_current_state
            else:
                # Merge well states - update existing wells or add new ones
                existing_wells = {
                    well.well_id: well for well in self.persistent_current_state
                }
                for new_well in new_current_state:
                    existing_wells[new_well.well_id] = new_well
                self.persistent_current_state = list(existing_wells.values())

        # Protocol log: append if provided (accumulate)
        if (
            hasattr(parsed, "protocol_log")
            and getattr(parsed, "protocol_log", None) is not None
        ):
            new_protocol_log = parsed.protocol_log
            if self.persistent_protocol_log is None:
                self.persistent_protocol_log = new_protocol_log
            else:
                self.persistent_protocol_log += "\n" + new_protocol_log

        # Warnings: extend list if provided (accumulate)
        if (
            hasattr(parsed, "warnings")
            and getattr(parsed, "warnings", None) is not None
        ):
            new_warnings = parsed.warnings
            if self.persistent_warnings is None:
                self.persistent_warnings = new_warnings
            else:
                self.persistent_warnings.extend(new_warnings)

        # Cache the batch results
        response_dict = (
            response.parsed.model_dump()
            if hasattr(response.parsed, "model_dump")
            else dict(response.parsed)
        )
        persistent_states = {
            "persistent_goal_state": self.persistent_goal_state,
            "persistent_current_state": self.persistent_current_state,
            "persistent_protocol_log": self.persistent_protocol_log,
            "persistent_warnings": self.persistent_warnings,
        }
        self.cache.save_batch_cache(batch_num, response_dict, persistent_states)

        # Now save all synchronized files for current batch (GIF, prompt, output)
        self._save_synchronized_files(batch_files, batch_num, prompt, response.parsed)

        self.current_batch += 1

        return response.parsed

    def _save_synchronized_files(
        self, batch_files: List[str], batch_num: int, prompt: str, response_data
    ) -> None:
        """Save GIF, prompt, and output.json all synchronized for current batch"""
        # Create GIF for current batch
        self.movie_gen.create_batch_movie(batch_files, batch_num)

        # Save current prompt
        with open("current_prompt.txt", "w") as f:
            f.write(prompt)

        # Save current output
        with open("current_output.json", "w") as f:
            if hasattr(response_data, "model_dump"):
                f.write(response_data.model_dump_json(indent=2))
            else:
                import json

                f.write(json.dumps(response_data, indent=2, default=str))

        print(
            f"Synchronized files saved: current_batch.gif, current_prompt.txt, current_output.json"
        )

    def print_current_state(self) -> None:
        """Print the current state in a readable format"""
        if not self.current_state:
            print("No state yet - run process_current_batch() first")
            return

        state = self.current_state
        print(f"\n📝 THINKING: {getattr(state, 'thinking', 'N/A')}")
        print(f"🎯 GOAL STATE: {self.persistent_goal_state or 'Not defined'}")
        print(f"🧪 CURRENT STATE: {self.persistent_current_state or 'Empty'}")
        print(f"📋 PROTOCOL LOG: {self.persistent_protocol_log or 'No events'}")
        print(f"⚠️  WARNINGS: {self.persistent_warnings or 'None'}")


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

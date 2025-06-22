#!/usr/bin/env python3
"""
Run all batches and then create the HTML viewer to see everything side by side
"""

from video_understanding.batch_viewer import create_batch_viewer
from video_understanding.tester import StatefulTester, process_all_batches


def main():
    # Configure your settings here
    images_folder = "videos/full_fps"  # UPDATE THIS PATH
    batch_size = 80
    start_batch = 0  # Start from beginning, or set to specific batch number

    print("🚀 Starting batch processing...")
    print(f"Images folder: {images_folder}")
    print(f"Batch size: {batch_size}")
    print(f"Starting from batch: {start_batch}")

    # Initialize tester
    tester = StatefulTester(
        images_folder=images_folder, batch_size=batch_size, start_batch=start_batch
    )

    # Process all batches
    print("\n📊 Processing all batches...")
    try:
        process_all_batches(tester)
        print("\n✅ All batches processed successfully!")
    except Exception as e:
        print(f"\n❌ Processing stopped at batch {tester.current_batch} due to error:")
        print(f"Error: {e}")
        print("\n📊 Creating viewer with batches processed so far...")

    # Create the HTML viewer (even if some batches failed)
    print("\n🎬 Creating batch viewer...")
    create_batch_viewer()

    print("\n✅ Viewer created!")
    print("📁 Files created:")
    print("  - batch_cache/ (contains all cached data and GIFs)")
    print("  - batch_viewer.html (open this in your browser)")
    print(f"  - Processed {tester.current_batch} batches before stopping")
    print(
        "\n🌐 Open batch_viewer.html in your browser to see all batches side by side!"
    )


if __name__ == "__main__":
    main()

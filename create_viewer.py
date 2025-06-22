#!/usr/bin/env python3
"""
Simple script to create the batch viewer HTML file
Run this after processing batches to see them all side by side
"""

from video_understanding.batch_viewer import create_batch_viewer

if __name__ == "__main__":
    print("Creating batch viewer...")
    create_batch_viewer()
    print("Done! Open batch_viewer.html in your browser")
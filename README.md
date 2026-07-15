# AirCursor

AirCursor is a computer vision project that enables hands-free cursor control on macOS using a standard webcam. It tracks hand movements in real time and translates them into mouse interactions, exploring a natural and intuitive way of interacting with a computer.

This project is being built publicly from day one, with every milestone committed and pushed to GitHub. The primary goal is not only to create a functional application but also to document the engineering process behind building a real-time computer vision system from scratch.

## About the Project

The initial MVP focuses on four core capabilities:

* Detect a hand from the webcam feed.
* Track the user's index fingertip.
* Activate a dedicated "Cursor Mode" using a hand gesture.
* Control the macOS cursor using the tracked fingertip.

Once the MVP is complete, the project will be extended with features such as gesture-based clicks, scrolling, drag-and-drop, custom gesture mapping, and AI-powered gesture recognition.

## Tech Stack

AirCursor is currently being developed with:

* **Python** — Primary programming language
* **OpenCV** — Webcam access and image processing
* **MediaPipe** — Real-time hand detection and landmark tracking
* **NumPy** — Mathematical operations and coordinate calculations
* **PyAutoGUI / Quartz** — Cursor control on macOS
* **uv** — Python package and environment management

> **Note:** This README is intentionally minimal and will evolve alongside the project as new features, documentation, demos, and architectural decisions are added.

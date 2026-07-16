# KSP Flight Data Visualizer
*A lightweight 3D visualizer for analyzing KSP flight data.*

## Description
Kerbal Space Program's kOS mod provides plenty of freedom in the way of changing the game the way is played, including data logging and processing. This data is essential for analyzing flight characteristics and control data, but visualizing it off numbers on a spreadsheet is difficult.

This tool serves to quickly intake time-indexed spreadsheet data from a dedicated kOS logging script and convert it for visualization in a controllable 3D environment for more intuitive and clear analysis for craft design.

## Project Purpose
This repository was primarily created as a hands-on project to learn the fundamentals of application design, data parsing, and development. While there are fully featured, established flight-data tools available in the KSP and broader enginnering communities, this project served as a practical sandbox for me to tackle real-world software engineering challenges from scratch.

## Primary Libraries Used
- numpy
- pandas
- PyQt5
- pyvista & pyvistaqt

## Other
This tool has been primarily designed for usage on Linux through the X11 display protocol.
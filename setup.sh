#!/bin/bash
echo "Setting up A-Star Visualizer..."
conda env create -f environment.yml
echo "Setup complete."
echo "Activate with: conda activate astar"
echo "Then run: python run.py"
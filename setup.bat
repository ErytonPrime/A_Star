@echo off
echo Setting up A-Star Visualizer...
call conda env create -f environment.yml
echo Setup complete.
echo Activate with: conda activate astar
echo Then run: python run.py
pause
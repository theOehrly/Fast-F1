"""This script will run flake8 but only check for then new line length limit of
79 characters. The checks are limited to the currently staged changes."""
import os
import subprocess
import sys

print(os.getcwd())


p_diff = subprocess.Popen(["git", "diff", "--cached", "-U0", "--relative"],
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

p_flake8 = subprocess.Popen(["flake8", "--max-line-length", "79",
                             "--select", "E501", "--diff",
                             "fastf1 examples scripts"],
                            stdin=p_diff.stdout)
p_flake8.wait()
sys.exit(p_flake8.returncode)

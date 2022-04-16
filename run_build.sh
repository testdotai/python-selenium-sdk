#!/bin/bash
# NOTE: Need to pip install build & twine

rm -rf dist/
rm -rf build/
rm -rf test_ai/*.egg-info

# NOTE: If you get a version issue where it can't find the regex go in and add check if version == None
python3 -m build

# Upload build
# NOTE: To upload put username __token__ then password put token
python3 -m twine upload dist/*

# Cleanup
rm -rf dist/
rm -rf build/
rm -rf test_ai/*.egg-info
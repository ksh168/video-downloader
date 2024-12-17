#!/bin/bash

# Define the path to the downloads directory
DOWNLOADS_DIR="/home/azureuser/folder1/downloads"

# Find and delete files older than 1 hour
# Delete files older than 1 hour
find "$DOWNLOADS_DIR" -type f -mmin +60 -exec rm -f {} \;

# Delete empty directories older than 1 hour
find "$DOWNLOADS_DIR" -type d -empty -mmin +60 -exec rmdir {} \;
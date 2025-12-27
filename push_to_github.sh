#!/bin/bash

# Configure Git Identity (Local to this repo)
echo "Configuring Git identity..."
git config user.name "Arnav Saxena"
git config user.email "Arnav-Saxena-India@users.noreply.github.com"

# Initialize Git
if [ ! -d ".git" ]; then
    echo "Initializing Git repository..."
    git init
fi

# Add all files
echo "Adding files..."
git add .

# Initial Commit
echo "Committing..."
git commit -m "Initial commit: Adaptive Competitive Programming Coach" || echo "Nothing to commit"

# Rename branch to main
git branch -M main

# Add Remote (reset if exists)
echo "Setting remote origin..."
git remote remove origin 2>/dev/null || true
git remote remove origin 2>/dev/null || true
echo "Setting remote origin..."
git remote add origin https://github.com/Arnav-Saxena-India/CP-COACH.git

# Push
echo "Pushing to GitHub (Force Overwrite)..."
git push -u origin main --force

if [ $? -ne 0 ]; then
    echo ""
    echo "❌ PUSH FAILED!"
    echo "The provided Personal Access Token may be invalid or expired,"
    echo "or there is a connection issue."
    echo ""
    exit 1
fi

echo "Done! If push failed, check your GitHub credentials."

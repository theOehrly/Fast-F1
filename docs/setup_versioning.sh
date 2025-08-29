#!/bin/bash

# This script correctly organizes multiple versions of the documentation
# in the _build/html folder such that the latest released version is in
# the web root and older versions and a dev build are in a subdirectory.
# It also generates a JSON file for the version switcher of the theme.
#
# You can run this script manually, if contents of the build directory
# were changed. The script is run automatically when a versioned documentation
# build is created with "make version-build"

# get the version that is currently in the root directory and move it out of
# the way into its version specific subdirectory
CURRENT_VERSION=""
if [ -f "_build/html/.version" ]; then
    CURRENT_VERSION=$(cat "_build/html/.version")

    echo "Current active version: $CURRENT_VERSION"

    rm -rf "_build/html/versions/$CURRENT_VERSION"
    mkdir -p "_build/html/versions/$CURRENT_VERSION"
    rsync -av --quiet --exclude='versions' "_build/html/" "_build/html/versions/$CURRENT_VERSION/"
fi

# if a new version is in the tmp build directory, grab it and move it to its
# version specific subdirectory
ADDED_VERSION=""
if [ -f "_build/tmp/.version" ]; then
    ADDED_VERSION=$(cat "_build/tmp/.version")

    echo "Added new version: $ADDED_VERSION"

    rm -r "_build/html/versions/$ADDED_VERSION"
    mkdir -p "_build/html/versions/$ADDED_VERSION"
    rsync -av --quiet --exclude='versions' "_build/tmp/" "_build/html/versions/$ADDED_VERSION"
    rm -rf "_build/tmp"
fi

# Get a list of all versions based on all versions in the versions
# subdirectory and find latest numeric version
VERSIONS=$(ls -1 "_build/html/versions/" 2>/dev/null)
LATEST_VERSION=""
for version in $VERSIONS; do
    if [[ $version =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
        if [[ "$version" > "$LATEST_VERSION" ]]; then
            LATEST_VERSION=$version
        fi
    fi
done

# Copy the contents of the latest version directory to the root directory
if [ -n "$LATEST_VERSION" ]; then
    rsync -av --quiet "_build/html/versions/$LATEST_VERSION/" "_build/html/"
    rm -rf "_build/html/versions/$LATEST_VERSION"
fi

# generate versions.json in the required format for the pydata-sphinx-theme switcher
# write the JSON file to the _static directory in the root
echo "$VERSIONS" | tr ' ' '\n' | jq -R -s 'split("\n")[:-1] | map({
    version: .,
    url: (if . == "'"$LATEST_VERSION"'" then "/" else "/versions/" + . + "/" end),
    preferred: (if . == "'"$LATEST_VERSION"'" then true else false end)
})' > "_build/html/_static/versions.json"

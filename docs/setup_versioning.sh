#!/bin/bash

CURRENT_VERSION=""
if [ -f "_build/html/.version" ]; then
    CURRENT_VERSION=$(cat "_build/html/.version")

    echo "Current active version: $CURRENT_VERSION"

    rm -rf "_build/html/versions/$CURRENT_VERSION"
    mkdir -p "_build/html/versions/$CURRENT_VERSION"
    rsync -av --quiet --exclude='versions' "_build/html/" "_build/html/versions/$CURRENT_VERSION/"
fi

ADDED_VERSION=""
if [ -f "_build/tmp/.version" ]; then
    ADDED_VERSION=$(cat "_build/tmp/.version")

    echo "Added new version: $ADDED_VERSION"

    rm -r "_build/html/versions/$ADDED_VERSION"
    mkdir -p "_build/html/versions/$ADDED_VERSION"
    rsync -av --quiet --exclude='versions' "_build/tmp/" "_build/html/versions/$ADDED_VERSION"
    rm -rf "_build/tmp"
fi

# Get list of all versions and find latest numeric version
VERSIONS=$(ls -1 "_build/html/versions/" 2>/dev/null)
LATEST_VERSION=""
for version in $VERSIONS; do
    if [[ $version =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
        if [[ "$version" > "$LATEST_VERSION" ]]; then
            LATEST_VERSION=$version
        fi
    fi
done

# generate versions.json
# format of versions.json:
#   - one entry for each version
#   - current version is specified
#   - current version has empty url, all others have /versions/<version>
#
# {
#     "current": "v1.2.3",
#     "versions": [
#         {
#             "version": "v1.2.3",
#             "url": "",
#             "title": "v1.2.3"
#         },
#         {
#             "version": "dev",
#             "url": "/versions/dev/",
#             "title": "dev"
#         }
#     ]
# }

#         url: if . == "'"$LATEST_VERSION"'" then "" else "/versions/" + . + "/" end,
VERSIONS_JSON=$(echo "$VERSIONS" | tr ' ' '\n' | grep -v '^$' | jq -R -s 'split("\n")[:-1] | {
    current: "'"$LATEST_VERSION"'",
    versions: map({
        version: .,
        url: (if . == "'"$LATEST_VERSION"'" then "" else "/versions/" + . + "/" end),
        title: .
    })
}')

# Copy versions.json to each version directory
for version in $VERSIONS; do
    # Write versions.json to each static directory
    echo "$VERSIONS_JSON" > "_build/html/versions/$version/_static/versions.json"
done

# Copy the contents of the latest version directory to the root directory
if [ -n "$LATEST_VERSION" ]; then
    rsync -av --quiet "_build/html/versions/$LATEST_VERSION/" "_build/html/"
    rm -rf "_build/html/versions/$LATEST_VERSION"
fi


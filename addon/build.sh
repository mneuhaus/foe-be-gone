#!/bin/bash

# Build Home Assistant Add-on for Foe Be Gone

set -e

ADDON_NAME="foe-be-gone"
VERSION="2.0.0"
ARCHITECTURES=("amd64" "aarch64" "armv7")

echo "Building Foe Be Gone Home Assistant Add-on v${VERSION}"

# Create build directory
BUILD_DIR="build"
rm -rf ${BUILD_DIR}
mkdir -p ${BUILD_DIR}

# Copy addon files
cp -r addon/* ${BUILD_DIR}/
cp -r app ${BUILD_DIR}/
cp -r alembic ${BUILD_DIR}/
cp -r public ${BUILD_DIR}/
cp pyproject.toml ${BUILD_DIR}/
cp uv.lock ${BUILD_DIR}/ 2>/dev/null || true
cp alembic.ini ${BUILD_DIR}/

# Copy logo if exists
if [ -f "public/logo.jpg" ]; then
    cp public/logo.jpg ${BUILD_DIR}/logo.png
fi

# Build for each architecture
for ARCH in "${ARCHITECTURES[@]}"; do
    echo "Building for ${ARCH}..."
    
    # Use Home Assistant builder
    docker run --rm --privileged \
        -v ${PWD}/${BUILD_DIR}:/data \
        -v /var/run/docker.sock:/var/run/docker.sock:ro \
        ghcr.io/home-assistant/amd64-builder \
        --target /data \
        --${ARCH} \
        --docker-hub ghcr.io \
        --image ${ADDON_NAME}-${ARCH} \
        --version ${VERSION}
done

echo "Build complete! Add-on packages created in ${BUILD_DIR}/"
echo ""
echo "To test locally:"
echo "1. Copy ${BUILD_DIR}/ to /addons/${ADDON_NAME}/ on your HA instance"
echo "2. Reload add-on store"
echo "3. Install and configure the add-on"
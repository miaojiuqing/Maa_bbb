#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
REPO_ROOT=$(CDPATH= cd -- "${SCRIPT_DIR}/.." && pwd)

IMAGE_REPOSITORY=${IMAGE_REPOSITORY:-ghcr.io/miaojiuqing/maa_bbb}
PLATFORM=${PLATFORM:-linux/amd64}
VERSION=${VERSION:-}

if [ -z "${VERSION}" ]; then
    VERSION=$(git -C "${REPO_ROOT}" describe --tags --abbrev=0 --match 'v*') || {
        printf '%s\n' 'Unable to determine the latest v* Git tag. Set VERSION explicitly.' >&2
        exit 1
    }
fi

case "${VERSION}" in
    v[0-9]*.[0-9]*.[0-9]*) ;;
    *)
        printf 'Invalid VERSION: %s (expected a v-prefixed semantic version)\n' "${VERSION}" >&2
        exit 1
        ;;
esac

MAJOR_VERSION=${VERSION%%.*}

set -- docker buildx build \
    --file "${SCRIPT_DIR}/Dockerfile" \
    --platform "${PLATFORM}" \
    --tag "${IMAGE_REPOSITORY}:${VERSION}" \
    --load \
    "$@"

case "${VERSION}" in
    *-*) ;;
    *)
        set -- "$@" \
            --tag "${IMAGE_REPOSITORY}:${MAJOR_VERSION}" \
            --tag "${IMAGE_REPOSITORY}:latest"
        ;;
esac

case "${PLATFORM}" in
    *,*)
        printf '%s\n' 'Local builds support only one platform.' >&2
        exit 1
        ;;
esac

printf 'Building %s for %s\n' "${VERSION}" "${PLATFORM}"
set -- "$@" "${REPO_ROOT}"
exec "$@"

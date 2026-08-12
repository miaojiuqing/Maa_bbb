# syntax=docker/dockerfile:1

# Common download tools. Individual release stages below remain independently
# cacheable when their respective version changes.
FROM debian:12 AS download-base
RUN apt-get update \
    && apt-get install --yes --no-install-recommends \
        ca-certificates \
        curl \
        unzip \
    && rm -rf /var/lib/apt/lists/*

FROM download-base AS maafw-runtime

ARG TARGETARCH
ARG MAAFRAMEWORK_VERSION=v5.12.3

WORKDIR /assets

RUN set -eux; \
    case "${TARGETARCH}" in \
        amd64) maa_arch=x86_64 ;; \
        arm64) maa_arch=aarch64 ;; \
        *) echo "Unsupported target architecture: ${TARGETARCH}" >&2; exit 1 ;; \
    esac; \
    mkdir deps; \
    curl --fail --location --silent --show-error \
        --output /tmp/maafw.zip \
        "https://github.com/MaaXYZ/MaaFramework/releases/download/${MAAFRAMEWORK_VERSION}/MAA-linux-${maa_arch}-${MAAFRAMEWORK_VERSION}.zip"; \
    unzip -q /tmp/maafw.zip -d deps; \
    if [ ! -d deps/bin ]; then \
        framework_root="$(find deps -mindepth 1 -maxdepth 1 -type d -exec test -d '{}/bin' \; -print -quit)"; \
        test -n "${framework_root}"; \
        mv "${framework_root}/bin" deps/; \
        mv "${framework_root}/share" deps/; \
        rmdir "${framework_root}" || true; \
    fi; \
    rm -rf /tmp/maafw.zip

FROM download-base AS mfw-runtime

ARG TARGETARCH
ARG MFW_VERSION=v4.8.23

WORKDIR /assets

RUN set -eux; \
    case "${TARGETARCH}" in \
        amd64) maa_arch=x86_64 ;; \
        arm64) maa_arch=aarch64 ;; \
        *) echo "Unsupported target architecture: ${TARGETARCH}" >&2; exit 1 ;; \
    esac; \
    mkdir MFWCFA; \
    curl --fail --location --silent --show-error \
        --output /tmp/mfw.zip \
        "https://github.com/overflow65537/MFW-PyQt6/releases/download/${MFW_VERSION}/MFW-PyQt6-linux-${maa_arch}-${MFW_VERSION}.zip"; \
    unzip -q /tmp/mfw.zip -d MFWCFA; \
    rm -rf /tmp/mfw.zip

FROM download-base AS virtualgl-runtime

ARG TARGETARCH
ARG VIRTUALGL_VERSION=3.1.4

WORKDIR /assets

RUN set -eux; \
    case "${TARGETARCH}" in \
        amd64) \
            virtualgl_arch=amd64; \
            virtualgl_sha256=02edc6b599571c385389af1a006f07a70c298e1d97c580a9bfd4b39d835c51e6 \
            ;; \
        arm64) \
            virtualgl_arch=arm64; \
            virtualgl_sha256=5583e08ee5694d14c6ea0f25d2cfd73fa6d5077869c6645c334a948265a777bb \
            ;; \
        *) echo "Unsupported target architecture: ${TARGETARCH}" >&2; exit 1 ;; \
    esac; \
    curl --fail --location --silent --show-error \
        --output virtualgl.deb \
        "https://github.com/VirtualGL/virtualgl/releases/download/${VIRTUALGL_VERSION}/virtualgl_${VIRTUALGL_VERSION}_${virtualgl_arch}.deb"; \
    echo "${virtualgl_sha256}  virtualgl.deb" | sha256sum --check --strict

# Build the Maa_bbb release directory with only the tools needed for packaging.
FROM debian:12 AS builder

ARG TARGETARCH
ARG MFW_VERSION=v4.8.23

RUN apt-get update \
    && apt-get install --yes --no-install-recommends \
        python3 \
        python3-pip \
    && rm -rf /var/lib/apt/lists/* \
    && python3 -m pip install --no-cache-dir --break-system-packages json-with-comments

WORKDIR /src
COPY . /src
COPY --from=maafw-runtime /assets/deps /opt/maa-cache/deps
COPY --from=mfw-runtime /assets/MFWCFA /opt/maa-cache/MFWCFA

RUN set -eux; \
    case "${TARGETARCH}" in \
        amd64) maa_arch=x86_64 ;; \
        arm64) maa_arch=aarch64 ;; \
        *) echo "Unsupported target architecture: ${TARGETARCH}" >&2; exit 1 ;; \
    esac; \
    rm -rf deps MFWCFA install; \
    cp -a /opt/maa-cache/deps deps; \
    cp -a /opt/maa-cache/MFWCFA MFWCFA; \
    python3 tools/install.py "${MFW_VERSION}" linux "${maa_arch}"; \
    python3 tools/copy_mfwcfa_to_install.py; \
    chmod 755 install/MFW; \
    test -x install/MFW

# MFW v4.8.23 requires GLIBC_2.38.
FROM jlesage/baseimage-gui:debian-13-v4

COPY --from=virtualgl-runtime /assets/virtualgl.deb /tmp/virtualgl.deb

RUN if [ ! -d /var/log ]; then rm -f /var/log; fi \
    && mkdir -p /var/log \
    && apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install --yes --no-install-recommends \
        adb \
        cron \
        libdbus-1-3 \
        libegl1 \
        libgl1 \
        libglib2.0-0 \
        libgomp1 \
        libgssapi-krb5-2 \
        libice6 \
        libsm6 \
        libx11-xcb1 \
        libxcb-cursor0 \
        libxcb-icccm4 \
        libxcb-image0 \
        libxcb-keysyms1 \
        libxcb-randr0 \
        libxcb-render-util0 \
        libxcb-shape0 \
        libxcb-shm0 \
        libxcb-sync1 \
        libxcb-xfixes0 \
        libxcb-xinerama0 \
        libxcb-xkb1 \
        libxkbcommon0 \
        libxkbcommon-x11-0 \
        libxi6 \
        libxrender1 \
        fontconfig \
        fonts-noto-cjk \
        /tmp/virtualgl.deb \
    && rm -f /tmp/virtualgl.deb \
    && rm -rf /var/lib/apt/lists/*

ENV APP_NAME=Maa_bbb \
    ANDROID_USER_HOME=/config/mfw/android \
    DISPLAY_HEIGHT=720 \
    DISPLAY_WIDTH=1280 \
    HOME=/config/mfw \
    LANG=C.UTF-8 \
    NVIDIA_DRIVER_CAPABILITIES=graphics,utility \
    PYTHONDONTWRITEBYTECODE=1 \
    XDG_CACHE_HOME=/config/mfw/xdg/cache \
    XDG_CONFIG_HOME=/config/mfw/xdg/config \
    XDG_DATA_HOME=/config/mfw/xdg/data

COPY --from=builder /src/install/ /opt/maa-bbb/
COPY docker/rootfs/ /

RUN chmod 755 /startapp.sh /etc/cont-init.d/90-agent-ownership.sh \
    && install -D -m 755 /opt/maa-bbb/cron-service.sh /etc/services.d/cron/run \
    && printf '0\n' > /etc/services.d/cron/uid \
    && : > /etc/services.d/default/cron.dep \
    && ln -s /config/mfw /opt/maa-bbb/config \
    && mkdir -p /config \
    && ln -s /config/mfw/android /config/.android \
    && ln -s /config/mfw/debug /opt/maa-bbb/debug \
    && rm -rf /opt/maa-bbb/resource/announcement \
    && ln -s /config/mfw/resource/announcement /opt/maa-bbb/resource/announcement \
    && rm -rf /opt/maa-bbb/release_notes /opt/maa-bbb/report /opt/maa-bbb/bundle \
    && ln -s /config/mfw/release_notes /opt/maa-bbb/release_notes \
    && ln -s /config/mfw/report /opt/maa-bbb/report \
    && ln -s /config/mfw/bundle /opt/maa-bbb/bundle \
    && rm -rf /var/spool/cron/crontabs \
    && ln -s /config/mfw/crontabs /var/spool/cron/crontabs \
    && ! ldd /opt/maa-bbb/MFW | grep -q 'not found' \
    && ! ldd /opt/maa-bbb/libQt6Network.so.6 | grep -q 'not found' \
    && ! ldd /opt/maa-bbb/PySide6/qt-plugins/platforms/libqxcb.so | grep -q 'not found'

WORKDIR /opt/maa-bbb

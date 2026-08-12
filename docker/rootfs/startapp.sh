#!/bin/sh
set -eu

umask 027
mkdir -p \
    /config/mfw/android \
    /config/mfw/bundle \
    /config/mfw/debug \
    /config/mfw/release_notes \
    /config/mfw/report \
    /config/mfw/resource/announcement \
    /config/mfw/xdg/cache \
    /config/mfw/xdg/config \
    /config/mfw/xdg/data \
    /config/mfw/crontabs

chmod 1730 /config/mfw/crontabs

adb start-server

if [ "${GUI_GPU_ACCELERATION:-0}" = "1" ]; then
    export QSG_RHI_BACKEND="${QSG_RHI_BACKEND:-opengl}"
    exec /opt/VirtualGL/bin/vglrun \
        -d "${VGL_DISPLAY:-egl0}" \
        -c proxy \
        /opt/maa-bbb/MFW
fi

exec /opt/maa-bbb/MFW

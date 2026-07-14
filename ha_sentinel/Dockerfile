ARG BUILD_FROM
FROM $BUILD_FROM

RUN apk add --no-cache python3 py3-requests

COPY rootfs /
RUN chmod a+x /app/ha_sentinel.py /etc/services.d/ha-sentinel/run

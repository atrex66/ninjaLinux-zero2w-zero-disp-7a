# Build and run from the project root:
# docker build --target test -f packaging/Dockerfile -t automation-hal-test .
# docker build --target packages --output type=local,dest=dist -f packaging/Dockerfile .
ARG DEBIAN_RELEASE=trixie
FROM debian:${DEBIAN_RELEASE}-slim AS build
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential cmake ninja-build libboost-dev libudev-dev \
    python3-dev python3-yapps dpkg-dev && rm -rf /var/lib/apt/lists/*
WORKDIR /source
COPY . .
RUN cmake -S . -B /build -G Ninja -DPython3_EXECUTABLE=/usr/bin/python3 \
    -DCMAKE_BUILD_TYPE=Release && cmake --build /build -j2 \
    && cd /build && cpack && mkdir /packages && cp ./*.deb /packages/

FROM debian:${DEBIAN_RELEASE}-slim AS test
COPY --from=build /packages /packages
COPY tests /test
RUN apt-get update && apt-get install -y --no-install-recommends passwd /packages/*.deb \
    && rm -rf /var/lib/apt/lists/* && useradd -m -u 1000 tester \
    && /opt/automation-hal/bin/ahal compile --install /test/sdk_probe.comp
USER tester
RUN /usr/bin/python3 /test/integration.py

FROM scratch AS packages
COPY --from=build /packages/ /

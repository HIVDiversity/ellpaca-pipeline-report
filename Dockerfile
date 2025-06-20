FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

# Disable Python downloads, because we want to use the system interpreter
# across both images. If using a managed Python version, it needs to be
# copied from the build image into the final image; see `standalone.Dockerfile`
# for an example.
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=0
WORKDIR /app

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev
ADD . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# Then, use a final image without uv
FROM python:3.12-slim-bookworm AS release
# It is important to use the image that matches the builder, as the path to the
# Python executable must be the same, e.g., using `python:3.11-slim-bookworm`
# will fail.


RUN apt-get update && \
    apt-get install --no-install-suggests --no-install-recommends --yes procps && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# RUN cd /usr/local/bin/ && \
#     wget https://github.com/typst/typst/releases/download/v0.13.1/typst-x86_64-unknown-linux-musl.tar.xz && \
#     tar -xJf typst-x86_64-unknown-linux-musl.tar.xz

ADD lib/typst /usr/local/bin

# Copy the application from the builder
COPY --from=builder --chown=app:app /app /app

# Place executables in the environment at the front of the path
ENV PATH="/app/.venv/bin:$PATH"

#
## Reset the entrypoint, don't invoke `uv`
#ENTRYPOINT []
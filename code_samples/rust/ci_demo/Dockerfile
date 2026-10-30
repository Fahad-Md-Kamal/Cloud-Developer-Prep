# Multi-stage build: compile in a full toolchain image, ship only the binary.
FROM rust:1.99-alpine AS build
RUN apk add --no-cache musl-dev
WORKDIR /app
# 1) Cache dependencies: copy only the manifests and build a dummy main first.
COPY Cargo.toml Cargo.lock ./
RUN mkdir src && echo 'fn main() {}' > src/main.rs \
 && cargo build --release --locked && rm -rf src target/release/hello-ci* target/release/deps/hello_ci*
# 2) Build the real code (only this layer reruns when source changes).
COPY src ./src
RUN cargo build --release --locked

# Final image: no shell, no libc, no package manager. Only the static binary.
FROM scratch
COPY --from=build /app/target/release/hello-ci /hello-ci
USER 10001
ENTRYPOINT ["/hello-ci"]

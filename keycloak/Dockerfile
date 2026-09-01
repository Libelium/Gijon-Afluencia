# Build email MFA extension
#
# Every base image is pinned by digest as well as by tag: a tag can be moved, a digest
# cannot, so this is what makes the build reproducible and auditable. To move to a newer
# base, resolve the new digest first:
#   docker buildx imagetools inspect <image>:<tag> | grep Digest
FROM maven:3.9.9-eclipse-temurin-21@sha256:3a4ab3276a087bf276f79cae96b1af04f53731bec53fb2e651aca79e4b10211e AS ext-builder

WORKDIR /build

# Third-party MFA-by-e-mail authenticator, built from source.
#
# MFA_AUTHENTICATOR_COMMIT is the exact commit that gets built — the last one compatible
# with Keycloak 25.x.x. `git checkout <sha>` already fixes the tree, and the rev-parse
# check right after makes that explicit and fails the build if the clone did not land on
# it (a moved branch, a mirror, a shallow clone).
ARG MFA_AUTHENTICATOR_COMMIT=7dbcdf70d1dc862d49e567b46e66671dfaa7dff9

# Expected SHA256 of the provider jar. Empty by default, because a Maven build is not
# byte-for-byte reproducible across toolchains, so a hard-coded value would break the
# build on the next base-image bump. The build always PRINTS the digest of what it
# produced and stores it in the final image, next to the licence, as
# /opt/keycloak/licences/keycloak-2fa-email-authenticator-SHA256SUMS. Record that value
# here (or pass --build-arg MFA_JAR_SHA256=<sha256>) to make the build verify it.
ARG MFA_JAR_SHA256=""

RUN set -eu; \
    git clone https://github.com/mesutpiskin/keycloak-2fa-email-authenticator.git .; \
    git checkout "${MFA_AUTHENTICATOR_COMMIT}"; \
    test "$(git rev-parse HEAD)" = "${MFA_AUTHENTICATOR_COMMIT}"; \
    mvn clean package -DskipTests

# Digest of the artefacts that will be redistributed inside the final image.
RUN set -eu; \
    mkdir -p /licences; \
    (cd /build/target && sha256sum *.jar) > /licences/keycloak-2fa-email-authenticator-SHA256SUMS; \
    echo '--- provider jar digests ---'; \
    cat /licences/keycloak-2fa-email-authenticator-SHA256SUMS; \
    if [ -n "${MFA_JAR_SHA256:-}" ]; then \
      awk '{print $1}' /licences/keycloak-2fa-email-authenticator-SHA256SUMS \
        | grep -qx "${MFA_JAR_SHA256}" \
        || { echo "ERROR: no built jar matches MFA_JAR_SHA256=${MFA_JAR_SHA256}"; exit 1; }; \
      echo "Provider jar digest verified against MFA_JAR_SHA256."; \
    fi

# The jar is redistributed inside the final image, and Apache-2.0 section 4 requires
# shipping a copy of the licence (and the NOTICE file, if the project has one) with
# it. Staged in its own directory so the COPY below never depends on which of the two
# files upstream happens to carry at this commit.
RUN mkdir -p /licences \
    && for f in LICENSE LICENSE.txt NOTICE NOTICE.txt; do \
         [ -f "$f" ] && cp "$f" "/licences/keycloak-2fa-email-authenticator-$f"; \
       done; true


FROM quay.io/keycloak/keycloak:25.0.0@sha256:1052ebec7bfbbdc52240cc4643616fbf3a74199b124bdd884531ede08f6ff4a5 AS builder

ENV KC_HEALTH_ENABLED=true
ENV KC_METRICS_ENABLED=true
ENV KC_FEATURES=token-exchange
ENV KC_DB=postgres

COPY --from=ext-builder /build/target/*.jar /opt/keycloak/providers/

WORKDIR /opt/keycloak
RUN /opt/keycloak/bin/kc.sh build


FROM registry.access.redhat.com/ubi9@sha256:25a147defd01e19674714f55d17538c8dbe55d8c305fa157ecc3f9c8977b05b6 AS ubi-micro-build
RUN mkdir -p /mnt/rootfs
RUN dnf install --installroot /mnt/rootfs curl --releasever 9 --setopt install_weak_deps=false --nodocs -y && \
    dnf --installroot /mnt/rootfs clean all && \
    rpm --root /mnt/rootfs -e --nodeps setup


# Final image. SAME version and digest as the builder stage above: they used to differ
# (25.0.0 vs the floating 25.0), so the image that built the providers and the image that
# ran them were not guaranteed to be the same Keycloak.
FROM quay.io/keycloak/keycloak:25.0.0@sha256:1052ebec7bfbbdc52240cc4643616fbf3a74199b124bdd884531ede08f6ff4a5
COPY --from=builder /opt/keycloak/ /opt/keycloak/
COPY --from=ubi-micro-build /mnt/rootfs /

# Licence of the bundled third-party provider (Apache-2.0 section 4). See NOTICE.md.
COPY --from=ext-builder /licences/ /opt/keycloak/licences/

COPY ./pidtheme /opt/keycloak/themes/pidtheme
COPY ./pidtheme-mobile /opt/keycloak/themes/pidtheme-mobile
COPY realm.json /opt/keycloak/data/import/realm.json
COPY change-password-client.json /opt/keycloak/data/import/client/change-password-client.json

# Group-writable so the bootstrap's `sed -i` (env-placeholder substitution at runtime,
# as uid 1000 / gid 0) can create its temp file; otherwise it fails silently.
USER root
RUN chmod -R g+rwX /opt/keycloak/data/import /opt/keycloak/themes/pidtheme
USER 1000

# This command runs Keycloak in production mode and
# imports the realm configuration from the /opt/keycloak/data/import/realm.json file
# REF: https://www.keycloak.org/server/importExport
COPY --chmod=755 ./bootstrap-keycloak-backend.sh /opt/keycloak/docker-entrypoint.d/bootstrap-keycloak-backend.sh

ENTRYPOINT ["/opt/keycloak/docker-entrypoint.d/bootstrap-keycloak-backend.sh"]
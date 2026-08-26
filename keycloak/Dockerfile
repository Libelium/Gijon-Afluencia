# Build email MFA extension
FROM maven:3.9.9-eclipse-temurin-21 AS ext-builder

WORKDIR /build

# Pinned to this commit because it is the last version compatible with Keycloak 25.x.x
RUN git clone https://github.com/mesutpiskin/keycloak-2fa-email-authenticator.git . \
    && git checkout 7dbcdf70d1dc862d49e567b46e66671dfaa7dff9 \
    && mvn clean package -DskipTests

# The jar is redistributed inside the final image, and Apache-2.0 section 4 requires
# shipping a copy of the licence (and the NOTICE file, if the project has one) with
# it. Staged in its own directory so the COPY below never depends on which of the two
# files upstream happens to carry at this commit.
RUN mkdir -p /licences \
    && for f in LICENSE LICENSE.txt NOTICE NOTICE.txt; do \
         [ -f "$f" ] && cp "$f" "/licences/keycloak-2fa-email-authenticator-$f"; \
       done; true


FROM quay.io/keycloak/keycloak:25.0.0 AS builder

ENV KC_HEALTH_ENABLED=true
ENV KC_METRICS_ENABLED=true
ENV KC_FEATURES=token-exchange
ENV KC_DB=postgres

COPY --from=ext-builder /build/target/*.jar /opt/keycloak/providers/

WORKDIR /opt/keycloak
RUN /opt/keycloak/bin/kc.sh build


FROM registry.access.redhat.com/ubi9 AS ubi-micro-build
RUN mkdir -p /mnt/rootfs
RUN dnf install --installroot /mnt/rootfs curl --releasever 9 --setopt install_weak_deps=false --nodocs -y && \
    dnf --installroot /mnt/rootfs clean all && \
    rpm --root /mnt/rootfs -e --nodeps setup


# Final image
FROM quay.io/keycloak/keycloak:25.0
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
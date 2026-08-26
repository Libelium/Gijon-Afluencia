#!/usr/bin/env bash
#
# Build, tag and optionally push every platform image.
#
# The repository names are the ones charts/pid-gijon-core expects underneath
# global.imageRegistry — do not rename them here without changing the chart.
#
#   deploy/build-images.sh registry.example.com/pid-gijon
#   deploy/build-images.sh registry.example.com/pid-gijon --push
#   deploy/build-images.sh registry.example.com/pid-gijon --tag v1.0.0 --push
#   deploy/build-images.sh localhost:5000/pid-gijon --only aether-link,web-back
#
# La interfaz web se construye aqui como un componente mas del chart: su imagen
# resuelve la configuracion al arrancar, asi que la misma vale en cualquier entorno.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REGISTRY=""; PUSH=0; TAG=""; ONLY=""; NOCACHE=""

usage() { sed -n '2,14p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit "${1:-0}"; }

# --help before the positional: otherwise it is read as the registry and the
# script starts building.
[[ $# -eq 0 ]] && usage 1
case "$1" in -h|--help) usage 0 ;; esac
REGISTRY="$1"; shift
while [[ $# -gt 0 ]]; do
  case "$1" in
    --push)     PUSH=1 ;;
    --tag)      TAG="$2"; shift ;;
    --only)     ONLY="$2"; shift ;;
    --no-cache) NOCACHE="--no-cache" ;;
    -h|--help)  usage 0 ;;
    *) echo "unknown option: $1" >&2; usage 1 ;;
  esac
  shift
done

# name | path | image repository | extra build flags
SERVICES=(
  "aether-link|aether-link|aether-link|--target prod --build-context pylibs=../pylibs"
  "queues-consumer|queues-consumer|queues-consumer|--target prod --build-context pylibs=../pylibs"
  "fiware-manager|fiware-manager|fiware-manager|--target prod"
  "web-back|backend|web-back|"
  "keycloak|keycloak|keycloak|"
  "frontend|frontend|frontend|"
  # No lo despliega el chart todavia: son dos CronJobs que se programan aparte.
  "predictions|predictions|predictions|"
)

want() { [[ -z "$ONLY" ]] || [[ ",$ONLY," == *",$1,"* ]]; }

# aether-link and queues-consumer are built with --build-context, which only the
# BuildKit builder understands. Docker's own packages bundle buildx; Ubuntu's
# `docker.io` does not, and its legacy builder fails with "unknown flag:
# --build-context" — a message that says nothing about why.
if ! docker buildx version >/dev/null 2>&1; then
  needs_buildx=0
  for e in "${SERVICES[@]}"; do
    IFS='|' read -r n _ _ f <<< "$e"
    [[ "$f" == *--build-context* ]] && want "$n" && needs_buildx=1
  done
  if [[ $needs_buildx -eq 1 ]]; then
    cat >&2 <<'MSG'
!! docker buildx is not installed, and the legacy builder cannot build
   aether-link or queues-consumer: they need --build-context to resolve the
   shared pylibs without a private index.

   Debian/Ubuntu:  sudo apt-get install -y docker-buildx
   Or install Docker from docker.com, whose packages bundle it.

   To build only the images that do not need it:
     deploy/build-images.sh <registry> --only fiware-manager,web-back,keycloak
MSG
    exit 1
  fi
fi

built=(); skipped=(); warned_no_git=0
for entry in "${SERVICES[@]}"; do
  IFS='|' read -r name path repo flags <<< "$entry"
  want "$name" || { skipped+=("$name"); continue; }

  if [[ ! -d "$ROOT/$path" || -z "$(ls -A "$ROOT/$path" 2>/dev/null)" ]]; then
    echo "!! $ROOT/$path is missing or empty — run this from a full checkout" >&2
    exit 1
  fi

  # The web-back Dockerfile copies device datamodel CSVs from a nested directory.
  if [[ "$name" == "web-back" && -z "$(ls -A "$ROOT/$path/libelium_devices_fiware_datamodels" 2>/dev/null)" ]]; then
    echo "!! $path/libelium_devices_fiware_datamodels is empty; the build will fail." >&2
    echo "   Restore $ROOT/$path/libelium_devices_fiware_datamodels before building." >&2
    exit 1
  fi

  # Falls back when there is no git metadata — an exported tarball, a vendored
  # copy, a CI checkout with --depth=0 stripped. Without this the script dies on
  # the first service for a reason that has nothing to do with the build.
  if ! sha="$(git -C "$ROOT/$path" rev-parse --short HEAD 2>/dev/null)"; then
    sha="${TAG:-local}"
    [[ -n "$TAG" ]] || warned_no_git=1
  fi
  echo
  echo "=== $name  ($repo:$sha)"
  # shellcheck disable=SC2086
  ( cd "$ROOT/$path" && docker build $NOCACHE $flags -t "$repo:latest" . )

  docker tag "$repo:latest" "$REGISTRY/$repo:$sha"
  docker tag "$repo:latest" "$REGISTRY/$repo:latest"
  tags=("$sha" "latest")
  if [[ -n "$TAG" ]]; then
    docker tag "$repo:latest" "$REGISTRY/$repo:$TAG"
    tags+=("$TAG")
  fi

  if [[ $PUSH -eq 1 ]]; then
    for t in "${tags[@]}"; do docker push "$REGISTRY/$repo:$t"; done
  fi

  built+=("$repo:$sha")
done

echo
if [[ $warned_no_git -eq 1 ]]; then
  echo "note: no git metadata found, so images are tagged 'local'."
  echo "      Pass --tag <version> to give them a real tag."
fi
echo "Built:"
printf '  %s\n' "${built[@]}"
[[ ${#skipped[@]} -gt 0 ]] && printf 'Skipped: %s\n' "${skipped[*]}"
if [[ $PUSH -eq 0 ]]; then
  echo
  echo "Not pushed. Re-run with --push once you have run: docker login ${REGISTRY%%/*}"
fi

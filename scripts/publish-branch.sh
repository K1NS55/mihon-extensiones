#!/usr/bin/env bash
# Publica archivos generados usando las credenciales del checkout de Actions.
set -euo pipefail
output=${1:?Indica el directorio de distribución}
output=$(cd "$output" && pwd)
repo=$(git rev-parse --show-toplevel)
git_dir=$(git rev-parse --absolute-git-dir)
cd "$repo"
remote_head=$(git ls-remote --heads origin refs/heads/repo)
parents=()
if [[ -n "$remote_head" ]]; then
  git fetch --no-tags origin repo
  parents=(-p "$(git rev-parse FETCH_HEAD)")
fi
index_file=$(mktemp)
rm "$index_file"
trap 'rm -f "$index_file"' EXIT
(
  cd "$output"
  export GIT_DIR="$git_dir" GIT_WORK_TREE="$output" GIT_INDEX_FILE="$index_file"
  git add --all .
  tree=$(git write-tree)
  commit=$(printf 'Publicar %s\n' "${RELEASE_TAG:-extensiones}" | git commit-tree "$tree" "${parents[@]}")
  git push origin "$commit:refs/heads/repo"
)

#!/bin/bash
set -euo pipefail

# build.sh — 一键构建 eco-prof-app 产品目录
# 产物位于 ../eco-prof-app/（与 eco_knowladge_base 同级）

APP_DIR="../eco-prof-app"
SKILLS_DIR="$APP_DIR/.claude/skills"
DEV_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "Building eco-prof-app at $APP_DIR ..."

# Step 1: 创建目录
mkdir -p "$SKILLS_DIR"

# Step 2: 创建 symlink（若不存在或指向不同目标则重建）
create_symlink() {
  local target="$1"  # 指向 dev repo 的路径
  local link="$2"    # symlink 在 eco-prof-app 中的位置

  if [ -L "$link" ] && [ "$(readlink "$link")" = "$target" ]; then
    return  # 已存在且正确，跳过
  fi

  if [ -e "$link" ] || [ -L "$link" ]; then
    rm -rf "$link"
  fi
  ln -s "$target" "$link"
}

create_symlink "$DEV_DIR/knowledge" "$APP_DIR/knowledge"
create_symlink "$DEV_DIR/lab" "$APP_DIR/lab"

# Step 3: 复制 skill 子目录
for skill_dir in "$DEV_DIR/src/skills/"*/; do
  skill_name=$(basename "$skill_dir")
  cp -r "${skill_dir%/}" "$SKILLS_DIR/"
done

# Step 4: 生成 CLAUDE.md
cp -f "$DEV_DIR/src/eco-prof.md" "$APP_DIR/CLAUDE.md"

echo "Done. eco-prof-app is ready at $APP_DIR"
echo "  cd $APP_DIR && claude  # to start"

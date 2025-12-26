#!/usr/bin/env bash

set -e

BUILD_DIR=build

echo "🔨 preparing build directories..."
mkdir -p "$BUILD_DIR" "$BUILD_DIR/dist" "$BUILD_DIR/docs" "$BUILD_DIR/protocols"

echo "🧹 cleaning old artifacts..."
rm -f "$BUILD_DIR/docs"/* \
    "$BUILD_DIR/protocols"/* \
    "$BUILD_DIR/dist"/{*.json,*.xml,*.py} \
    2>/dev/null || true

echo "🔨 copying documentation..."
cp docs/* "$BUILD_DIR/docs"

echo "🔨 minifying bootstrap components..."
python3 main.py --silent minify-json minify ./protocols/{protocol-schema,rules}.json \
    --null-removal -o "$BUILD_DIR/protocols"

echo "🔨 minifying orchestration files..."
python3 main.py --silent minify-json minify ./protocols/orchestration-*.json \
    --null-removal -o "$BUILD_DIR/protocols/"

echo "🔨 normalizing filenames (stripping minification suffixes)..."
for f in "$BUILD_DIR/protocols"/*-out.json ; do mv "$f" "${f%-out.json}.json"; done

echo "🔨 nesting stage protocols..."
for dir in ./protocols/s*-*; do
    [ -d "$dir" ] || continue
    dname=$(basename "$dir")
    python3 main.py --silent nest-json nest "$dir" \
        -o "$BUILD_DIR/protocols/${dname}.json" --length "$dname"
done

echo "🔨 aggregating stage protocols..."
for llm in chatgpt gemini perplexity; do
  files=( "$BUILD_DIR"/protocols/s*"$llm"*.json )
  if [ ${#files[@]} -gt 0 ]; then
    python3 main.py --silent nest-json nest "${files[@]}" \
      -o "$BUILD_DIR/protocols/protocols-$llm.json" \
      --sum protocols-$llm
  fi
  rm -f "$BUILD_DIR"/protocols/s*"$llm".json
done

echo "🔨 compiling full kernels (orchestration,rules,protocols)..."
for llm in chatgpt gemini perplexity; do
  python3 main.py --silent nest-json nest \
    "$BUILD_DIR/protocols/orchestration-$llm.json" \
    "$BUILD_DIR/protocols/rules-$llm.json" \
    "$BUILD_DIR/protocols/protocol-schema.json" \
    "$BUILD_DIR/protocols/protocols-$llm.json" \
    -o "$BUILD_DIR/kernel-$llm.json" \
    --length rules \
    --sum protocols-$llm \
    --wrap "{\"metadata\":{\"type\":\"orchestration-control-plane\"}}"
    echo "  ✅ $BUILD_DIR/kernel-$llm.json created"
done

echo "🔨 validating build outputs..."
python3 main.py --silent verify-json "$BUILD_DIR/protocols/" -a

echo "🚀 bundling python scripts..."
python3 main.py --silent build-bundle -o "$BUILD_DIR/dist/bundle.py"
echo "  ✅ $BUILD_DIR/dist/bundle.py created"

echo "🚀 packaging context xml..."
for llm in chatgpt gemini perplexity; do
  mkdir -p "$BUILD_DIR/dist/$llm"
  python3 main.py --silent minify-json minify "$BUILD_DIR/kernel-$llm.json" \
    --null-removal --compact -o "$BUILD_DIR/dist/$llm/"
  python3 main.py build-session "$BUILD_DIR/dist/$llm/kernel-$llm-out.json" -o "$BUILD_DIR/dist/$llm/"
  echo "  ✅ $BUILD_DIR/dist/$llm/context.xml created"
  #rm "$BUILD_DIR/dist/$llm/kernel-$llm-out.json"
done

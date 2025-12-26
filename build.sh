#!/usr/bin/env bash

set -e

BUILD_DIR=build
LLMS=("chatgpt" "gemini" "perplexity")
SUFFIX_MAP=("chatgpt:-chatgpt" "gemini:-gemini" "perplexity:-perplexity")

echo "🔨 preparing build directories..."
mkdir -p "$BUILD_DIR" "$BUILD_DIR/dist" "$BUILD_DIR/docs" "$BUILD_DIR/protocols"

echo "🧹 cleaning old artifacts..."
rm -f "$BUILD_DIR/docs"/* "$BUILD_DIR/protocols"/* "$BUILD_DIR/dist"/{*.json,*.xml,*.py} 2>/dev/null || true

echo "🔨 copying documentation..."
cp docs/* "$BUILD_DIR/docs"

echo "🔨 minifying bootstrap components..."
python3 main.py --silent minify-json minify ./protocols/{protocol-schema,rules}.json --null-removal -o "$BUILD_DIR/protocols"

echo "🔨 minifying orchestration files..."
python3 main.py --silent minify-json minify ./protocols/orchestration-*.json --null-removal -o "$BUILD_DIR/protocols/"

echo "🔨 normalizing filenames (stripping minification suffixes)..."
for f in "$BUILD_DIR/protocols"/*-out.json ; do mv "$f" "${f%-out.json}.json"; done

echo "🔨 nesting all stage protocols..."
for dir in ./protocols/s*-*; do
    [ -d "$dir" ] || continue
    dname=$(basename "$dir")
    python3 main.py --silent nest-json "$dir" -o "$BUILD_DIR/protocols/${dname}.json" --length "$dname"
done

echo "🔨 aggregating stage protocols..."
for llm in chatgpt gemini perplexity; do
  python3 main.py --silent nest-json "$BUILD_DIR"/protocols/s*"$llm"*.json \
    -o "$BUILD_DIR/protocols/protocols-$llm.json" \
    --sum $STAGES
  rm -f "$BUILD_DIR"/protocols/s*"$llm".json
done

echo "🔨 finalizing session payloads..."
for llm in chatgpt gemini perplexity; do
  mkdir -p "$BUILD_DIR/dist/$llm"
  python3 main.py --silent nest-json \
    "$BUILD_DIR/protocols/orchestration-$llm.json" \
    rules.json \
    "$BUILD_DIR/protocols/protocol-schema.json" \
    "$BUILD_DIR/protocols/protocols-$llm.json" \
    -o "$BUILD_DIR/dist/$llm/session.json" \
    --length rules \
    --sum protocols-$llm \
    --wrap "{\"metadata\":{\"type\":\"orchestration-control-plan\"}}"
  echo "  ✅ ./build/protocols/ $llm master-payload.json created"
done

echo "🔨 validating, auto-fixing outputs..."
python3 main.py --silent verify-json ./build/protocols/ -a

#echo "🔨 finalizing master payloads..."
#python3 scripts/nest-json.py \
#   build/protocols/{orchestration,kernel-contract,states,validators,gates,locked-rules}.json -o build/protocols/master-payload.json --wrap '{"metadata":{"version":"7.1.0","type":"state-kernel-control-plane"}}'

echo "🚀 final packaging..."
python3 main.py --silent build-bundle -o "$BUILD_DIR/dist/bundle.py"
echo "  ✅ ./build/dist/bundle.json created"

echo "🔨 creating session xml from master payload..."
# python3 scripts/package-session.py "$DIST_DIR/master.json" -o "$DIST_DIR/"

echo "✅ Build and packaging complete: $DIST_DIR/context.xml"

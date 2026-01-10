#!/bin/bash
# Creates the DMG background image with "Drag to install" arrow
# Requires ImageMagick: brew install imagemagick

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT="$SCRIPT_DIR/background.png"
WIDTH=600
HEIGHT=400

# Check if ImageMagick is installed
if ! command -v convert &> /dev/null; then
    echo "ImageMagick not found. Install with: brew install imagemagick"
    echo "Creating placeholder background instead..."

    # Create a simple gradient background using sips (built-in)
    # This is a fallback - the real background should be designed properly
    cat > "$SCRIPT_DIR/background.svg" << 'EOF'
<svg width="600" height="400" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#1a1a2e;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#16213e;stop-opacity:1" />
    </linearGradient>
  </defs>
  <rect width="600" height="400" fill="url(#bg)"/>
  <!-- Arrow pointing right -->
  <path d="M 250 200 L 350 200 L 350 180 L 400 210 L 350 240 L 350 220 L 250 220 Z"
        fill="#ff6b35" opacity="0.8"/>
  <!-- Text -->
  <text x="300" y="320" text-anchor="middle" fill="#ffffff" font-family="SF Pro Display, Helvetica" font-size="16" opacity="0.7">
    Drag Oximy to Applications to install
  </text>
</svg>
EOF

    # Convert SVG to PNG using built-in tools (qlmanage)
    qlmanage -t -s 600 -o "$SCRIPT_DIR" "$SCRIPT_DIR/background.svg" 2>/dev/null || true
    if [ -f "$SCRIPT_DIR/background.svg.png" ]; then
        mv "$SCRIPT_DIR/background.svg.png" "$OUTPUT"
        rm "$SCRIPT_DIR/background.svg"
    fi

    echo "Created: $OUTPUT (basic version)"
    exit 0
fi

# Create background with ImageMagick
convert -size ${WIDTH}x${HEIGHT} \
    -define gradient:angle=180 \
    gradient:'#1a1a2e'-'#16213e' \
    -font "Helvetica-Bold" \
    -pointsize 16 \
    -fill 'rgba(255,255,255,0.7)' \
    -gravity south \
    -annotate +0+40 'Drag Oximy to Applications to install' \
    -fill '#ff6b35' \
    -draw "translate 300,200 path 'M -50,0 L 30,0 L 30,-20 L 70,0 L 30,20 L 30,0 Z'" \
    "$OUTPUT"

echo "Created: $OUTPUT"

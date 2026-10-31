#!/usr/bin/env python3
"""Render a trusted PNG/SVG logo on the build host; no target SVG dependency."""
import argparse
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


def prepare(source, destination):
    from PIL import Image, ImageOps
    Image.MAX_IMAGE_PIXELS = 16_000_000
    source = Path(source).resolve(strict=True)
    destination = Path(destination)
    if source.stat().st_size > 16 * 1024 * 1024:
        raise ValueError('Logo input exceeds 16 MiB')
    with tempfile.TemporaryDirectory(prefix='ninja-logo-') as directory:
        image_path = source
        if source.suffix.lower() == '.svg':
            image_path = Path(directory) / 'rendered.png'
            renderer = shutil.which('rsvg-convert')
            if renderer:
                command = [renderer, '--width', '1024', '--height', '600',
                           '--keep-aspect-ratio', '--output', str(image_path), str(source)]
            else:
                renderer = shutil.which('magick') or shutil.which('convert')
                if not renderer:
                    raise ValueError('SVG needs rsvg-convert or ImageMagick on the build host')
                command = [renderer, '-limit', 'memory', '128MiB', '-limit', 'map', '256MiB',
                           '-background', 'none', 'SVG:' + str(source), '-resize', '1024x600',
                           'PNG32:' + str(image_path)]
            result = subprocess.run(command, timeout=10, capture_output=True)
            if result.returncode:
                raise ValueError('SVG rendering failed')
        elif source.suffix.lower() != '.png':
            raise ValueError('Only PNG and SVG inputs are supported')
        with Image.open(image_path) as original:
            if original.format != 'PNG':
                raise ValueError('Expected PNG image data')
            original.load()
            image = ImageOps.contain(original.convert('RGBA'), (1024, 600), Image.Resampling.LANCZOS)
        canvas = Image.new('RGBA', (1024, 600), (0, 0, 0, 255))
        canvas.alpha_composite(image, ((1024 - image.width) // 2, (600 - image.height) // 2))
        destination.parent.mkdir(parents=True, exist_ok=True)
        canvas.convert('RGB').save(destination, format='PNG')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source')
    parser.add_argument('destination')
    args = parser.parse_args()
    try:
        prepare(args.source, args.destination)
    except Exception as error:
        print('Boot logo omitted:', error, file=sys.stderr)
        raise SystemExit(1)

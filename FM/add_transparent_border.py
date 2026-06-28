"""Add transparent borders to images, matching the sample gallery style.

This script adds transparent borders with the same pattern as the images
in the sample gallery: transparent pixels with grayish RGB values.
"""

import os
import argparse
from typing import Tuple
import numpy as np
from PIL import Image, ImageDraw
from tqdm import tqdm


def add_transparent_border(
    image: Image.Image,
    border_size: int = 20,
    background_color: Tuple[int, int, int] = (255, 255, 255),
    transparent_fill: Tuple[int, int, int] = (60, 60, 62),
    corner_radius: int = 10
) -> Image.Image:
    """Add a transparent border to an image.
    
    Args:
        image: Input PIL Image.
        border_size: Size of border in pixels.
        background_color: RGB color for background (default: white).
        transparent_fill: RGB color for transparent areas (default: grayish).
        corner_radius: Radius for rounded corners (0 = no rounding).
        
    Returns:
        New image with transparent border.
    """
    # Ensure image is in RGBA mode
    if image.mode != 'RGBA':
        image = image.convert('RGBA')
    
    # Get original size
    orig_width, orig_height = image.size
    
    # Create new image with border
    new_width = orig_width + 2 * border_size
    new_height = orig_height + 2 * border_size
    
    # Create base image with transparent fill color and full alpha
    new_image = Image.new('RGBA', (new_width, new_height), 
                          (*transparent_fill, 255))
    
    # Create alpha mask for the border
    alpha_mask = Image.new('L', (new_width, new_height), 0)  # Start fully transparent
    draw = ImageDraw.Draw(alpha_mask)
    
    # Draw opaque rectangle for center (where original image will be)
    if corner_radius > 0:
        # Rounded rectangle for center
        draw.rounded_rectangle(
            [(border_size, border_size), 
             (new_width - border_size, new_height - border_size)],
            radius=corner_radius,
            fill=255  # Opaque
        )
    else:
        # Regular rectangle
        draw.rectangle(
            [(border_size, border_size), 
             (new_width - border_size, new_height - border_size)],
            fill=255  # Opaque
        )
    
    # Apply alpha mask
    new_image.putalpha(alpha_mask)
    
    # Paste original image in center
    new_image.paste(image, (border_size, border_size), image)
    
    return new_image


def add_white_background_with_transparent_border(
    image: Image.Image,
    border_size: int = 20,
    inner_padding: int = 10,
    transparent_fill: Tuple[int, int, int] = (60, 60, 62),
    corner_radius: int = 10
) -> Image.Image:
    """Add white background with transparent border (matches sample style).
    
    This creates the pattern seen in sample gallery:
    - Transparent outer border
    - White background
    - Original image centered
    
    Args:
        image: Input PIL Image.
        border_size: Size of transparent border.
        inner_padding: White padding around image.
        transparent_fill: RGB color for transparent pixels.
        corner_radius: Radius for rounded corners.
        
    Returns:
        New image with white background and transparent border.
    """
    # Ensure RGB mode for center
    if image.mode == 'RGBA':
        # Composite onto white background first
        white_bg = Image.new('RGB', image.size, (255, 255, 255))
        white_bg.paste(image, (0, 0), image)
        image = white_bg
    elif image.mode != 'RGB':
        image = image.convert('RGB')
    
    # Calculate new dimensions
    orig_width, orig_height = image.size
    total_padding = border_size + inner_padding
    new_width = orig_width + 2 * total_padding
    new_height = orig_height + 2 * total_padding
    
    # Create RGBA image
    new_image = Image.new('RGBA', (new_width, new_height), 
                          (*transparent_fill, 0))  # Fully transparent
    
    # Create mask
    mask = Image.new('L', (new_width, new_height), 0)
    draw_mask = ImageDraw.Draw(mask)
    
    # White background area (opaque)
    if corner_radius > 0:
        draw_mask.rounded_rectangle(
            [(border_size, border_size),
             (new_width - border_size, new_height - border_size)],
            radius=corner_radius,
            fill=255
        )
    else:
        draw_mask.rectangle(
            [(border_size, border_size),
             (new_width - border_size, new_height - border_size)],
            fill=255
        )
    
    # Create white background layer
    white_layer = Image.new('RGBA', (new_width, new_height), (255, 255, 255, 255))
    
    # Composite: transparent background + white center
    new_image = Image.composite(white_layer, new_image, mask)
    
    # Paste original image
    image_rgba = image.convert('RGBA')
    new_image.paste(image_rgba, (total_padding, total_padding), image_rgba)
    
    return new_image


def detect_and_match_border_style(
    sample_image_path: str
) -> Tuple[int, Tuple[int, int, int]]:
    """Detect border style from a sample image.
    
    Args:
        sample_image_path: Path to sample image with border.
        
    Returns:
        Tuple of (border_size, transparent_fill_color)
    """
    img = Image.open(sample_image_path)
    
    if img.mode not in ('RGBA', 'LA', 'PA'):
        print("Sample image has no alpha channel")
        return 20, (60, 60, 62)  # Defaults
    
    img_array = np.array(img)
    
    if img.mode == 'RGBA':
        alpha = img_array[:,:,3]
        rgb = img_array[:,:,:3]
        
        # Find transparent pixels
        transparent_mask = (alpha == 0)
        
        if not np.any(transparent_mask):
            print("No transparent pixels found")
            return 20, (60, 60, 62)
        
        # Get RGB values at transparent pixels
        trans_rgb = rgb[transparent_mask]
        avg_color = tuple(int(trans_rgb[:,i].mean()) for i in range(3))
        
        # Detect border size (count transparent pixels from edge)
        # Check top edge
        for i in range(img.shape[0]):
            if np.mean(alpha[i,:]) > 128:  # First row with mostly opaque
                border_size = i
                break
        else:
            border_size = 20  # Default
        
        print(f"Detected border size: {border_size}")
        print(f"Detected transparent fill color: {avg_color}")
        
        return border_size, avg_color
    
    return 20, (60, 60, 62)  # Defaults


def process_image(
    input_path: str,
    output_path: str,
    border_size: int = 20,
    style: str = 'transparent_border',
    **kwargs
):
    """Process a single image to add border.
    
    Args:
        input_path: Path to input image.
        output_path: Path to save output image.
        border_size: Size of border.
        style: Border style ('transparent_border' or 'white_background').
        **kwargs: Additional arguments for border functions.
    """
    img = Image.open(input_path)
    
    if style == 'transparent_border':
        result = add_transparent_border(img, border_size=border_size, **kwargs)
    elif style == 'white_background':
        result = add_white_background_with_transparent_border(
            img, border_size=border_size, **kwargs
        )
    else:
        raise ValueError(f"Unknown style: {style}")
    
    # Save as PNG to preserve transparency
    result.save(output_path, 'PNG')


def batch_process_directory(
    input_dir: str,
    output_dir: str,
    border_size: int = 20,
    style: str = 'transparent_border',
    match_sample: str = None,
    **kwargs
):
    """Process all images in a directory.
    
    Args:
        input_dir: Directory containing input images.
        output_dir: Directory to save output images.
        border_size: Size of border.
        style: Border style.
        match_sample: Path to sample image to match style.
        **kwargs: Additional arguments for border functions.
    """
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Match sample style if provided
    if match_sample and os.path.exists(match_sample):
        print(f"Analyzing sample image: {match_sample}")
        detected_border, detected_color = detect_and_match_border_style(match_sample)
        border_size = detected_border
        kwargs['transparent_fill'] = detected_color
        print()
    
    # Get all image files
    image_files = []
    for filename in os.listdir(input_dir):
        if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif')):
            image_files.append(filename)
    
    if not image_files:
        print(f"No image files found in {input_dir}")
        return
    
    print(f"Processing {len(image_files)} images...")
    print(f"Border size: {border_size}")
    print(f"Style: {style}")
    print()
    
    # Process each image
    for filename in tqdm(image_files, desc="Processing", unit="img"):
        input_path = os.path.join(input_dir, filename)
        
        # Change extension to .png for output
        name, _ = os.path.splitext(filename)
        output_filename = f"{name}.png"
        output_path = os.path.join(output_dir, output_filename)
        
        try:
            process_image(input_path, output_path, border_size, style, **kwargs)
        except Exception as e:
            print(f"  Error processing {filename}: {e}")
    
    print(f"\n✅ Done! Processed images saved to: {output_dir}")


def main():
    parser = argparse.ArgumentParser(
        description="Add transparent borders to images"
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Single image command
    single = subparsers.add_parser('single', help='Process a single image')
    single.add_argument('input', help='Input image path')
    single.add_argument('output', help='Output image path')
    single.add_argument('--border', type=int, default=20, help='Border size (default: 20)')
    single.add_argument(
        '--style',
        choices=['transparent_border', 'white_background'],
        default='white_background',
        help='Border style (default: white_background)'
    )
    single.add_argument('--inner-padding', type=int, default=10, help='Inner padding (white_background style)')
    single.add_argument('--corner-radius', type=int, default=10, help='Corner radius (0 = no rounding)')
    
    # Batch processing command
    batch = subparsers.add_parser('batch', help='Process a directory of images')
    batch.add_argument('input_dir', help='Input directory')
    batch.add_argument('output_dir', help='Output directory')
    batch.add_argument('--border', type=int, default=20, help='Border size (default: 20)')
    batch.add_argument(
        '--style',
        choices=['transparent_border', 'white_background'],
        default='white_background',
        help='Border style (default: white_background)'
    )
    batch.add_argument(
        '--match-sample',
        help='Path to sample image to match style'
    )
    batch.add_argument('--inner-padding', type=int, default=10, help='Inner padding (white_background style)')
    batch.add_argument('--corner-radius', type=int, default=10, help='Corner radius (0 = no rounding)')
    
    # Analyze command
    analyze = subparsers.add_parser('analyze', help='Analyze an image border')
    analyze.add_argument('image', help='Image to analyze')
    
    args = parser.parse_args()
    
    if args.command == 'single':
        print(f"Processing: {args.input}")
        print(f"Output: {args.output}")
        print(f"Border size: {args.border}")
        print(f"Style: {args.style}")
        
        kwargs = {
            'corner_radius': args.corner_radius
        }
        if args.style == 'white_background':
            kwargs['inner_padding'] = args.inner_padding
        
        process_image(args.input, args.output, args.border, args.style, **kwargs)
        print("✅ Done!")
        
    elif args.command == 'batch':
        kwargs = {
            'corner_radius': args.corner_radius
        }
        if args.style == 'white_background':
            kwargs['inner_padding'] = args.inner_padding
        
        batch_process_directory(
            args.input_dir,
            args.output_dir,
            args.border,
            args.style,
            args.match_sample,
            **kwargs
        )
        
    elif args.command == 'analyze':
        print(f"Analyzing: {args.image}")
        detect_and_match_border_style(args.image)
        
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

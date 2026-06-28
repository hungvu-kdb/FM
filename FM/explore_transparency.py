"""Explore how transparent images are converted to RGB.

This script analyzes sample images to understand the transparency pattern,
then demonstrates how to add transparent borders to images.
"""

import os
import numpy as np
from PIL import Image
import matplotlib.pyplot as plt


def analyze_image_transparency(image_path: str) -> dict:
    """Analyze an image to understand its transparency and color structure.
    
    Args:
        image_path: Path to the image file.
        
    Returns:
        Dictionary with analysis results.
    """
    print(f"\n{'='*60}")
    print(f"Analyzing: {os.path.basename(image_path)}")
    print('='*60)
    
    # Load image with all channels
    img = Image.open(image_path)
    
    results = {
        'filename': os.path.basename(image_path),
        'mode': img.mode,
        'size': img.size,
        'has_alpha': img.mode in ('RGBA', 'LA', 'PA')
    }
    
    print(f"Mode: {img.mode}")
    print(f"Size: {img.size}")
    print(f"Has Alpha: {results['has_alpha']}")
    
    # Convert to numpy array
    img_array = np.array(img)
    print(f"Array shape: {img_array.shape}")
    print(f"Array dtype: {img_array.dtype}")
    
    results['array_shape'] = img_array.shape
    
    # Analyze channels
    if results['has_alpha']:
        if img.mode == 'RGBA':
            r, g, b, a = img_array[:,:,0], img_array[:,:,1], img_array[:,:,2], img_array[:,:,3]
            print(f"\nChannel ranges:")
            print(f"  R: [{r.min()}, {r.max()}]")
            print(f"  G: [{g.min()}, {g.max()}]")
            print(f"  B: [{b.min()}, {b.max()}]")
            print(f"  A: [{a.min()}, {a.max()}]")
            
            # Find transparent pixels (alpha = 0)
            transparent_mask = (a == 0)
            num_transparent = np.sum(transparent_mask)
            total_pixels = a.size
            
            print(f"\nTransparency analysis:")
            print(f"  Transparent pixels: {num_transparent} ({num_transparent/total_pixels*100:.2f}%)")
            print(f"  Opaque pixels: {total_pixels - num_transparent} ({(total_pixels-num_transparent)/total_pixels*100:.2f}%)")
            
            if num_transparent > 0:
                # Analyze what RGB values transparent pixels have
                trans_r = r[transparent_mask]
                trans_g = g[transparent_mask]
                trans_b = b[transparent_mask]
                
                print(f"\nRGB values at transparent pixels:")
                print(f"  R: [{trans_r.min()}, {trans_r.max()}] (mean: {trans_r.mean():.2f})")
                print(f"  G: [{trans_g.min()}, {trans_g.max()}] (mean: {trans_g.mean():.2f})")
                print(f"  B: [{trans_b.min()}, {trans_b.max()}] (mean: {trans_b.mean():.2f})")
                
                # Check if most transparent pixels are white (255, 255, 255)
                white_transparent = np.sum((trans_r == 255) & (trans_g == 255) & (trans_b == 255))
                print(f"  White (255,255,255) transparent pixels: {white_transparent} ({white_transparent/num_transparent*100:.2f}%)")
                
                results['transparent_pixels'] = num_transparent
                results['transparent_color'] = (trans_r.mean(), trans_g.mean(), trans_b.mean())
    
    # Convert to RGB and analyze
    print(f"\n{'---'*20}")
    print("Converting to RGB...")
    rgb_img = img.convert('RGB')
    rgb_array = np.array(rgb_img)
    
    print(f"RGB array shape: {rgb_array.shape}")
    print(f"RGB array dtype: {rgb_array.dtype}")
    
    r, g, b = rgb_array[:,:,0], rgb_array[:,:,1], rgb_array[:,:,2]
    print(f"\nRGB channel ranges after conversion:")
    print(f"  R: [{r.min()}, {r.max()}]")
    print(f"  G: [{g.min()}, {g.max()}]")
    print(f"  B: [{b.min()}, {b.max()}]")
    
    # If original had alpha, check what happened to transparent areas
    if results['has_alpha'] and num_transparent > 0:
        # Get RGB values at same positions that were transparent
        rgb_at_transparent_r = r[transparent_mask]
        rgb_at_transparent_g = g[transparent_mask]
        rgb_at_transparent_b = b[transparent_mask]
        
        print(f"\nRGB values at formerly transparent positions:")
        print(f"  R: [{rgb_at_transparent_r.min()}, {rgb_at_transparent_r.max()}] (mean: {rgb_at_transparent_r.mean():.2f})")
        print(f"  G: [{rgb_at_transparent_g.min()}, {rgb_at_transparent_g.max()}] (mean: {rgb_at_transparent_g.mean():.2f})")
        print(f"  B: [{rgb_at_transparent_b.min()}, {rgb_at_transparent_b.max()}] (mean: {rgb_at_transparent_b.mean():.2f})")
        
        # Check if they became white or black
        white_count = np.sum((rgb_at_transparent_r == 255) & (rgb_at_transparent_g == 255) & (rgb_at_transparent_b == 255))
        black_count = np.sum((rgb_at_transparent_r == 0) & (rgb_at_transparent_g == 0) & (rgb_at_transparent_b == 0))
        
        print(f"  White (255,255,255): {white_count} ({white_count/num_transparent*100:.2f}%)")
        print(f"  Black (0,0,0): {black_count} ({black_count/num_transparent*100:.2f}%)")
        
        results['rgb_transparent_color'] = (rgb_at_transparent_r.mean(), rgb_at_transparent_g.mean(), rgb_at_transparent_b.mean())
    
    return results


def visualize_transparency(image_path: str, output_path: str = None):
    """Visualize the transparency mask and RGB conversion.
    
    Args:
        image_path: Path to the image file.
        output_path: Optional path to save visualization.
    """
    img = Image.open(image_path)
    
    if img.mode not in ('RGBA', 'LA', 'PA'):
        print(f"Image {os.path.basename(image_path)} has no alpha channel")
        return
    
    # Create figure
    fig, axes = plt.subplots(2, 3, figsize=(15, 10))
    fig.suptitle(f'Transparency Analysis: {os.path.basename(image_path)}', fontsize=16)
    
    img_array = np.array(img)
    
    # Original RGBA
    axes[0, 0].imshow(img)
    axes[0, 0].set_title('Original RGBA')
    axes[0, 0].axis('off')
    
    # Alpha channel
    if img.mode == 'RGBA':
        alpha = img_array[:,:,3]
        axes[0, 1].imshow(alpha, cmap='gray')
        axes[0, 1].set_title('Alpha Channel')
        axes[0, 1].axis('off')
        
        # Transparency mask
        transparent_mask = (alpha == 0)
        axes[0, 2].imshow(transparent_mask, cmap='gray')
        axes[0, 2].set_title('Transparent Pixels (white)')
        axes[0, 2].axis('off')
        
        # RGB channels at transparent areas
        rgb = img_array[:,:,:3]
        rgb_at_transparent = rgb.copy()
        rgb_at_transparent[~transparent_mask] = 0  # Black out non-transparent areas
        
        axes[1, 0].imshow(rgb_at_transparent)
        axes[1, 0].set_title('RGB at Transparent Areas')
        axes[1, 0].axis('off')
    
    # Converted to RGB
    rgb_img = img.convert('RGB')
    axes[1, 1].imshow(rgb_img)
    axes[1, 1].set_title('Converted to RGB')
    axes[1, 1].axis('off')
    
    # Difference visualization
    if img.mode == 'RGBA':
        rgb_array = np.array(rgb_img)
        diff = np.abs(img_array[:,:,:3].astype(float) - rgb_array.astype(float)).mean(axis=2)
        axes[1, 2].imshow(diff, cmap='hot')
        axes[1, 2].set_title('Difference (RGBA RGB vs Converted RGB)')
        axes[1, 2].axis('off')
    
    plt.tight_layout()
    
    if output_path:
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"Visualization saved to: {output_path}")
    
    plt.show()


def explore_sample_gallery(gallery_dir: str = r"d:\Mini-Project\FM\sample", num_samples: int = 5):
    """Explore multiple images from the sample gallery.
    
    Args:
        gallery_dir: Path to gallery directory.
        num_samples: Number of images to analyze.
    """
    print("="*60)
    print("EXPLORING SAMPLE GALLERY")
    print("="*60)
    
    # Get PNG files
    png_files = []
    for filename in os.listdir(gallery_dir):
        if filename.lower().endswith('.png'):
            png_files.append(os.path.join(gallery_dir, filename))
    
    png_files.sort()
    
    if not png_files:
        print(f"No PNG files found in {gallery_dir}")
        return
    
    print(f"Found {len(png_files)} PNG files")
    print(f"Analyzing first {min(num_samples, len(png_files))} images...\n")
    
    results = []
    for image_path in png_files[:num_samples]:
        result = analyze_image_transparency(image_path)
        results.append(result)
    
    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print('='*60)
    
    has_alpha_count = sum(1 for r in results if r['has_alpha'])
    print(f"Images with alpha channel: {has_alpha_count}/{len(results)}")
    
    if has_alpha_count > 0:
        print(f"\nPattern detected:")
        alpha_results = [r for r in results if r['has_alpha']]
        
        if 'transparent_color' in alpha_results[0]:
            avg_trans_color = np.mean([r['transparent_color'] for r in alpha_results if 'transparent_color' in r], axis=0)
            print(f"  Average RGB at transparent pixels: ({avg_trans_color[0]:.1f}, {avg_trans_color[1]:.1f}, {avg_trans_color[2]:.1f})")
            
            if all(c > 250 for c in avg_trans_color):
                print(f"  ✅ Transparent areas are WHITE (255, 255, 255)")
            elif all(c < 5 for c in avg_trans_color):
                print(f"  ✅ Transparent areas are BLACK (0, 0, 0)")
            else:
                print(f"  ⚠️ Transparent areas have mixed colors")
        
        if 'rgb_transparent_color' in alpha_results[0]:
            avg_rgb_trans = np.mean([r['rgb_transparent_color'] for r in alpha_results if 'rgb_transparent_color' in r], axis=0)
            print(f"  After RGB conversion: ({avg_rgb_trans[0]:.1f}, {avg_rgb_trans[1]:.1f}, {avg_rgb_trans[2]:.1f})")
            
            if all(c > 250 for c in avg_rgb_trans):
                print(f"  ✅ Transparent pixels become WHITE in RGB")
            elif all(c < 5 for c in avg_rgb_trans):
                print(f"  ✅ Transparent pixels become BLACK in RGB")
    
    return results


def main():
    """Main exploration function."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Explore how transparent images convert to RGB"
    )
    parser.add_argument(
        "--gallery",
        default=r"d:\Mini-Project\FM\sample",
        help="Gallery directory to explore"
    )
    parser.add_argument(
        "--samples",
        type=int,
        default=5,
        help="Number of sample images to analyze"
    )
    parser.add_argument(
        "--visualize",
        metavar="IMAGE",
        help="Path to specific image to visualize"
    )
    parser.add_argument(
        "--output",
        help="Output path for visualization"
    )
    
    args = parser.parse_args()
    
    if args.visualize:
        # Visualize specific image
        visualize_transparency(args.visualize, args.output)
    else:
        # Explore gallery
        results = explore_sample_gallery(args.gallery, args.samples)
        
        # Optionally visualize first image with alpha
        if results:
            alpha_images = [r for r in results if r['has_alpha']]
            if alpha_images:
                print(f"\n{'='*60}")
                print("Creating visualization for first image with alpha channel...")
                print('='*60)
                
                first_alpha = alpha_images[0]['filename']
                image_path = os.path.join(args.gallery, first_alpha)
                output_path = args.output or f"transparency_analysis_{first_alpha}"
                
                try:
                    visualize_transparency(image_path, output_path)
                except Exception as e:
                    print(f"Could not create visualization: {e}")


if __name__ == "__main__":
    main()

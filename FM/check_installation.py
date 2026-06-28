"""Installation verification script.

Run this script to verify that all dependencies for the CNN implementation
and Streamlit app are properly installed.
"""

import sys
from typing import List, Tuple


def check_imports() -> List[Tuple[str, bool, str]]:
    """Check if all required packages can be imported.
    
    Returns:
        List of (package_name, success, message) tuples.
    """
    results = []
    
    # Core dependencies
    packages = [
        ("torch", "PyTorch"),
        ("torchvision", "TorchVision"),
        ("facenet_pytorch", "FaceNet-PyTorch"),
        ("numpy", "NumPy"),
        ("PIL", "Pillow"),
        ("streamlit", "Streamlit"),
        ("pandas", "Pandas"),
        ("requests", "Requests"),
    ]
    
    for import_name, display_name in packages:
        try:
            __import__(import_name)
            results.append((display_name, True, "✅ Installed"))
        except ImportError as e:
            results.append((display_name, False, f"❌ Not found: {e}"))
    
    return results


def check_torch_cuda():
    """Check PyTorch CUDA availability."""
    try:
        import torch
        if torch.cuda.is_available():
            device_count = torch.cuda.device_count()
            device_name = torch.cuda.get_device_name(0)
            return True, f"✅ CUDA available: {device_count} device(s) - {device_name}"
        else:
            return False, "⚠️  CUDA not available (CPU only)"
    except Exception as e:
        return False, f"❌ Error checking CUDA: {e}"


def check_models():
    """Check if models can be loaded."""
    try:
        from facenet_pytorch import MTCNN, InceptionResnetV1
        
        # Try to initialize models (doesn't download if cached)
        device = 'cpu'  # Use CPU for quick check
        mtcnn = MTCNN(device=device)
        facenet = InceptionResnetV1(pretrained='vggface2').eval()
        
        return True, "✅ Models can be loaded"
    except Exception as e:
        return False, f"❌ Error loading models: {e}"


def check_gallery():
    """Check if default gallery directory exists."""
    import os
    default_gallery = r"d:\Mini-Project\FM\sample"
    
    if os.path.isdir(default_gallery):
        # Count PNG files
        png_files = [f for f in os.listdir(default_gallery) 
                     if f.lower().endswith('.png')]
        return True, f"✅ Gallery found: {len(png_files)} images"
    else:
        return False, f"⚠️  Default gallery not found: {default_gallery}"


def check_cnn_module():
    """Check if CNN.py can be imported."""
    try:
        import CNN
        return True, "✅ CNN.py module can be imported"
    except ImportError as e:
        return False, f"❌ Cannot import CNN.py: {e}"
    except Exception as e:
        return False, f"⚠️  Import warning: {e}"


def main():
    """Run all checks and display results."""
    print("=" * 60)
    print("  Facial Recognition System - Installation Check")
    print("=" * 60)
    print()
    
    # Check Python version
    print("🐍 Python Version:")
    print(f"   {sys.version}")
    if sys.version_info < (3, 8):
        print("   ⚠️  Warning: Python 3.8+ recommended")
    else:
        print("   ✅ Version OK")
    print()
    
    # Check package imports
    print("📦 Package Dependencies:")
    results = check_imports()
    all_installed = True
    for name, success, message in results:
        print(f"   {name:20s} {message}")
        if not success:
            all_installed = False
    print()
    
    # Check CUDA
    print("🔥 GPU/CUDA Support:")
    cuda_available, cuda_msg = check_torch_cuda()
    print(f"   {cuda_msg}")
    print()
    
    # Check models
    print("🤖 FaceNet Models:")
    models_ok, models_msg = check_models()
    print(f"   {models_msg}")
    if models_ok:
        print("   Note: First run will download models (~100MB)")
    print()
    
    # Check CNN module
    print("📄 CNN Module:")
    cnn_ok, cnn_msg = check_cnn_module()
    print(f"   {cnn_msg}")
    print()
    
    # Check gallery
    print("📁 Gallery Directory:")
    gallery_ok, gallery_msg = check_gallery()
    print(f"   {gallery_msg}")
    print()
    
    # Summary
    print("=" * 60)
    print("  Summary")
    print("=" * 60)
    
    if all_installed and models_ok and cnn_ok:
        print("✅ All checks passed!")
        print()
        print("You're ready to run the app:")
        print("   streamlit run app.py")
        print()
        if not cuda_available:
            print("ℹ️  Note: GPU not available. App will use CPU (slower).")
            print("   For GPU support, install CUDA-enabled PyTorch.")
    else:
        print("❌ Some checks failed. Please install missing dependencies:")
        print()
        if not all_installed:
            print("   Install packages:")
            print("   pip install -r requirements_cnn.txt")
            print()
        if not models_ok:
            print("   Models check failed. Ensure PyTorch is properly installed.")
            print()
        if not cnn_ok:
            print("   CNN.py module check failed. Ensure file exists in current directory.")
    
    print()
    print("=" * 60)
    
    # Return exit code
    return 0 if (all_installed and models_ok and cnn_ok) else 1


if __name__ == "__main__":
    sys.exit(main())

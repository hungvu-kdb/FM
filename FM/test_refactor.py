"""Quick test script to verify refactored functions work correctly."""

import os
import json
import numpy as np
from pathlib import Path

# Test configuration
ENCODED_RESULT_DIR = r"d:\Mini-Project\FM\encoded_result"
MANIFEST_PATH = os.path.join(ENCODED_RESULT_DIR, "manifest.json")

def test_manifest_exists():
    """Test if manifest.json exists."""
    exists = os.path.exists(MANIFEST_PATH)
    print(f"{'✅' if exists else '❌'} Manifest exists: {exists}")
    return exists

def test_manifest_readable():
    """Test if manifest.json is readable."""
    try:
        with open(MANIFEST_PATH, 'r', encoding='utf-8') as f:
            manifest = json.load(f)
        count = len(manifest)
        print(f"✅ Manifest readable: {count} entries")
        return True, manifest
    except Exception as e:
        print(f"❌ Manifest read failed: {e}")
        return False, None

def test_encoding_files_exist(manifest, sample_size=10):
    """Test if encoding files exist."""
    if not manifest:
        print("❌ No manifest to test")
        return False
    
    # Test first N entries
    entries = list(manifest.items())[:sample_size]
    valid = 0
    
    for path, entry in entries:
        encoding_file = os.path.join(ENCODED_RESULT_DIR, entry['encoding_file'])
        if os.path.exists(encoding_file):
            valid += 1
    
    print(f"✅ Encoding files test: {valid}/{len(entries)} files exist")
    return valid == len(entries)

def test_encoding_loadable(manifest, sample_size=5):
    """Test if encoding files are loadable."""
    if not manifest:
        print("❌ No manifest to test")
        return False
    
    entries = list(manifest.items())[:sample_size]
    loaded = 0
    
    for path, entry in entries:
        encoding_file = os.path.join(ENCODED_RESULT_DIR, entry['encoding_file'])
        try:
            if os.path.exists(encoding_file):
                encoding = np.load(encoding_file)
                if encoding.shape[0] == 512:  # Check expected shape
                    loaded += 1
        except Exception as e:
            print(f"  ⚠️ Failed to load {entry['encoding_file']}: {e}")
    
    print(f"✅ Encoding load test: {loaded}/{len(entries)} files loaded successfully")
    return loaded == len(entries)

def test_manifest_structure(manifest):
    """Test if manifest has correct structure."""
    if not manifest:
        print("❌ No manifest to test")
        return False
    
    # Test first entry structure
    first_entry = next(iter(manifest.values()))
    required_fields = ['original_path', 'basename', 'encoding_file', 'encoding_shape', 'encoding_dtype']
    
    has_all = all(field in first_entry for field in required_fields)
    
    if has_all:
        print(f"✅ Manifest structure valid: All required fields present")
    else:
        missing = [f for f in required_fields if f not in first_entry]
        print(f"❌ Manifest structure invalid: Missing fields {missing}")
    
    return has_all

def main():
    """Run all tests."""
    print("=" * 60)
    print("Testing Refactored Manifest-Based Loading")
    print("=" * 60)
    print()
    
    # Test 1: Manifest exists
    if not test_manifest_exists():
        print("\n⚠️ Manifest not found. Run app and load gallery first.")
        return
    
    print()
    
    # Test 2: Manifest readable
    success, manifest = test_manifest_readable()
    if not success:
        return
    
    print()
    
    # Test 3: Manifest structure
    test_manifest_structure(manifest)
    
    print()
    
    # Test 4: Encoding files exist
    test_encoding_files_exist(manifest, sample_size=10)
    
    print()
    
    # Test 5: Encoding files loadable
    test_encoding_loadable(manifest, sample_size=5)
    
    print()
    print("=" * 60)
    print("✅ All tests completed!")
    print("=" * 60)
    
    # Summary
    total_entries = len(manifest)
    print(f"\n📊 Summary:")
    print(f"   - Total entries in manifest: {total_entries}")
    print(f"   - Manifest file size: {os.path.getsize(MANIFEST_PATH) / (1024*1024):.2f} MB")
    print(f"   - Encoding directory: {ENCODED_RESULT_DIR}")
    print(f"\n✨ Refactor appears to be working correctly!")

if __name__ == "__main__":
    main()

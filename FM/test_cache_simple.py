"""Simple test script to debug cache loading issue."""

import os
import json
import numpy as np
from CNN import CNNGallerySet, EMBEDDING_DIM

ENCODED_RESULT_DIR = r"d:\Mini-Project\FM\encoded_result"

def test_load_encodings():
    """Test loading encodings from encoded_result directory."""
    manifest_path = os.path.join(ENCODED_RESULT_DIR, "manifest.json")
    
    print(f"Manifest path: {manifest_path}")
    print(f"Manifest exists: {os.path.exists(manifest_path)}")
    
    if not os.path.exists(manifest_path):
        print("ERROR: Manifest file not found!")
        return None
    
    try:
        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest = json.load(f)
        
        print(f"SUCCESS: Loaded manifest with {len(manifest)} entries")
        
        if not manifest:
            print("ERROR: Manifest is empty")
            return None
        
        # Load all encodings with unique filenames
        filenames = []
        embeddings = []
        seen_basenames = {}  # Track duplicate basenames
        
        missing_files = []
        for original_path, entry in manifest.items():
            encoding_file = os.path.join(ENCODED_RESULT_DIR, entry['encoding_file'])
            
            if os.path.exists(encoding_file):
                encoding = np.load(encoding_file)
                
                # Create unique filename by adding counter if duplicate
                basename = entry['basename']
                if basename in seen_basenames:
                    seen_basenames[basename] += 1
                    unique_name = f"{os.path.splitext(basename)[0]}_{seen_basenames[basename]}{os.path.splitext(basename)[1]}"
                else:
                    seen_basenames[basename] = 0
                    unique_name = basename
                
                filenames.append(unique_name)
                embeddings.append(encoding)
            else:
                missing_files.append(entry['encoding_file'])
        
        if missing_files:
            print(f"WARNING: {len(missing_files)} encoding files not found")
        
        if not embeddings:
            print(f"ERROR: No valid encoding files found in {ENCODED_RESULT_DIR}")
            return None
        
        # Check for duplicates after processing
        duplicates = {k: v for k, v in seen_basenames.items() if v > 0}
        if duplicates:
            print(f"INFO: Handled {len(duplicates)} duplicate filenames by adding suffixes")
            print(f"Examples: {list(duplicates.items())[:5]}")
        
        print(f"SUCCESS: Successfully loaded {len(embeddings)} encodings")
        print(f"EMBEDDING_DIM from CNN: {EMBEDDING_DIM}")
        
        # Stack into matrix
        matrix = np.stack(embeddings)
        print(f"Matrix shape: {matrix.shape}")
        
        # Verify filenames are unique
        if len(filenames) != len(set(filenames)):
            print("ERROR: Filenames are NOT unique!")
            return None
        
        print(f"SUCCESS: All {len(filenames)} filenames are unique")
        
        gallery = CNNGallerySet(filenames=filenames, matrix=matrix)
        print(f"SUCCESS: Gallery created with {len(gallery)} faces")
        
        return gallery
    
    except Exception as e:
        print(f"ERROR loading encodings: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    print("=" * 60)
    print("Testing cache loading...")
    print("=" * 60)
    
    result = test_load_encodings()
    
    print("\n" + "=" * 60)
    if result:
        print("SUCCESS: Cache loading works!")
    else:
        print("FAILED: Cache loading failed")
    print("=" * 60)

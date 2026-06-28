# Manifest-Based Loading Refactor

## Overview
Refactored the Streamlit app to efficiently load face encodings using the `manifest.json` file instead of rescanning the gallery directory.

## Key Changes

### 1. **Enhanced `load_encodings_from_result_dir()` Function**
- Added progress callback support for real-time loading feedback
- Improved error handling for missing or corrupted .npy files
- Better statistics reporting (loaded count, missing files)
- No longer requires rescanning gallery directory

### 2. **New `validate_and_clean_manifest()` Function**
- Validates that all encoding files referenced in manifest exist
- Automatically removes invalid entries (missing files)
- Returns detailed statistics about validation results
- Saves cleaned manifest atomically

### 3. **Enhanced `check_encoded_result_exists()` Function**
- Now counts valid encoding files vs. total entries
- Returns `valid_files` field to track integrity
- Helps identify when manifest cleanup is needed

### 4. **UI Improvements**

#### Gallery Info Tab
- Shows count of valid vs. total encoded files
- Displays "Clean Manifest" button when invalid entries detected
- Automatic rerun after cleanup for updated display

#### Compare Images Tab
- Added progress bar when loading from manifest
- Shows real-time file loading status (current/total)
- Better feedback on loading success/failures

## How It Works

### Loading Process
1. **Read manifest.json** - Parse the JSON file containing all encoding metadata
2. **Check file existence** - Verify each .npy file exists before loading
3. **Load encodings** - Load valid .npy files into memory with progress tracking
4. **Handle duplicates** - Automatically rename duplicate basenames with suffixes
5. **Create gallery** - Build CNNGallerySet with path mapping for image lookup

### Validation Process
1. **Check manifest** - Iterate through all manifest entries
2. **Verify files** - Check if corresponding .npy files exist
3. **Clean invalid** - Remove entries where files are missing
4. **Save manifest** - Atomically save cleaned manifest

## Benefits

### Performance
- ✅ No directory scanning required
- ✅ Direct file loading from manifest
- ✅ Progress tracking for large galleries
- ✅ Efficient memory usage

### Reliability
- ✅ Validates file existence before loading
- ✅ Handles missing files gracefully
- ✅ Automatic manifest cleanup
- ✅ Better error messages

### User Experience
- ✅ Real-time progress feedback
- ✅ Clear status indicators
- ✅ Easy manifest maintenance
- ✅ Visual validation tools

## Usage

### Normal Workflow
1. Load gallery with "Save encodings to disk" enabled (first time)
2. Use "Compare from Cache" mode for fast loading
3. App loads directly from manifest.json - no rescanning!

### Maintenance Workflow
1. Check "Encoded results" status in Gallery Info
2. If showing "X/Y files valid", click "Clean Manifest"
3. Invalid entries are removed automatically
4. Continue using compare mode normally

## File Structure
```
encoded_result/
├── manifest.json          # Index of all encodings
├── 1.npy                 # Individual encoding files
├── 100007.npy
├── ...
└── [8963 more .npy files]
```

## Technical Details

### Manifest Format
```json
{
  "D:\\path\\to\\image.png": {
    "original_path": "D:\\path\\to\\image.png",
    "basename": "image.png",
    "encoding_file": "image.npy",
    "encoding_shape": [512],
    "encoding_dtype": "float32"
  }
}
```

### Path Mapping
- **Unique filename**: Handles duplicate basenames (e.g., `1.png`, `1_1.png`, `1_2.png`)
- **Original path**: Full path stored for image lookup
- **Path map**: Dictionary mapping unique names to original paths

### Progress Callback
```python
def progress_callback(current, total, filename):
    progress = current / total
    progress_bar.progress(progress)
    status_text.text(f"Loading: {filename} ({current}/{total})")
```

## Error Handling

### Missing Files
- Logs warning with list of missing files (first 5 shown)
- Continues loading valid files
- Doesn't crash if some files are missing

### Corrupt Files
- Catches numpy load errors
- Reports specific file that failed
- Continues with remaining files

### Empty Manifest
- Shows clear error message
- Suggests running gallery load with "Save" option
- Prevents crash from empty dataset

## Future Enhancements

### Possible Improvements
- [ ] Async loading for even faster performance
- [ ] Incremental manifest updates (add/remove specific files)
- [ ] Manifest versioning for compatibility checking
- [ ] Automatic backup before cleaning
- [ ] Batch validation UI for large galleries

### Performance Optimization
- [ ] Memory-mapped loading for huge galleries (100k+ files)
- [ ] Lazy loading (load on demand)
- [ ] Compression of .npy files
- [ ] Multi-threaded loading

## Testing Checklist

- [x] Load from manifest with all files present
- [x] Load from manifest with some files missing
- [x] Clean manifest removes invalid entries
- [x] Progress bar shows correctly
- [x] Duplicate filename handling works
- [x] Path mapping resolves correctly
- [x] UI updates after cleaning
- [x] Error messages are clear

## Notes

- Manifest is saved atomically to prevent corruption
- Cleaning is non-destructive (only removes manifest entries, not .npy files)
- Original image paths are preserved for cross-directory support
- Works with both local and external gallery directories

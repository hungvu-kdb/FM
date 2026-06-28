"""Streamlit web interface for facial recognition.

This app provides a user-friendly interface to:
1. Upload a query image from computer or URL
2. Find the most similar face in the gallery
3. Display top matching results with similarity scores
"""

import os
import math
import tempfile
import json
import concurrent.futures
from io import BytesIO
from typing import Optional, Dict, List

import numpy as np
import streamlit as st
from PIL import Image
import requests

# Import CNN implementation
from CNN import (
    CNNEncoder,
    CNNMatcher,
    CNNCache,
    CNNGalleryManager,
    CNNGallerySet,
    CNNCacheEntry,
    ImageDecodeError
)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
DEFAULT_GALLERY = r"d:\Mini-Project\FM\sample"
CACHE_FILENAME = ".cnn_encodings.npz"
ENCODED_RESULT_DIR = r"d:\Mini-Project\FM\encoded_result"
DEFAULT_THRESHOLD = 0.7
DEFAULT_TOP_K = 5

# Parallel processing configuration
NUM_CHUNKS = 10       # Split the to-be-cached file list into this many smaller lists
MAX_WORKERS = 3       # Number of worker threads running at the same time


# ---------------------------------------------------------------------------
# Session State Initialization
# ---------------------------------------------------------------------------
def init_session_state():
    """Initialize session state variables."""
    if 'encoder' not in st.session_state:
        st.session_state.encoder = None
    if 'gallery' not in st.session_state:
        st.session_state.gallery = None
    if 'matcher' not in st.session_state:
        st.session_state.matcher = None
    if 'gallery_loaded' not in st.session_state:
        st.session_state.gallery_loaded = False
    if 'stop_loading' not in st.session_state:
        st.session_state.stop_loading = False
    if 'loading_in_progress' not in st.session_state:
        st.session_state.loading_in_progress = False


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------
def sanitize_filename(basename: str) -> str:
    """Convert image basename to encoding output filename.
    
    Example: "100007.png" -> "100007.npy"
    """
    name_without_ext = os.path.splitext(basename)[0]
    return f"{name_without_ext}.npy"


def load_manifest(output_dir: str = ENCODED_RESULT_DIR) -> Dict[str, any]:
    """Load existing manifest.json file.
    
    Args:
        output_dir: Directory containing manifest.json.
        
    Returns:
        Dictionary of manifest entries, empty dict if not found.
    """
    manifest_path = os.path.join(output_dir, "manifest.json")
    if os.path.exists(manifest_path):
        try:
            with open(manifest_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def is_path_in_manifest(image_path: str, manifest: Dict[str, any]) -> bool:
    """Check if an image path exists in the manifest.
    
    Args:
        image_path: Full path to image file.
        manifest: Manifest dictionary.
        
    Returns:
        True if path exists in manifest, False otherwise.
    """
    return image_path in manifest


def save_encoding_immediately(filename: str, embedding: np.ndarray, image_path: str, manifest: Dict[str, any], output_dir: str = ENCODED_RESULT_DIR) -> None:
    """Save a single encoding immediately to encoded_result directory.
    
    Args:
        filename: Image filename (e.g., "100007.png").
        embedding: Face embedding array.
        image_path: Full path to original image.
        manifest: Current manifest dictionary (will be updated in-place).
        output_dir: Output directory for encoded results.
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # Save encoding as .npy file
    output_filename = sanitize_filename(filename)
    output_path = os.path.join(output_dir, output_filename)
    np.save(output_path, embedding)
    
    # Add/update entry in manifest (in-place update)
    manifest[image_path] = {
        "original_path": image_path,
        "basename": filename,
        "encoding_file": output_filename,
        "encoding_shape": list(embedding.shape),
        "encoding_dtype": str(embedding.dtype)
    }
    
    # Save manifest immediately after each encoding
    save_manifest(manifest, output_dir)


def save_manifest(manifest: Dict[str, any], output_dir: str = ENCODED_RESULT_DIR) -> None:
    """Save manifest.json file atomically.
    
    Args:
        manifest: Manifest dictionary to save.
        output_dir: Output directory for manifest.json.
    """
    os.makedirs(output_dir, exist_ok=True)
    manifest_path = os.path.join(output_dir, "manifest.json")
    
    # Save manifest atomically
    import tempfile
    manifest_dir = os.path.dirname(manifest_path)
    fd, tmp_path = tempfile.mkstemp(suffix=".json", dir=manifest_dir, text=True)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
        os.replace(tmp_path, manifest_path)
    except BaseException:
        try:
            os.remove(tmp_path)
        except OSError:
            pass
        raise


def validate_and_clean_manifest(output_dir: str = ENCODED_RESULT_DIR) -> Dict[str, any]:
    """Validate manifest and remove entries where encoding files don't exist.
    
    Args:
        output_dir: Directory containing manifest.json and .npy files.
        
    Returns:
        Dictionary with validation statistics:
        - total: Total entries in original manifest
        - valid: Number of valid entries (files exist)
        - removed: Number of entries removed (files missing)
        - cleaned_manifest: Cleaned manifest dictionary
    """
    manifest = load_manifest(output_dir)
    
    if not manifest:
        return {
            "total": 0,
            "valid": 0,
            "removed": 0,
            "cleaned_manifest": {}
        }
    
    total = len(manifest)
    cleaned = {}
    removed = 0
    
    for original_path, entry in manifest.items():
        encoding_file = os.path.join(output_dir, entry['encoding_file'])
        if os.path.exists(encoding_file):
            cleaned[original_path] = entry
        else:
            removed += 1
    
    # Save cleaned manifest
    if removed > 0:
        save_manifest(cleaned, output_dir)
    
    return {
        "total": total,
        "valid": len(cleaned),
        "removed": removed,
        "cleaned_manifest": cleaned
    }


def save_encodings_to_result_dir(gallery: CNNGallerySet, gallery_dir: str, output_dir: str = ENCODED_RESULT_DIR) -> Dict[str, any]:
    """Save gallery encodings to encoded_result directory.
    
    Args:
        gallery: CNNGallerySet with filenames and embeddings.
        gallery_dir: Original gallery directory path.
        output_dir: Output directory for encoded results.
        
    Returns:
        Dictionary with export statistics.
    """
    os.makedirs(output_dir, exist_ok=True)
    
    manifest = {}
    successful = 0
    
    for filename, embedding in zip(gallery.filenames, gallery.matrix):
        # Full path to original image
        image_path = os.path.join(gallery_dir, filename)
        
        # Output filename
        output_filename = sanitize_filename(filename)
        output_path = os.path.join(output_dir, output_filename)
        
        # Save encoding as .npy file
        np.save(output_path, embedding)
        
        # Record in manifest
        manifest[image_path] = {
            "original_path": image_path,
            "basename": filename,
            "encoding_file": output_filename,
            "encoding_shape": list(embedding.shape),
            "encoding_dtype": str(embedding.dtype)
        }
        
        successful += 1
    
    # Save manifest
    manifest_path = os.path.join(output_dir, "manifest.json")
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    
    return {
        "successful": successful,
        "output_dir": output_dir,
        "manifest_path": manifest_path
    }


def check_encoded_result_exists(gallery_dir: str, output_dir: str = ENCODED_RESULT_DIR) -> Dict[str, any]:
    """Check if encoded results exist and are up-to-date.
    
    Args:
        gallery_dir: Gallery directory to check against.
        output_dir: Encoded result directory.
        
    Returns:
        Dictionary with status information:
        - exists: bool (True if manifest exists)
        - count: int (number of encodings in manifest)
        - gallery_count: int (number of PNG files in gallery)
        - up_to_date: bool (True if counts match)
        - valid_files: int (number of encoding files that actually exist)
    """
    manifest_path = os.path.join(output_dir, "manifest.json")
    
    if not os.path.exists(manifest_path):
        return {
            "exists": False,
            "count": 0,
            "gallery_count": 0,
            "up_to_date": False,
            "valid_files": 0
        }
    
    # Load manifest
    try:
        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest = json.load(f)
    except Exception:
        return {
            "exists": False,
            "count": 0,
            "gallery_count": 0,
            "up_to_date": False,
            "valid_files": 0
        }
    
    # Count PNG files in gallery
    png_count = 0
    if os.path.exists(gallery_dir):
        for filename in os.listdir(gallery_dir):
            if filename.lower().endswith('.png'):
                png_count += 1
    
    # Count valid encoding files
    valid_files = 0
    for entry in manifest.values():
        encoding_file = os.path.join(output_dir, entry['encoding_file'])
        if os.path.exists(encoding_file):
            valid_files += 1
    
    manifest_count = len(manifest)
    
    return {
        "exists": True,
        "count": manifest_count,
        "gallery_count": png_count,
        "up_to_date": (manifest_count == png_count),
        "valid_files": valid_files
    }


def load_encodings_from_result_dir(output_dir: str = ENCODED_RESULT_DIR, progress_callback=None) -> Optional[tuple]:
    """Load encodings from encoded_result directory using manifest.json.
    
    Args:
        output_dir: Directory containing manifest.json and .npy files.
        progress_callback: Optional callback function(current, total, filename) for progress tracking.
        
    Returns:
        Tuple of (CNNGallerySet, path_map) or None if loading fails.
        path_map: dict mapping unique filenames to original full paths for image lookup.
    """
    manifest_path = os.path.join(output_dir, "manifest.json")
    
    if not os.path.exists(manifest_path):
        st.error(f"❌ Manifest file not found: {manifest_path}")
        return None
    
    try:
        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest = json.load(f)
        
        if not manifest:
            st.error("❌ Manifest file is empty")
            return None
        
        total_entries = len(manifest)
        st.info(f"📦 Found {total_entries} entries in manifest")
        
        # Load all encodings with unique filenames
        filenames = []
        embeddings = []
        seen_basenames = {}  # Track duplicate basenames
        path_map = {}  # Map unique names to original full paths
        
        missing_files = []
        loaded_count = 0
        
        for idx, (original_path, entry) in enumerate(manifest.items(), 1):
            encoding_file = os.path.join(output_dir, entry['encoding_file'])
            
            # Progress callback
            if progress_callback:
                progress_callback(idx, total_entries, entry['basename'])
            
            # Check if encoding file exists
            if os.path.exists(encoding_file):
                try:
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
                    path_map[unique_name] = entry['original_path']  # Store full original path
                    loaded_count += 1
                except Exception as e:
                    missing_files.append(f"{entry['encoding_file']} (error: {str(e)[:30]})")
            else:
                missing_files.append(entry['encoding_file'])
        
        if missing_files:
            st.warning(f"⚠️ {len(missing_files)} encoding files not found or failed to load (showing first 5):")
            for mf in missing_files[:5]:
                st.caption(f"  - {mf}")
        
        if not embeddings:
            st.error(f"❌ No valid encoding files found in {output_dir}")
            return None
        
        # Check for duplicates after processing
        duplicates = {k: v for k, v in seen_basenames.items() if v > 0}
        if duplicates:
            st.info(f"ℹ️ Handled {len(duplicates)} duplicate filenames by adding suffixes")
        
        st.success(f"✅ Successfully loaded {loaded_count} encodings from manifest")
        
        # Stack into matrix
        from CNN import EMBEDDING_DIM
        matrix = np.stack(embeddings)
        
        gallery = CNNGallerySet(filenames=filenames, matrix=matrix)
        return (gallery, path_map)
    
    except Exception as e:
        st.error(f"❌ Error loading encodings: {str(e)}")
        st.exception(e)
        return None


@st.cache_resource
def load_models(device: str = "auto"):
    """Load and cache the CNN encoder (expensive operation)."""
    device_arg = None if device == "auto" else device
    encoder = CNNEncoder(device=device_arg)
    return encoder


def _build_gallery_from_manifest(manifest: Dict[str, any], output_dir: str = ENCODED_RESULT_DIR):
    """Build a CNNGallerySet from encodings referenced in the manifest.
    
    Used when all gallery images are already encoded, so the session still
    has a usable gallery without re-encoding anything.
    
    Args:
        manifest: Manifest dictionary.
        output_dir: Directory containing the .npy encoding files.
        
    Returns:
        CNNGallerySet or None if no valid encodings found.
    """
    from CNN import CNNGallerySet, EMBEDDING_DIM
    
    filenames = []
    embeddings = []
    seen_basenames = {}
    
    for original_path, entry in manifest.items():
        encoding_file = os.path.join(output_dir, entry['encoding_file'])
        if not os.path.exists(encoding_file):
            continue
        try:
            encoding = np.load(encoding_file)
        except Exception:
            continue
        
        basename = entry['basename']
        if basename in seen_basenames:
            seen_basenames[basename] += 1
            unique_name = f"{os.path.splitext(basename)[0]}_{seen_basenames[basename]}{os.path.splitext(basename)[1]}"
        else:
            seen_basenames[basename] = 0
            unique_name = basename
        
        filenames.append(unique_name)
        embeddings.append(encoding)
    
    if not embeddings:
        return None
    
    matrix = np.stack(embeddings)
    return CNNGallerySet(filenames=filenames, matrix=matrix)


def _split_into_chunks(items: List[str], num_chunks: int) -> List[List[str]]:
    """Split a list of items into up to `num_chunks` roughly equal smaller lists.
    
    Args:
        items: List of file paths to split.
        num_chunks: Desired number of chunks.
        
    Returns:
        List of chunks (each chunk is a list of paths). Empty input yields [].
    """
    if not items:
        return []
    # Don't create more chunks than items
    num_chunks = max(1, min(num_chunks, len(items)))
    chunk_size = math.ceil(len(items) / num_chunks)
    return [items[i:i + chunk_size] for i in range(0, len(items), chunk_size)]


def _process_single_file(image_path: str, cache: "CNNCache", cached_entries: dict, encoder) -> dict:
    """Encode or reuse a single image. Pure worker function (no Streamlit / shared state writes).
    
    Args:
        image_path: Full path to the image.
        cache: CNNCache instance (used only for read-only signature checks).
        cached_entries: Existing cached entries (read-only).
        encoder: CNNEncoder instance.
        
    Returns:
        Result dict with keys: image_path, filename, status, embedding, size, mtime, error.
        status is one of: 'reused', 'encoded', 'no_face', 'failed'.
    """
    filename = os.path.basename(image_path)
    size, mtime = cache.file_signature(image_path)
    sig = (size, mtime)
    
    # Reuse cached entry if signature matches
    cached = cached_entries.get(image_path)
    if cached is not None and cached.signature == sig:
        return {
            'image_path': image_path, 'filename': filename, 'status': 'reused',
            'embedding': cached.embedding, 'size': size, 'mtime': mtime, 'error': None,
        }
    
    # Otherwise encode
    try:
        embedding = encoder.encode_image(image_path)
        if embedding is not None:
            return {
                'image_path': image_path, 'filename': filename, 'status': 'encoded',
                'embedding': embedding, 'size': size, 'mtime': mtime, 'error': None,
            }
        return {
            'image_path': image_path, 'filename': filename, 'status': 'no_face',
            'embedding': None, 'size': size, 'mtime': mtime, 'error': None,
        }
    except Exception as e:
        return {
            'image_path': image_path, 'filename': filename, 'status': 'failed',
            'embedding': None, 'size': size, 'mtime': mtime, 'error': str(e),
        }


def _process_chunk(chunk: List[str], cache: "CNNCache", cached_entries: dict, encoder) -> List[dict]:
    """Process one chunk of files sequentially inside a worker thread.
    
    Returns a list of per-file result dicts (see _process_single_file).
    """
    return [_process_single_file(path, cache, cached_entries, encoder) for path in chunk]


def load_gallery_with_progress(_encoder, gallery_dir: str, save_encodings: bool = False, manifest: Dict[str, any] = None):
    """Load gallery embeddings with progress tracking and manifest-based skipping.
    
    Args:
        _encoder: CNNEncoder instance.
        gallery_dir: Gallery directory path.
        save_encodings: If True, save new encodings immediately to encoded_result.
        manifest: Existing manifest dictionary (if save_encodings is True).
    
    Note: Cannot use @st.cache_data because we need to show progress.
    Instead, we'll cache the result in session state.
    """
    cache_path = os.path.join(gallery_dir, CACHE_FILENAME)
    cache = CNNCache(cache_path)
    
    # Step 1: List all PNG files in the gallery directory using os.listdir
    all_png_files = []
    for filename in os.listdir(gallery_dir):
        if filename.lower().endswith('.png'):
            all_png_files.append(os.path.join(gallery_dir, filename))
    all_png_files.sort()
    
    total_in_dir = len(all_png_files)
    
    if total_in_dir == 0:
        st.error("No PNG files found in gallery directory!")
        return None
    
    st.info(f"📊 Found **{total_in_dir}** images in gallery directory")
    
    # Step 2: Remove files that already exist in the manifest.
    # Only files NOT in the manifest need to be encoded/cached.
    if save_encodings and manifest is not None:
        png_files = [p for p in all_png_files if not is_path_in_manifest(p, manifest)]
        already_in_manifest = total_in_dir - len(png_files)
        
        if already_in_manifest > 0:
            st.info(f"📦 **{already_in_manifest}** images already in manifest (will be skipped)")
        
        if len(png_files) == 0:
            st.success(f"✅ All {total_in_dir} images are already encoded in the manifest. Nothing to do!")
            # Build gallery from existing manifest so the session still has data
            return _build_gallery_from_manifest(manifest)
        
        st.info(f"🔄 **{len(png_files)}** images need to be encoded")
    else:
        # Not saving to manifest: process all files
        png_files = all_png_files
    
    # Total files we will actually process this run
    total_files = len(png_files)
    
    # Load existing cache
    cached_entries = cache.load()
    num_cached = len(cached_entries)
    
    if num_cached > 0:
        st.success(f"💾 Found **{num_cached}** cached embeddings")
    
    # Create progress tracking
    progress_bar = st.progress(0)
    status_text = st.empty()
    stats_text = st.empty()
    
    # Create expandable details section
    with st.expander("📋 Show processing details", expanded=False):
        details_container = st.container()
        details_text = details_container.empty()
        processing_details = []
    
    # Track statistics
    stats = {
        'processed': 0,
        'reused': 0,
        'encoded': 0,
        'no_face': 0,
        'failed': 0,
        'saved': 0,  # Track how many were saved immediately
    }
    
    entries = {}
    
    # ------------------------------------------------------------------
    # Parallel processing: split the to-be-cached list into NUM_CHUNKS
    # smaller lists and run MAX_WORKERS threads at the same time.
    # ------------------------------------------------------------------
    # Warm up the encoder models on the main thread first. The encoder uses
    # lazy model initialization which is NOT thread-safe; initializing here
    # avoids a race where multiple worker threads try to build the models.
    try:
        _encoder._init_models()
    except Exception:
        # If warm-up fails, processing will surface the error per-file anyway.
        pass
    
    chunks = _split_into_chunks(png_files, NUM_CHUNKS)
    st.info(f"🧵 Split {total_files} images into **{len(chunks)}** chunks, running **{MAX_WORKERS}** threads at a time")
    
    processed_count = 0
    cancelled = False
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Submit each chunk to the thread pool
        future_to_chunk = {
            executor.submit(_process_chunk, chunk, cache, cached_entries, _encoder): chunk_idx
            for chunk_idx, chunk in enumerate(chunks)
        }
        
        # Collect results as chunks complete
        for future in concurrent.futures.as_completed(future_to_chunk):
            # Check if stop was requested
            if st.session_state.get('stop_loading', False):
                cancelled = True
                # Cancel any not-yet-started chunks
                for f in future_to_chunk:
                    f.cancel()
                break
            
            try:
                chunk_results = future.result()
            except Exception as e:
                processing_details.append(f"❌ Chunk failed: {str(e)[:50]}")
                continue
            
            # Merge results from this chunk into shared state (main thread only)
            for res in chunk_results:
                image_path = res['image_path']
                filename = res['filename']
                status = res['status']
                
                if status == 'reused':
                    entries[image_path] = cached_entries[image_path]
                    stats['reused'] += 1
                    if save_encodings and manifest is not None:
                        try:
                            save_encoding_immediately(filename, res['embedding'], image_path, manifest, ENCODED_RESULT_DIR)
                            stats['saved'] += 1
                            processing_details.append(f"💾 {filename} - Reused & saved to manifest")
                        except Exception as cb_error:
                            processing_details.append(f"⚠️ {filename} - Reused but save failed: {str(cb_error)[:30]}")
                    else:
                        processing_details.append(f"✅ {filename} - Reused from cache")
                
                elif status == 'encoded':
                    from CNN import CNNCacheEntry
                    entries[image_path] = CNNCacheEntry(
                        image_path=image_path,
                        size_bytes=res['size'],
                        mtime=res['mtime'],
                        embedding=res['embedding']
                    )
                    stats['encoded'] += 1
                    if save_encodings and manifest is not None:
                        try:
                            save_encoding_immediately(filename, res['embedding'], image_path, manifest, ENCODED_RESULT_DIR)
                            stats['saved'] += 1
                            processing_details.append(f"💾 {filename} - Encoded & saved")
                        except Exception as cb_error:
                            processing_details.append(f"⚠️ {filename} - Encoded but save failed: {str(cb_error)[:30]}")
                    else:
                        processing_details.append(f"🔄 {filename} - Newly encoded")
                
                elif status == 'no_face':
                    stats['no_face'] += 1
                    processing_details.append(f"⚠️ {filename} - No face detected")
                
                else:  # 'failed'
                    stats['failed'] += 1
                    processing_details.append(f"❌ {filename} - Failed: {str(res['error'])[:50]}")
                
                processed_count += 1
            
            stats['processed'] = processed_count
            
            # Update progress after each completed chunk
            progress = min(processed_count / total_files, 1.0)
            progress_bar.progress(progress)
            status_text.text(f"Processed {processed_count}/{total_files} images...")
            
            # Update stats display
            stats_display = (
                f"**Progress:** {stats['processed']}/{total_files} | "
                f"**Reused:** {stats['reused']} | "
                f"**Encoded:** {stats['encoded']} | "
                f"**No face:** {stats['no_face']} | "
                f"**Failed:** {stats['failed']}"
            )
            if save_encodings:
                stats_display += f" | **Saved:** {stats['saved']}"
            stats_text.markdown(stats_display)
            
            # Update details (show last 10 only)
            recent_details = processing_details[-10:] if len(processing_details) > 10 else processing_details
            details_text.text("\n".join(recent_details))
    
    # Handle cancellation
    if cancelled:
        status_text.text("⚠️ Loading cancelled by user")
        st.warning(f"⚠️ **Loading stopped!** Processed {stats['processed']}/{total_files} images before cancellation.")
        st.session_state.stop_loading = False
        st.session_state.loading_in_progress = False
        
        if entries:
            status_text.text("Saving partial cache...")
            cache.save(entries)
            from CNN import CNNGallerySet
            paths = list(entries.keys())
            filenames = [os.path.basename(p) for p in paths]
            matrix = np.stack([entries[p].embedding for p in paths])
            return CNNGallerySet(filenames=filenames, matrix=matrix)
        return None
    
    # Save cache
    status_text.text("Saving cache to disk...")
    cache.save(entries)
    
    # Build gallery set
    from CNN import CNNGallerySet, EMBEDDING_DIM
    paths = list(entries.keys())
    filenames = [os.path.basename(p) for p in paths]
    
    if paths:
        matrix = np.stack([entries[p].embedding for p in paths])
    else:
        matrix = np.empty((0, EMBEDDING_DIM), dtype=np.float64)
    
    gallery = CNNGallerySet(filenames=filenames, matrix=matrix)
    
    # Clear progress indicators
    progress_bar.empty()
    status_text.empty()
    stats_text.empty()
    
    # Clear loading flag
    st.session_state.loading_in_progress = False
    
    # Show final summary
    if stats['encoded'] > 0:
        summary_msg = (
            f"✅ Gallery loaded: **{len(gallery)}** faces | "
            f"Newly encoded: **{stats['encoded']}** | "
            f"Reused: **{stats['reused']}**"
        )
        
        if save_encodings and stats['saved'] > 0:
            summary_msg += f" | **Saved to disk: {stats['saved']}**"
        
        st.success(summary_msg)
    else:
        st.success(
            f"✅ Gallery loaded: **{len(gallery)}** faces "
            f"(all from cache)"
        )
    
    if stats['no_face'] > 0:
        st.warning(f"⚠️ {stats['no_face']} images skipped (no face detected)")
    
    if stats['failed'] > 0:
        st.error(f"❌ {stats['failed']} images failed to process")
    
    return gallery


def download_image_from_url(url: str) -> Optional[Image.Image]:
    """Download an image from a URL.
    
    Args:
        url: Image URL to download.
        
    Returns:
        PIL Image or None if download fails.
    """
    try:
        response = requests.get(url, timeout=10, stream=True)
        response.raise_for_status()
        
        # Check content type
        content_type = response.headers.get('content-type', '')
        if 'image' not in content_type.lower():
            st.error(f"URL does not point to an image. Content-Type: {content_type}")
            return None
        
        # Load image
        img = Image.open(BytesIO(response.content)).convert('RGB')
        return img
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to download image: {e}")
        return None
    except Exception as e:
        st.error(f"Failed to process image from URL: {e}")
        return None


def save_uploaded_image(uploaded_file) -> str:
    """Save uploaded file to temporary location.
    
    Args:
        uploaded_file: Streamlit UploadedFile object.
        
    Returns:
        Path to temporary file.
    """
    suffix = os.path.splitext(uploaded_file.name)[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
        tmp_file.write(uploaded_file.getbuffer())
        return tmp_file.name


def save_pil_image(image: Image.Image) -> str:
    """Save PIL Image to temporary location.
    
    Args:
        image: PIL Image object.
        
    Returns:
        Path to temporary file.
    """
    with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp_file:
        image.save(tmp_file, format='PNG')
        return tmp_file.name


def format_similarity(similarity: float) -> str:
    """Format similarity score with color coding."""
    if similarity >= 0.8:
        return f"🟢 {similarity:.3f} (High)"
    elif similarity >= 0.6:
        return f"🟡 {similarity:.3f} (Medium)"
    else:
        return f"🔴 {similarity:.3f} (Low)"


# ---------------------------------------------------------------------------
# Main App
# ---------------------------------------------------------------------------
def main():
    """Main Streamlit application."""
    
    # Page config
    st.set_page_config(
        page_title="Facial Recognition App",
        page_icon="👤",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Initialize session state
    init_session_state()
    
    # Title and description
    st.title("👤 Facial Recognition System")
    st.markdown("""
    **Two main features:**
    1. **Load/Reload Gallery** - Load face encodings from your gallery
    2. **Compare Images** - Find matching faces in the gallery
    """)
    
    # Sidebar - Configuration
    st.sidebar.header("⚙️ Settings")
    
    # Device selection
    device_option = st.sidebar.selectbox(
        "Computation Device",
        ["auto", "cpu", "cuda"],
        help="Select 'cuda' if you have NVIDIA GPU"
    )
    
    # Gallery directory
    gallery_dir = st.sidebar.text_input(
        "Gallery Directory",
        value=DEFAULT_GALLERY,
        help="Path to gallery images (*.png)"
    )
    
    # Threshold
    threshold = st.sidebar.slider(
        "Similarity Threshold",
        min_value=0.0,
        max_value=1.0,
        value=DEFAULT_THRESHOLD,
        step=0.05,
        help="Minimum similarity for match"
    )
    
    # Top K results
    top_k = st.sidebar.slider(
        "Number of Results",
        min_value=1,
        max_value=20,
        value=DEFAULT_TOP_K,
        help="Number of top matches to show"
    )
    
    st.sidebar.markdown("---")
    
    # Display gallery status
    if st.session_state.gallery_loaded:
        st.sidebar.success(
            f"✅ **Gallery Loaded**\n\n"
            f"📊 {len(st.session_state.gallery)} faces ready"
        )
    else:
        st.sidebar.info("⚠️ Gallery not loaded")
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("""
    ### 📖 Quick Guide
    1. **Load Gallery** - Click button below
    2. **Compare** - Upload image to find matches
    3. **Results** - View top matches with scores
    """)
    
    # Main content - Two feature tabs
    tab1, tab2 = st.tabs(["🔄 Load/Reload Gallery", "🔍 Compare Images"])
    
    # ========== TAB 1: LOAD/RELOAD GALLERY ==========
    with tab1:
        st.header("🔄 Load/Reload Gallery")
        st.markdown("""
        Load face encodings from the gallery directory. This needs to be done once before comparing images.
        """)
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.subheader("📁 Gallery Info")
            
            # Show loading status if in progress
            if st.session_state.get('loading_in_progress', False):
                st.warning("⏳ **Loading in progress...**")
            
            st.write(f"**Directory:** `{gallery_dir}`")
            
            if os.path.isdir(gallery_dir):
                png_count = sum(1 for f in os.listdir(gallery_dir) if f.lower().endswith('.png'))
                st.write(f"**Images found:** {png_count} PNG files")
                
                # Check cache status
                cache_path = os.path.join(gallery_dir, CACHE_FILENAME)
                if os.path.exists(cache_path):
                    file_size = os.path.getsize(cache_path) / (1024 * 1024)
                    st.write(f"**Cache:** ✅ Available ({file_size:.2f} MB)")
                else:
                    st.write(f"**Cache:** ⚠️ Not found")
                
                # Check encoded results
                encoded_status = check_encoded_result_exists(gallery_dir, ENCODED_RESULT_DIR)
                if encoded_status["exists"]:
                    valid_count = encoded_status["valid_files"]
                    total_count = encoded_status["count"]
                    
                    if valid_count == total_count:
                        st.write(f"**Encoded results:** ✅ {total_count} files (all valid)")
                    else:
                        st.write(f"**Encoded results:** ⚠️ {valid_count}/{total_count} files valid")
                    
                    # Validate manifest button
                    if valid_count < total_count:
                        if st.button("🔍 Clean Manifest", help="Remove entries with missing files"):
                            with st.spinner("Cleaning manifest..."):
                                validation = validate_and_clean_manifest(ENCODED_RESULT_DIR)
                                
                                if validation["removed"] > 0:
                                    st.warning(f"⚠️ Removed {validation['removed']} invalid entries from manifest")
                                    st.success(f"✅ Manifest now has {validation['valid']} valid entries")
                                    st.rerun()
                                else:
                                    st.success(f"✅ All {validation['valid']} entries are valid!")
                else:
                    st.write(f"**Encoded results:** ⚠️ Not exported")
            else:
                st.error("❌ Directory not found!")
        
        with col2:
            st.subheader("⚙️ Load Options")
            
            save_result = st.checkbox(
                "💾 Save encodings to disk",
                value=st.session_state.get('auto_save_enabled', False),
                help="Save to encoded_result/ for faster loading next time"
            )
            st.session_state.auto_save_enabled = save_result
            
            if save_result:
                st.caption("✅ Will save new encodings to `encoded_result/`")
            else:
                st.caption("⚠️ Won't save encodings (slower next time)")
        
        st.markdown("---")
        
        # Load button and Stop button
        col_btn1, col_btn2 = st.columns([1, 1])
        
        with col_btn1:
            load_button = st.button(
                "🔄 Load/Reload Gallery", 
                type="primary", 
                use_container_width=True, 
                disabled=st.session_state.get('loading_in_progress', False)
            )
        
        with col_btn2:
            stop_button = st.button(
                "⏹️ Stop Loading", 
                type="secondary", 
                use_container_width=True, 
                disabled=not st.session_state.get('loading_in_progress', False)
            )
        
        # Handle stop button
        if stop_button:
            st.session_state.stop_loading = True
            st.warning("⚠️ Stop requested... waiting for current image to finish processing.")
        
        # Handle load button
        if load_button:
            if not os.path.isdir(gallery_dir):
                st.error(f"❌ Gallery directory not found: {gallery_dir}")
            else:
                # Set loading flag
                st.session_state.loading_in_progress = True
                st.session_state.stop_loading = False
                
                # Load encoder
                st.session_state.encoder = load_models(device_option)
                
                # Load existing manifest if save_result is enabled
                manifest = None
                if save_result:
                    manifest = load_manifest(ENCODED_RESULT_DIR)
                
                # Load gallery with progress tracking
                st.session_state.gallery = load_gallery_with_progress(
                    st.session_state.encoder,
                    gallery_dir,
                    save_encodings=save_result,
                    manifest=manifest
                )
                
                # Clear loading flag
                st.session_state.loading_in_progress = False
                
                if st.session_state.gallery is not None:
                    # Create matcher
                    st.session_state.matcher = CNNMatcher(threshold=threshold)
                    st.session_state.gallery_loaded = True
                    
                    # Show success message based on whether it was stopped
                    if st.session_state.get('stop_loading', False):
                        st.info(f"ℹ️ Loading partially completed. Gallery has {len(st.session_state.gallery)} faces loaded.")
                        st.session_state.stop_loading = False
                    else:
                        st.success(f"✅ Gallery fully loaded with {len(st.session_state.gallery)} faces!")
                        st.balloons()
                else:
                    st.session_state.gallery_loaded = False
                    if not st.session_state.get('stop_loading', False):
                        st.error("❌ Failed to load gallery")
                    if not st.session_state.get('stop_loading', False):
                        st.error("❌ Failed to load gallery")
    
    # ========== TAB 2: COMPARE IMAGES ==========
    with tab2:
        st.header("🔍 Compare Images")
        
        st.markdown("Choose comparison mode and upload an image to find matching faces.")
        
        # Comparison mode selection
        st.subheader("📊 Comparison Mode")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**🗂️ Compare from Cache**")
            st.caption("Load pre-encoded results from `encoded_result/` folder")
            cache_available = check_encoded_result_exists(gallery_dir, ENCODED_RESULT_DIR)["exists"]
            if cache_available:
                st.caption("✅ Cache available")
            else:
                st.caption("⚠️ No cache found")
        
        with col2:
            st.markdown("**💾 Compare from Loaded Gallery**")
            st.caption("Use gallery loaded in current session")
            if st.session_state.gallery_loaded:
                st.caption(f"✅ {len(st.session_state.gallery)} faces loaded")
            else:
                st.caption("⚠️ Gallery not loaded")
        
        comparison_mode = st.radio(
            "Select comparison mode:",
            ["🗂️ Compare from Cache (encoded_result/)", "💾 Compare from Loaded Gallery (current session)"],
            help="Cache mode loads from disk, Loaded Gallery uses current session data"
        )
        
        # Check availability based on mode
        use_cache_mode = comparison_mode.startswith("🗂️")
        
        if use_cache_mode and not cache_available:
            st.error("❌ **Cache not available!** No encoded results found in `encoded_result/` folder. Please load gallery with 'Save encodings to disk' enabled first.")
            return
        
        if not use_cache_mode and not st.session_state.gallery_loaded:
            st.error("❌ **Gallery not loaded!** Please load the gallery first in the 'Load/Reload Gallery' tab.")
            return
        
        st.markdown("---")
        
        # Update matcher threshold if changed
        if st.session_state.matcher is not None:
            st.session_state.matcher.threshold = threshold
        
        # Input method selection
        input_method = st.radio(
            "Choose input method:",
            ["📤 Upload from Computer", "🌐 Load from URL"],
            horizontal=True
        )
        
        query_image = None
        query_path = None
        
        if input_method == "📤 Upload from Computer":
            uploaded_file = st.file_uploader(
                "Choose an image file",
                type=["png", "jpg", "jpeg", "bmp"],
                help="Select an image containing a face"
            )
            
            if uploaded_file is not None:
                query_image = Image.open(uploaded_file).convert('RGB')
                query_path = save_uploaded_image(uploaded_file)
                
        else:  # Load from URL
            image_url = st.text_input(
                "Enter image URL:",
                placeholder="https://example.com/image.jpg"
            )
            
            if image_url:
                with st.spinner("Downloading image..."):
                    query_image = download_image_from_url(image_url)
                    if query_image is not None:
                        query_path = save_pil_image(query_image)
        
        # Display query image
        if query_image is not None:
            st.markdown("---")
            col1, col2 = st.columns([1, 2])
            
            with col1:
                st.subheader("Query Image")
                st.image(query_image, use_container_width=True)
            
            with col2:
                st.subheader("Image Info")
                st.write(f"**Size:** {query_image.size[0]} × {query_image.size[1]} pixels")
                st.write(f"**Format:** {query_image.format or 'N/A'}")
                st.write(f"**Mode:** {query_image.mode}")
                st.markdown("---")
                
                # Find matches button
                if st.button("🔍 Find Matches", type="primary", use_container_width=True):
                    with st.spinner("Encoding and comparing..."):
                        try:
                            # Load encoder if not already loaded
                            if st.session_state.encoder is None:
                                st.session_state.encoder = load_models(device_option)
                            
                            encoder = st.session_state.encoder
                            
                            # Encode query
                            query_embedding = encoder.encode_image(query_path)
                            
                            if query_embedding is None:
                                st.error("❌ No face detected in the query image. Please try another image.")
                            else:
                                results = None
                                
                                # Determine which gallery to use based on mode
                                if use_cache_mode:
                                    # Load gallery from cache with progress
                                    progress_bar = st.progress(0)
                                    status_text = st.empty()
                                    
                                    def progress_callback(current, total, filename):
                                        progress = current / total
                                        progress_bar.progress(progress)
                                        status_text.text(f"Loading: {filename} ({current}/{total})")
                                    
                                    st.info("🗂️ Loading encodings from manifest...")
                                    cache_result = load_encodings_from_result_dir(ENCODED_RESULT_DIR, progress_callback)
                                    
                                    # Clear progress indicators
                                    progress_bar.empty()
                                    status_text.empty()
                                    
                                    if cache_result is None:
                                        # Error already shown by load_encodings_from_result_dir
                                        pass
                                    else:
                                        cache_gallery, path_map = cache_result
                                        
                                        # Store path map for image lookup
                                        st.session_state.cache_path_map = path_map
                                        
                                        # Create temporary matcher for cache mode
                                        cache_matcher = CNNMatcher(threshold=threshold)
                                        results = cache_matcher.rank(query_embedding, cache_gallery, top_k=top_k)
                                        
                                        # Store mode info
                                        st.session_state.comparison_mode = "cache"
                                        st.session_state.comparison_source = f"encoded_result/ ({len(cache_gallery)} faces)"
                                else:
                                    # Use loaded gallery from session
                                    matcher = st.session_state.matcher
                                    gallery = st.session_state.gallery
                                    results = matcher.rank(query_embedding, gallery, top_k=top_k)
                                    
                                    # Store mode info
                                    st.session_state.comparison_mode = "loaded"
                                    st.session_state.comparison_source = f"Loaded gallery ({len(gallery)} faces)"
                                
                                if results is None:
                                    # Error already shown above
                                    pass
                                elif not results:
                                    st.warning("⚠️ No matches found in the gallery.")
                                else:
                                    # Store results in session state
                                    st.session_state.last_results = results
                                    st.session_state.last_query_image = query_image
                                    st.rerun()
                        
                        except ImageDecodeError as e:
                            st.error(f"❌ Failed to decode image: {e}")
                        except Exception as e:
                            st.error(f"❌ An error occurred: {e}")
                            st.exception(e)
                        finally:
                            # Cleanup temporary file
                            try:
                                if query_path and os.path.exists(query_path):
                                    os.unlink(query_path)
                            except:
                                pass
        
        # Display results if available
        if 'last_results' in st.session_state and st.session_state.last_results:
            st.markdown("---")
            st.markdown("---")
            
            results = st.session_state.last_results
            query_image = st.session_state.last_query_image
            
            # Display comparison mode info
            if 'comparison_mode' in st.session_state:
                mode_icon = "🗂️" if st.session_state.comparison_mode == "cache" else "💾"
                st.info(f"{mode_icon} **Comparison Source:** {st.session_state.get('comparison_source', 'Unknown')}")
            
            st.success(f"✅ Found {len(results)} matches!")
            
            # Best match (highlighted)
            st.header("🏆 Best Match")
            best = results[0]
            
            col1, col2, col3 = st.columns([1, 1, 2])
            
            with col1:
                st.subheader("Query")
                st.image(query_image, use_container_width=True)
            
            with col2:
                st.subheader("Match")
                
                # Get the actual image path
                if st.session_state.get('comparison_mode') == "cache" and 'cache_path_map' in st.session_state:
                    # Use full path from manifest
                    best_image_path = st.session_state.cache_path_map.get(best.filename, None)
                    if best_image_path is None:
                        # Fallback to gallery_dir + filename
                        best_image_path = os.path.join(gallery_dir, best.filename)
                else:
                    # Use gallery_dir + filename for loaded gallery mode
                    best_image_path = os.path.join(gallery_dir, best.filename)
                
                if best_image_path and os.path.exists(best_image_path):
                    st.image(best_image_path, use_container_width=True)
                else:
                    st.error(f"Image not found: {best.filename}")
                    if best_image_path:
                        st.caption(f"Tried path: {best_image_path}")
            
            with col3:
                st.subheader("Match Details")
                st.metric("Filename", best.filename)
                st.metric("Similarity Score", format_similarity(best.similarity))
                st.metric(
                    "Match Status",
                    "✅ Same Person" if best.is_match else "❌ Different Person"
                )
            
            # Top K matches
            if len(results) > 1:
                st.markdown("---")
                st.header(f"📊 Top {len(results)} Matches")
                
                # Create columns for results
                cols_per_row = 5
                for i in range(0, len(results), cols_per_row):
                    cols = st.columns(cols_per_row)
                    for j, col in enumerate(cols):
                        idx = i + j
                        if idx >= len(results):
                            break
                        
                        result = results[idx]
                        with col:
                            # Get the actual image path
                            if st.session_state.get('comparison_mode') == "cache" and 'cache_path_map' in st.session_state:
                                # Use full path from manifest
                                img_path = st.session_state.cache_path_map.get(result.filename, None)
                                if img_path is None:
                                    # Fallback to gallery_dir + filename
                                    img_path = os.path.join(gallery_dir, result.filename)
                            else:
                                # Use gallery_dir + filename for loaded gallery mode
                                img_path = os.path.join(gallery_dir, result.filename)
                            
                            # Display image
                            if img_path and os.path.exists(img_path):
                                st.image(img_path, use_container_width=True)
                            else:
                                st.warning(f"Not found")
                            
                            # Display info
                            st.caption(f"**#{idx + 1}** {result.filename}")
                            st.caption(f"Similarity: **{result.similarity:.3f}**")
                            if result.is_match:
                                st.caption("✅ Match")
                            else:
                                st.caption("❌ No match")
            
            # Detailed results table
            st.markdown("---")
            st.subheader("📋 Detailed Results")
            
            # Create DataFrame for table display
            import pandas as pd
            
            df_data = []
            for idx, result in enumerate(results, 1):
                df_data.append({
                    "Rank": idx,
                    "Filename": result.filename,
                    "Similarity": f"{result.similarity:.4f}",
                    "Match": "✅ Yes" if result.is_match else "❌ No"
                })
            
            df = pd.DataFrame(df_data)
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            # Clear results button
            if st.button("🗑️ Clear Results", use_container_width=True):
                if 'last_results' in st.session_state:
                    del st.session_state.last_results
                if 'last_query_image' in st.session_state:
                    del st.session_state.last_query_image
                st.rerun()



# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    main()

# Compare Images - Two Comparison Modes

## Overview
The "Compare Images" feature now supports two distinct comparison modes, allowing flexible image matching based on your needs.

---

## 🗂️ Mode 1: Compare from Cache (encoded_result/)

### Description
Loads pre-encoded face embeddings directly from the `encoded_result/` folder on disk.

### When to Use
- **Quick comparisons** without loading the entire gallery into memory
- When you want to compare against **all previously encoded faces**
- **Independent operation** - doesn't require loading gallery in current session
- Ideal for **production use** where encodings are pre-computed

### Requirements
- The `encoded_result/` folder must exist with:
  - `manifest.json` file
  - `.npy` encoding files

### How It Works
1. Select "🗂️ Compare from Cache (encoded_result/)"
2. Upload query image
3. Click "Find Matches"
4. System loads encodings from disk on-demand
5. Compares query against cached encodings
6. Returns top matches

### Advantages
✅ No need to load gallery first  
✅ Faster startup (no encoding phase)  
✅ Uses disk-cached data  
✅ Memory efficient  
✅ Can compare against historical encodings  

### Disadvantages
⚠️ Requires pre-encoded results (must run "Load Gallery" with save option at least once)  
⚠️ Slightly slower during comparison (disk I/O)  

---

## 💾 Mode 2: Compare from Loaded Gallery (current session)

### Description
Uses the gallery that was loaded in the current Streamlit session.

### When to Use
- When you've **just loaded the gallery** in the current session
- For **testing and development** with frequently changing galleries
- When working with a **subset of images** (not all encoded yet)
- Need **in-memory performance** for multiple comparisons

### Requirements
- Gallery must be loaded first using "Load/Reload Gallery" tab
- Encoder and matcher must be initialized in current session

### How It Works
1. Load gallery first in "Load/Reload Gallery" tab
2. Select "💾 Compare from Loaded Gallery (current session)"
3. Upload query image
4. Click "Find Matches"
5. System uses in-memory gallery data
6. Compares query against loaded encodings
7. Returns top matches

### Advantages
✅ Fastest comparison (all data in memory)  
✅ Works with fresh/new images (just added to gallery)  
✅ No dependency on disk cache  
✅ Great for iterative testing  

### Disadvantages
⚠️ Requires loading gallery first (time-consuming initial step)  
⚠️ Memory intensive for large galleries  
⚠️ Session-specific (data lost when session ends)  

---

## Comparison Matrix

| Feature | Compare from Cache | Compare from Loaded Gallery |
|---------|-------------------|----------------------------|
| **Requires gallery load** | ❌ No | ✅ Yes |
| **Requires pre-encoded files** | ✅ Yes | ❌ No |
| **Comparison speed** | Medium (disk I/O) | Fast (in-memory) |
| **Memory usage** | Low | High |
| **Setup time** | Instant | Slow (encoding phase) |
| **Works with new images** | ❌ No (must re-encode) | ✅ Yes |
| **Best for** | Production, one-off queries | Development, multiple queries |

---

## Workflow Examples

### Example 1: First-time User
1. Go to "Load/Reload Gallery" tab
2. Enable "💾 Save encodings to disk"
3. Click "Load/Reload Gallery" (wait for completion)
4. Go to "Compare Images" tab
5. Choose either mode (both available now)

### Example 2: Returning User (Cache Available)
1. Go to "Compare Images" tab directly
2. Select "🗂️ Compare from Cache"
3. Upload image and compare
4. **No loading required!**

### Example 3: Testing New Gallery Images
1. Add new images to gallery folder
2. Go to "Load/Reload Gallery" tab
3. Click "Load/Reload Gallery" with save option
4. Go to "Compare Images" tab
5. Select "💾 Compare from Loaded Gallery" for immediate testing

---

## Technical Details

### Cache Mode Implementation
```python
# Loads from disk
cache_gallery = load_encodings_from_result_dir(ENCODED_RESULT_DIR)
cache_matcher = CNNMatcher(threshold=threshold)
results = cache_matcher.rank(query_embedding, cache_gallery, top_k=top_k)
```

### Loaded Gallery Mode Implementation
```python
# Uses session state
matcher = st.session_state.matcher
gallery = st.session_state.gallery
results = matcher.rank(query_embedding, gallery, top_k=top_k)
```

---

## Tips

💡 **For best performance:**
- Use **Cache mode** for single queries or infrequent comparisons
- Use **Loaded Gallery mode** when doing multiple comparisons in one session

💡 **For reliability:**
- Always keep `encoded_result/` folder up-to-date
- Re-encode when adding new faces to gallery

💡 **For flexibility:**
- You can switch between modes anytime
- Results show which mode was used

---

## Results Display

Both modes display:
- 🏆 Best match with similarity score
- 📊 Top K matches (configurable)
- 📋 Detailed results table
- 🗂️/💾 Icon showing which mode was used
- Number of faces compared against

---

## Error Handling

### Cache Mode Errors
- ❌ "Cache not available" → Run "Load Gallery" with save option first
- ❌ "Failed to load from cache" → Check `encoded_result/` folder integrity

### Loaded Gallery Mode Errors
- ❌ "Gallery not loaded" → Go to "Load/Reload Gallery" tab first
- ❌ "No matcher found" → Reload the gallery

---

## Files Involved

- **`app.py`** - Main Streamlit application with comparison logic
- **`encoded_result/`** - Folder containing cached encodings
  - `manifest.json` - Metadata about encoded files
  - `*.npy` - NumPy arrays with face embeddings
- **`sample/.cnn_encodings.npz`** - Session cache file

---

Last Updated: 2026-06-18

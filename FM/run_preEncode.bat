@echo off
echo ========================================
echo  Pre-Encode Gallery Images
echo ========================================
echo.
echo This will encode all images in the gallery
echo and save embeddings to cache for faster loading.
echo.
echo Default gallery: d:\Mini-Project\FM\sample
echo.
echo Press Ctrl+C to cancel, or
pause
echo.
echo Starting pre-encoding...
echo ========================================
echo.

python pre_encode_gallery.py --verify

echo.
echo ========================================
echo Done! You can now run the Streamlit app.
echo ========================================
pause

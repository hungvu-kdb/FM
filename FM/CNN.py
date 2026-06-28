"""PyTorch-based CNN implementation for facial recognition.

This module provides a PyTorch alternative to the dlib-based face_recognition
stack. It implements face detection and embedding generation using:

- MTCNN for face detection
- FaceNet (InceptionResnetV1) for generating 512-d embeddings
- Cosine similarity for face matching

Key differences from the original implementation:
- Uses PyTorch instead of dlib
- Generates 512-d embeddings instead of 128-d
- Uses cosine similarity instead of Euclidean distance
- Supports GPU acceleration when available
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict

import numpy as np
import torch
from PIL import Image


# The FaceNet model produces a 512-dimensional embedding
EMBEDDING_DIM = 512


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------
class ImageDecodeError(Exception):
    """Raised when image bytes cannot be decoded into a valid image."""
    pass


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class CNNCacheEntry:
    """A persisted gallery embedding with file metadata.
    
    Attributes:
        image_path: Absolute path to the gallery image.
        size_bytes: File size in bytes at encode time.
        mtime: File modification time at encode time.
        embedding: 512-d float embedding for the face.
    """
    image_path: str
    size_bytes: int
    mtime: float
    embedding: np.ndarray
    
    def __post_init__(self) -> None:
        if not self.image_path:
            raise ValueError("image_path must be non-empty")
        if self.size_bytes < 0:
            raise ValueError(f"size_bytes must be >= 0, got {self.size_bytes}")
        if self.mtime <= 0:
            raise ValueError(f"mtime must be > 0, got {self.mtime}")
        if not isinstance(self.embedding, np.ndarray):
            raise TypeError("embedding must be a numpy array")
        if self.embedding.shape != (EMBEDDING_DIM,):
            raise ValueError(
                f"embedding must have shape ({EMBEDDING_DIM},), got {self.embedding.shape}"
            )
    
    @property
    def signature(self) -> Tuple[int, float]:
        """Return the (size_bytes, mtime) file signature."""
        return (self.size_bytes, self.mtime)


@dataclass
class CNNGallerySet:
    """The in-memory set of gallery embeddings.
    
    Attributes:
        filenames: Filenames parallel to the rows of matrix.
        matrix: Embedding matrix of shape (N, 512).
    """
    filenames: List[str] = field(default_factory=list)
    matrix: np.ndarray = field(
        default_factory=lambda: np.empty((0, EMBEDDING_DIM))
    )
    
    def __post_init__(self) -> None:
        if len(set(self.filenames)) != len(self.filenames):
            raise ValueError("filenames must be unique")
        if self.matrix.shape != (len(self.filenames), EMBEDDING_DIM):
            raise ValueError(
                f"matrix must have shape ({len(self.filenames)}, {EMBEDDING_DIM}), "
                f"got {self.matrix.shape}"
            )
    
    def __len__(self) -> int:
        return len(self.filenames)


@dataclass(frozen=True)
class CNNMatchResult:
    """Result of comparing a query embedding against a gallery entry.
    
    Attributes:
        filename: Gallery filename of the match.
        similarity: Cosine similarity in [-1, 1] (higher = more similar).
        is_match: True if similarity >= threshold (same-person flag).
    """
    filename: str
    similarity: float
    is_match: bool
    
    def __post_init__(self) -> None:
        if not self.filename:
            raise ValueError("filename must be non-empty")
        if not (-1.0 <= self.similarity <= 1.0):
            raise ValueError(
                f"similarity must be in [-1, 1], got {self.similarity}"
            )


# ---------------------------------------------------------------------------
# CNN Encoder (PyTorch + FaceNet)
# ---------------------------------------------------------------------------
class CNNEncoder:
    """Face detection and embedding generation using PyTorch."""
    
    def __init__(
        self, 
        device: Optional[str] = None,
        min_face_size: int = 40,
        thresholds: Optional[List[float]] = None
    ) -> None:
        """Initialize the CNN encoder.
        
        Args:
            device: Device to run models on ('cuda', 'cpu', or None for auto).
            min_face_size: Minimum face size for MTCNN detector.
            thresholds: MTCNN detection thresholds [P, R, O stages].
        """
        if device is None:
            self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        else:
            self.device = torch.device(device)
        
        self.min_face_size = min_face_size
        self.thresholds = thresholds or [0.6, 0.7, 0.7]
        
        # Lazy initialization of models (imported when first needed)
        self._mtcnn = None
        self._facenet = None
    
    def _init_models(self) -> None:
        """Lazy initialization of MTCNN and FaceNet models."""
        if self._mtcnn is not None:
            return
        
        try:
            from facenet_pytorch import MTCNN, InceptionResnetV1
        except ImportError:
            raise ImportError(
                "facenet-pytorch is required for CNNEncoder. "
                "Install it with: pip install facenet-pytorch"
            )
        
        # Initialize MTCNN for face detection
        self._mtcnn = MTCNN(
            image_size=160,
            margin=0,
            min_face_size=self.min_face_size,
            thresholds=self.thresholds,
            factor=0.709,
            post_process=True,
            device=self.device,
            keep_all=True  # Detect all faces, not just the largest
        )
        
        # Initialize FaceNet for embedding generation
        self._facenet = InceptionResnetV1(pretrained='vggface2').eval().to(self.device)
    
    def _load_image(self, image_path: str) -> Image.Image:
        """Load an image from disk.
        
        Args:
            image_path: Path to the image file.
            
        Returns:
            PIL Image in RGB format.
            
        Raises:
            ImageDecodeError: If the image cannot be loaded.
        """
        try:
            img = Image.open(image_path).convert('RGB')
            return img
        except (IOError, OSError) as e:
            raise ImageDecodeError(
                f"Could not decode image from {image_path!r}: {e}"
            ) from e
    
    def _detect_faces(self, image: Image.Image) -> Optional[torch.Tensor]:
        """Detect faces and return aligned face tensors.
        
        Args:
            image: PIL Image in RGB format.
            
        Returns:
            Tensor of shape (N, 3, 160, 160) with N detected faces,
            or None if no faces detected.
        """
        self._init_models()
        
        # MTCNN returns aligned face tensors ready for FaceNet
        faces = self._mtcnn(image)
        
        if faces is None:
            return None
        
        # Ensure we have a batch dimension
        if faces.dim() == 3:
            faces = faces.unsqueeze(0)
        
        return faces
    
    def _generate_embeddings(self, faces: torch.Tensor) -> List[np.ndarray]:
        """Generate embeddings for detected faces.
        
        Args:
            faces: Tensor of shape (N, 3, 160, 160).
            
        Returns:
            List of N embeddings, each of shape (512,).
        """
        self._init_models()
        
        with torch.no_grad():
            faces = faces.to(self.device)
            embeddings = self._facenet(faces)
            
            # Normalize embeddings for cosine similarity
            embeddings = embeddings / embeddings.norm(dim=1, keepdim=True)
            
            # Convert to numpy
            embeddings_np = embeddings.cpu().numpy()
        
        return [emb for emb in embeddings_np]
    
    def encode_image(self, image_path: str) -> Optional[np.ndarray]:
        """Encode the most prominent face in an image.
        
        Args:
            image_path: Path to the image file.
            
        Returns:
            A (512,) numpy array for the most prominent face,
            or None if no face is detected.
            
        Raises:
            ImageDecodeError: If the image cannot be decoded.
        """
        image = self._load_image(image_path)
        faces = self._detect_faces(image)
        
        if faces is None or len(faces) == 0:
            return None
        
        embeddings = self._generate_embeddings(faces)
        return embeddings[0]  # Return first (most prominent) face
    
    def encode_all_faces(self, image_path: str) -> List[np.ndarray]:
        """Encode all detected faces in an image.
        
        Args:
            image_path: Path to the image file.
            
        Returns:
            List of (512,) numpy arrays, one per detected face.
            Empty list if no faces detected.
            
        Raises:
            ImageDecodeError: If the image cannot be decoded.
        """
        image = self._load_image(image_path)
        faces = self._detect_faces(image)
        
        if faces is None or len(faces) == 0:
            return []
        
        return self._generate_embeddings(faces)


# ---------------------------------------------------------------------------
# CNN Matcher (Cosine Similarity)
# ---------------------------------------------------------------------------
class CNNMatcher:
    """Compare query embeddings against gallery using cosine similarity."""
    
    def __init__(self, threshold: float = 0.7) -> None:
        """Initialize matcher.
        
        Args:
            threshold: Minimum cosine similarity to be considered the same person.
                      Range: [-1, 1], typical values: 0.6-0.8
        """
        self.threshold = threshold
    
    @staticmethod
    def _cosine_similarities(
        gallery_matrix: np.ndarray, 
        query: np.ndarray
    ) -> np.ndarray:
        """Compute cosine similarity between query and each gallery entry.
        
        Args:
            gallery_matrix: Shape (N, 512) of normalized embeddings.
            query: Shape (512,) normalized embedding.
            
        Returns:
            Array of shape (N,) with similarity scores in [-1, 1].
        """
        # Ensure query is normalized
        query = query / np.linalg.norm(query)
        
        # Cosine similarity = dot product for normalized vectors
        similarities = gallery_matrix @ query
        
        return similarities
    
    def find_best_match(
        self, 
        query: np.ndarray, 
        gallery: CNNGallerySet
    ) -> Optional[CNNMatchResult]:
        """Find the closest gallery entry.
        
        Args:
            query: Query embedding of shape (512,).
            gallery: Gallery set to search.
            
        Returns:
            Best match result, or None if gallery is empty.
        """
        if len(gallery) == 0:
            return None
        
        results = self.rank(query, gallery, top_k=1)
        return results[0] if results else None
    
    def rank(
        self, 
        query: np.ndarray, 
        gallery: CNNGallerySet, 
        top_k: int = 5
    ) -> List[CNNMatchResult]:
        """Rank gallery entries by similarity to query.
        
        Args:
            query: Query embedding of shape (512,).
            gallery: Gallery set to search.
            top_k: Number of top matches to return.
            
        Returns:
            List of up to top_k matches, sorted by descending similarity.
        """
        n = len(gallery)
        if n == 0 or top_k <= 0:
            return []
        
        similarities = self._cosine_similarities(gallery.matrix, query)
        
        # Clamp similarities to [-1, 1] to handle floating-point precision issues
        similarities = np.clip(similarities, -1.0, 1.0)
        
        # Sort descending (highest similarity first)
        order = np.argsort(-similarities)
        
        results: List[CNNMatchResult] = []
        for i in order[:top_k]:
            sim = float(similarities[i])
            results.append(
                CNNMatchResult(
                    filename=gallery.filenames[i],
                    similarity=sim,
                    is_match=(sim >= self.threshold)
                )
            )
        
        return results


# ---------------------------------------------------------------------------
# CNN Cache (same structure as original)
# ---------------------------------------------------------------------------
class CNNCache:
    """Persist and retrieve CNN-generated embeddings."""
    
    def __init__(self, cache_path: str) -> None:
        self.cache_path = cache_path
    
    @staticmethod
    def file_signature(image_path: str) -> Tuple[int, float]:
        """Return (size_bytes, mtime) for the image file."""
        stat = os.stat(image_path)
        return (stat.st_size, stat.st_mtime)
    
    def save(self, entries: Dict[str, CNNCacheEntry]) -> None:
        """Save cache entries to disk using numpy format."""
        import tempfile
        
        paths = list(entries.keys())
        if paths:
            sizes = np.array([entries[p].size_bytes for p in paths], dtype=np.int64)
            mtimes = np.array([entries[p].mtime for p in paths], dtype=np.float64)
            matrix = np.stack([entries[p].embedding for p in paths])
        else:
            sizes = np.empty((0,), dtype=np.int64)
            mtimes = np.empty((0,), dtype=np.float64)
            matrix = np.empty((0, EMBEDDING_DIM), dtype=np.float64)
        
        image_paths = np.array(paths, dtype=object)
        
        cache_dir = os.path.dirname(os.path.abspath(self.cache_path))
        os.makedirs(cache_dir, exist_ok=True)
        
        # Atomic write via temp file
        fd, tmp_path = tempfile.mkstemp(suffix=".tmp", dir=cache_dir)
        try:
            with os.fdopen(fd, "wb") as fh:
                np.savez(
                    fh,
                    image_paths=image_paths,
                    sizes=sizes,
                    mtimes=mtimes,
                    matrix=matrix
                )
            os.replace(tmp_path, self.cache_path)
        except BaseException:
            try:
                os.remove(tmp_path)
            except OSError:
                pass
            raise
    
    def load(self) -> Dict[str, CNNCacheEntry]:
        """Load cache from disk, returning empty dict if missing/corrupt."""
        if not os.path.exists(self.cache_path):
            return {}
        
        try:
            import zipfile
            
            with np.load(self.cache_path, allow_pickle=True) as data:
                image_paths = data["image_paths"]
                sizes = data["sizes"]
                mtimes = data["mtimes"]
                matrix = data["matrix"]
                
                n = len(image_paths)
                if not (len(sizes) == len(mtimes) == matrix.shape[0] == n):
                    return {}
                
                entries: Dict[str, CNNCacheEntry] = {}
                for i in range(n):
                    path = str(image_paths[i])
                    embedding = matrix[i].astype(np.float64)
                    entries[path] = CNNCacheEntry(
                        image_path=path,
                        size_bytes=int(sizes[i]),
                        mtime=float(mtimes[i]),
                        embedding=embedding
                    )
                return entries
        except Exception:
            # Any error -> treat as empty cache
            return {}


# ---------------------------------------------------------------------------
# CNN Gallery Manager
# ---------------------------------------------------------------------------
class CNNGalleryManager:
    """Build and maintain the gallery of CNN embeddings."""
    
    def __init__(self, encoder: CNNEncoder, cache: CNNCache) -> None:
        self.encoder = encoder
        self.cache = cache
    
    def _list_png_files(self, gallery_dir: str) -> List[str]:
        """Return sorted full paths of *.png files (case-insensitive)."""
        paths: List[str] = []
        with os.scandir(gallery_dir) as it:
            for entry in it:
                if entry.is_file() and entry.name.lower().endswith(".png"):
                    paths.append(os.path.join(gallery_dir, entry.name))
        paths.sort()
        return paths
    
    def load_gallery(self, gallery_dir: str) -> CNNGallerySet:
        """Load gallery, reusing cache when possible.
        
        Args:
            gallery_dir: Directory containing *.png gallery images.
            
        Returns:
            CNNGallerySet with embeddings for all encodable faces.
        """
        cached = self.cache.load()
        current_paths = self._list_png_files(gallery_dir)
        entries: Dict[str, CNNCacheEntry] = {}
        
        for path in current_paths:
            size, mtime = self.cache.file_signature(path)
            sig = (size, mtime)
            
            if path in cached and cached[path].signature == sig:
                # Reuse cached embedding
                entries[path] = cached[path]
            else:
                # Encode new/changed file
                embedding = self.encoder.encode_image(path)
                if embedding is not None:
                    entries[path] = CNNCacheEntry(
                        image_path=path,
                        size_bytes=size,
                        mtime=mtime,
                        embedding=embedding
                    )
                else:
                    # No face detected - skip
                    print(f"Warning: No face detected in {path}")
        
        # Save reconciled cache
        self.cache.save(entries)
        
        return self._build_gallery_set(entries)
    
    @staticmethod
    def _build_gallery_set(entries: Dict[str, CNNCacheEntry]) -> CNNGallerySet:
        """Build CNNGallerySet from cache entries."""
        paths = list(entries.keys())
        filenames = [os.path.basename(p) for p in paths]
        
        if paths:
            matrix = np.stack([entries[p].embedding for p in paths])
        else:
            matrix = np.empty((0, EMBEDDING_DIM), dtype=np.float64)
        
        return CNNGallerySet(filenames=filenames, matrix=matrix)


# ---------------------------------------------------------------------------
# Main CLI Interface
# ---------------------------------------------------------------------------
def main() -> int:
    """Simple CLI for testing the CNN implementation."""
    import argparse
    import sys
    
    parser = argparse.ArgumentParser(
        description="PyTorch CNN-based facial recognition"
    )
    parser.add_argument("query", help="Path to query image")
    parser.add_argument(
        "--gallery",
        default=r"d:\Mini-Project\FM\sample",
        help="Gallery directory (default: %(default)s)"
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.7,
        help="Similarity threshold (default: %(default)s)"
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        dest="top_k",
        help="Number of matches to show (default: %(default)s)"
    )
    parser.add_argument(
        "--device",
        choices=["cuda", "cpu", "auto"],
        default="auto",
        help="Device to use (default: %(default)s)"
    )
    
    args = parser.parse_args()
    
    # Validate paths
    if not os.path.isfile(args.query):
        print(f"Error: Query image not found: {args.query}", file=sys.stderr)
        return 1
    if not os.path.isdir(args.gallery):
        print(f"Error: Gallery directory not found: {args.gallery}", file=sys.stderr)
        return 1
    
    device = None if args.device == "auto" else args.device
    
    # Initialize pipeline
    encoder = CNNEncoder(device=device)
    cache_path = os.path.join(args.gallery, ".cnn_encodings.npz")
    cache = CNNCache(cache_path)
    
    print("Loading gallery...")
    gallery_manager = CNNGalleryManager(encoder, cache)
    gallery = gallery_manager.load_gallery(args.gallery)
    
    if len(gallery) == 0:
        print("Error: No encodable faces in gallery", file=sys.stderr)
        return 3
    
    print(f"Gallery loaded: {len(gallery)} faces")
    print(f"Encoding query image...")
    
    # Encode query
    try:
        query_embedding = encoder.encode_image(args.query)
    except ImageDecodeError:
        query_embedding = None
    
    if query_embedding is None:
        print("Error: No face detected in query image", file=sys.stderr)
        return 2
    
    # Match and display results
    matcher = CNNMatcher(threshold=args.threshold)
    results = matcher.rank(query_embedding, gallery, top_k=args.top_k)
    
    if results:
        print(f"\nBest match: {results[0].filename}")
        print(f"  Similarity: {results[0].similarity:.3f}")
        print(f"  Same person: {'yes' if results[0].is_match else 'no'}")
        
        if len(results) > 1:
            print(f"\nTop {len(results)} matches:")
            for i, result in enumerate(results, 1):
                same = "yes" if result.is_match else "no"
                print(
                    f"  #{i}: {result.filename} "
                    f"(similarity: {result.similarity:.3f}, same-person: {same})"
                )
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())

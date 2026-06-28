# Requirements Document

## Introduction

This document specifies the requirements for a 1-to-many facial similarity matching command-line tool. Given a gallery directory of PNG portrait images, the tool encodes each gallery face into a 128-dimensional embedding (cached to disk for reuse), encodes a single query image, compares the query embedding against every gallery embedding using Euclidean distance, and reports the gallery filename whose face is most similar to the query face. The requirements below are derived from the approved design document and capture the behavior of the Encoder, EncodingCache, GalleryManager, Matcher, and CLI components.

## Glossary

- **System**: The facial recognition CLI tool as a whole.
- **Encoder**: The component that detects a face in an image and produces a 128-dimensional embedding vector.
- **Embedding**: A fixed-length 128-dimensional float vector representing a detected face.
- **EncodingCache**: The component that persists and retrieves gallery embeddings on disk.
- **GalleryManager**: The component that discovers gallery images, reconciles them with the cache, and produces the in-memory encoding set.
- **Matcher**: The component that computes distances between a query embedding and gallery embeddings and ranks results.
- **CLI**: The command-line entry point that parses arguments, wires components, prints results, and returns exit codes.
- **Gallery**: The directory of PNG portrait images to search against.
- **Query_Image**: The single input image whose face is matched against the gallery.
- **Cache_Entry**: A stored record holding an image path, file signature (size and modification time), and embedding.
- **File_Signature**: The tuple of file size in bytes and modification time used to detect stale cache entries.
- **Match_Result**: A record holding a matched filename, Euclidean distance, normalized similarity score, and a same-person flag.
- **Distance**: The Euclidean (L2) distance between two embeddings; lower means more similar.
- **Similarity**: A normalized score in the range (0, 1] derived from distance; higher means more similar.
- **Threshold**: The maximum distance at which two faces are considered the same person.

## Requirements

### Requirement 1: Encode a face into an embedding

**User Story:** As a user, I want each image's face converted into a numerical embedding, so that faces can be compared mathematically.

#### Acceptance Criteria

1. WHEN an image containing at least one detectable face is provided to the Encoder, THE Encoder SHALL return a 128-dimensional float embedding for the most prominent face.
2. IF face detection runs successfully but finds no faces in the provided image, THEN THE Encoder SHALL return None without raising an exception.
3. IF the image bytes cannot be decoded, THEN THE Encoder SHALL signal a decoding failure without crashing the System.
4. WHEN an image containing multiple faces is provided to the Encoder, THE Encoder SHALL return one 128-dimensional embedding for every detected face.
5. WHERE the detector model option is set to "hog" or "cnn", THE Encoder SHALL use the selected model to locate faces.

### Requirement 2: Persist and reuse gallery encodings

**User Story:** As a user, I want gallery encodings cached on disk, so that repeated queries do not re-encode the entire gallery.

#### Acceptance Criteria

1. WHEN the GalleryManager produces gallery encodings, THE EncodingCache SHALL persist those encodings to disk.
2. WHEN the EncodingCache loads a cache file, THE EncodingCache SHALL return the stored Cache_Entry records.
3. IF the cache file is missing or corrupt, including when it is both missing and corrupt, THEN THE EncodingCache SHALL return an empty result so the System rebuilds the cache.
4. WHEN comparing a Cache_Entry to its source file, THE EncodingCache SHALL treat the entry as stale if the current File_Signature differs from the stored File_Signature.
5. WHEN saving the cache, THE EncodingCache SHALL write the file atomically.
6. THE EncodingCache SHALL compute a File_Signature as the tuple of current file size in bytes and modification time.

### Requirement 3: Build and reconcile the gallery encoding set

**User Story:** As a user, I want the gallery to reflect the current image files, so that matching uses up-to-date encodings.

#### Acceptance Criteria

1. WHEN the GalleryManager loads a gallery directory, THE GalleryManager SHALL enumerate all PNG files in the directory using case-insensitive matching.
2. WHILE reconciling the gallery against the cache, THE GalleryManager SHALL reuse a cached encoding when the file signature is unchanged.
3. WHILE reconciling the gallery against the cache, THE GalleryManager SHALL re-encode a file when its File_Signature differs from the cached signature.
4. WHEN a gallery image has no detectable face, THE GalleryManager SHALL skip that image and log a warning.
5. WHEN the GalleryManager finishes reconciliation, THE GalleryManager SHALL persist a cache that excludes files no longer present in the gallery directory.
6. THE GalleryManager SHALL return a gallery encoding set whose embedding matrix has one row per included filename and no duplicate filenames.

### Requirement 4: Match a query against the gallery

**User Story:** As a user, I want the tool to find the gallery face most similar to my query, so that I can identify the closest match.

#### Acceptance Criteria

1. WHEN a query embedding is matched against a non-empty gallery, THE Matcher SHALL return the gallery entry whose Distance to the query is the minimum over the gallery.
2. WHEN the Matcher ranks gallery entries, THE Matcher SHALL return the entries sorted by non-decreasing Distance.
3. WHEN the Matcher ranks gallery entries with a top_k limit, THE Matcher SHALL return at most min(top_k, gallery size) entries.
4. IF the gallery is empty, THEN THE Matcher SHALL return None.
5. THE Matcher SHALL compute the Distance between two embeddings as their Euclidean distance, which SHALL be non-negative and symmetric.
6. THE Matcher SHALL convert a Distance to a Similarity in the range (0, 1] that is non-increasing as Distance increases, yielding 1.0 when Distance is 0.
7. WHEN producing a Match_Result, THE Matcher SHALL set the same-person flag to true exactly when the Distance is less than or equal to the Threshold.

### Requirement 5: Command-line orchestration and output

**User Story:** As a user, I want to run the tool from the command line, so that I can get the best match for a query image.

#### Acceptance Criteria

1. WHEN the CLI is invoked with a query path and gallery directory, THE CLI SHALL run the pipeline and print the best-match filename with its similarity and distance.
2. WHERE a top_k argument is supplied, THE CLI SHALL print the top_k ranked matches, printing no matches when top_k is 0.
3. WHERE a threshold, model, or gallery argument is supplied, THE CLI SHALL apply the supplied value to the pipeline.
4. IF the query file or gallery directory does not exist, THEN THE CLI SHALL print a specific error and return exit code 1.
5. IF no face is detected in the query image, THEN THE CLI SHALL print "No face detected in query image" and return exit code 2.
6. IF no encodable faces are found in the gallery, THEN THE CLI SHALL print "No encodable faces found in gallery" and return exit code 3.

### Requirement 6: Cache-consistent results

**User Story:** As a user, I want results to be the same whether or not a cache was reused, so that caching is purely a performance optimization.

#### Acceptance Criteria

1. WHEN an unchanged gallery is matched against a query, THE System SHALL produce identical Match_Results whether the gallery encodings were freshly built or reused from cache.

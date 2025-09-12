# Mock implementations for face_recognition functions

def load_image_file(file_path):
    """Mock implementation of face_recognition.load_image_file"""
    print(f"MOCK: Loading image from {file_path}")
    # Return a dummy image (a simple black image as a numpy array)
    import numpy as np
    return np.zeros((100, 100, 3), dtype=np.uint8)

def face_encodings(image, known_face_locations=None):
    """Mock implementation of face_recognition.face_encodings"""
    print("MOCK: Generating face encodings")
    import numpy as np
    # Return a dummy encoding (128-dimensional vector of zeros)
    return [np.zeros(128)]

def face_locations(image):
    """Mock implementation of face_recognition.face_locations"""
    print("MOCK: Finding face locations")
    # Return a dummy face location (top, right, bottom, left)
    return [(0, 100, 100, 0)]

def compare_faces(known_face_encodings, face_encoding_to_check, tolerance=0.6):
    """Mock implementation of face_recognition.compare_faces"""
    print("MOCK: Comparing faces")
    # Always return False for mock
    return [False]
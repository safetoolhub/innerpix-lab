from utils.file_utils import detect_file_source

filename = "82DB60A3-002F-4FAE-80FC-96082431D247_001.jpg"
source = detect_file_source(filename)
print(f"Filename: {filename}")
print(f"Detected Source: {source}")

assert source == "WhatsApp", f"Expected WhatsApp, got {source}"
print("Test PASSED")

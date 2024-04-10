import os
import shutil

def clear_except_allowed_folder(path, allowedFolders):
    """
    Clears everything in the specified path except for the allowedFolder.
    
    :param path: Path to the directory to clear.
    :param allowedFolder: The name of the folder to keep.
    """
    # Make sure the path is a directory
    if not os.path.isdir(path):
        print(f"The provided path {path} is not a directory.")
        return
    current_file_dir = os.path.dirname(os.path.abspath(__file__))

    # Iterate through items in the directory
    for item in os.listdir(path):
        item_path = os.path.join(path, item)
        # Check if the current item is the allowedFolder
        if item in allowedFolders or item_path == current_file_dir:
            continue  # Skip the allowedFolder
        
        # If item is a directory, remove it and its contents
        if os.path.isdir(item_path):
            shutil.rmtree(item_path)
            print(f"Removed directory: {item_path}")
        # Don't remove file
        # else:
        #     os.remove(item_path)
        #     print(f"Removed file: {item_path}")
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def list_files_in_directory(directory_path, output_file_path="file_list.txt"):
    """
    Lists all files in a given directory and saves the list to a specified file.

    Args:
        directory_path (str): The path to the directory to list files from.
        output_file_path (str, optional): The path to the file where the list of files will be saved.
                                           Defaults to "file_list.txt".

    Returns:
        bool: True if the operation was successful, False otherwise.

    Raises:
        TypeError: if directory_path or output_file_path is not a string.
        FileNotFoundError: if the provided directory does not exist.
        OSError: if there is an error accessing the directory or writing to the file.
    """

    # Input validation
    if not isinstance(directory_path, str):
        raise TypeError("directory_path must be a string.")
    if not isinstance(output_file_path, str):
        raise TypeError("output_file_path must be a string.")

    # Check if the directory exists
    if not os.path.isdir(directory_path):
        raise FileNotFoundError(f"Directory not found: {directory_path}")

    try:
        # List files in the directory
        files = os.listdir(directory_path)

        # Filter out directories, keeping only files. Use list comprehension for efficiency.
        file_paths = [f for f in files if os.path.isfile(os.path.join(directory_path, f))]

        # Save the list of files to the output file
        with open(output_file_path, "w") as outfile:
            for file_name in file_paths:
                outfile.write(file_name + "\n")  # Write each file name on a new line

        logging.info(f"Successfully listed files from '{directory_path}' and saved to '{output_file_path}'")
        return True

    except OSError as e:
        logging.error(f"An error occurred: {e}")
        return False


if __name__ == "__main__":
    # Example Usage:
    try:
        # Replace 'example_directory' with an actual directory path
        directory_to_list = "example_directory"

        # Create the example directory if it doesn't exist
        if not os.path.exists(directory_to_list):
            os.makedirs(directory_to_list)
            # Create some dummy files within the directory
            with open(os.path.join(directory_to_list, "file1.txt"), "w") as f:
                f.write("This is file 1.")
            with open(os.path.join(directory_to_list, "file2.txt"), "w") as f:
                f.write("This is file 2.")
            with open(os.path.join(directory_to_list, "file3.log"), "w") as f:
                f.write("This is a log file.")


        output_file = "files.txt"  # Specify the output file name

        success = list_files_in_directory(directory_to_list, output_file)

        if success:
            print(f"File list saved to {output_file}")
        else:
            print("Failed to list files.")

    except FileNotFoundError as e:
        print(f"Error: {e}")
    except TypeError as e:
        print(f"Error: {e}")
    except OSError as e:
        print(f"Error: {e}")
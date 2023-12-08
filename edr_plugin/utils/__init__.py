import os
import re
from uuid import uuid4


def download_response_file(response, download_dir, download_filename=None, chunk_size=1024**2):
    """Download and write content from the response object."""
    if not download_filename:
        try:
            content_disposition = response.headers["content-disposition"]
            download_filename = re.findall("filename=(.+)", content_disposition)[0].strip('"')
        except KeyError:
            collection_name = re.findall("collections/(.+?)/", response.url)[0]
            download_filename = f"{collection_name}_{uuid4()}.json"
    download_filepath = os.path.join(download_dir, download_filename)
    with open(download_filepath, "wb") as f:
        for chunk in response.iter_content(chunk_size=chunk_size):
            if chunk:
                f.write(chunk)
    return download_filepath


def is_dir_writable(working_dir):
    """Try to write an empty text file into given location to check if location is writable."""
    test_filename = f"{uuid4()}.txt"
    test_file_path = os.path.join(working_dir, test_filename)
    try:
        with open(test_file_path, "w") as test_file:
            test_file.write("")
        os.remove(test_file_path)
    except (PermissionError, OSError):
        return False
    return True

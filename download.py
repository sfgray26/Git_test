import os
import requests
from typing import Optional, Dict, Any, List

class ThirdPartyAPIFacade:
    def __init__(self):
        self.base_url = "http://localhost:5000"  # Replace with your Flask API base URL
        self._proxies = {}  # Define proxies if needed, or leave empty

    def download_file(
        self,
        location_id: int,
        file_id: str,
        requested_by: str,
        save_path: str,
    ) -> Dict[str, Any]:
        """
        Download a file from the Flask API using a two-step process.

        Args:
            location_id (int): The ID of the location.
            file_id (str): The ID of the file to download.
            requested_by (str): The user requesting the download.
            save_path (str): The local path where the file should be saved.

        Returns:
            Dict[str, Any]: A dictionary with the status and details of the download.
        """
        # Validate inputs
        try:
            validate_location_id(location_id)
            print(f"Validating file download requested by: {requested_by}")
            validate_user(requested_by)
            if not file_id or not isinstance(file_id, str):
                raise ValueError("Invalid file ID")
        except Exception as e:
            print(f"Validation failed: {str(e)}")
            return {"status": "error", "error": f"Validation failed: {str(e)}", "locationId": location_id}

        # Ensure the save directory exists
        save_dir = os.path.dirname(save_path)
        if save_dir and not os.path.exists(save_dir):
            os.makedirs(save_dir)

        # Fetch access token
        try:
            token = self.get_access_token()
            print(f"Token in download_file: {repr(token)} (type: {type(token)})")
        except Exception as e:
            print(f"Failed to get access token: {str(e)}")
            return {"status": "error", "error": f"Authentication failed: {str(e)}", "locationId": location_id}

        # Prepare headers with the token
        headers = {"Authorization": f"Bearer {token}"}

        # Step 1: Request the download URL
        initial_download_url = f"{self.base_url}/v1/los/file/request-for-download/locationId/{location_id}/fileId/{file_id}/requestedBy/{requested_by}"
        initial_data = {
            "locationId": str(location_id),
            "fileId": file_id,
            "requestedBy": requested_by,
        }

        try:
            print(f"Requesting download URL from: {initial_download_url}")
            print(f"Initial data: {initial_data}")
            initial_response = requests.post(
                initial_download_url,
                json=initial_data,  # Sending as JSON; adjust to multipart/form-data if needed
                headers=headers,
                verify=False,
                proxies=self._proxies,
                timeout=10
            )

            # Debug the response object
            print(f"Initial response type: {type(initial_response)}")
            print(f"Initial response status: {initial_response.status_code}")
            print(f"Initial response content: {initial_response.text}")

            if initial_response.status_code != 200:
                return {
                    "status": "error",
                    "error": f"Failed to get download URL: status code {initial_response.status_code}, response: {initial_response.text}",
                    "locationId": location_id,
                }

            # Parse the response as JSON
            try:
                data = initial_response.json()
                if not isinstance(data, dict):
                    return {
                        "status": "error",
                        "error": f"Response data is not a dictionary: {data}",
                        "locationId": location_id,
                    }
                if "download_url" not in data:
                    return {
                        "status": "error",
                        "error": "No download_url in initial response",
                        "locationId": location_id,
                    }
                download_url = data["download_url"]
            except ValueError:
                return {
                    "status": "error",
                    "error": f"Initial response is not JSON-parsable: {initial_response.text}",
                    "locationId": location_id,
                }
        except Exception as e:
            print(f"Failed to parse initial response: {str(e)}")
            return {
                "status": "error",
                "error": f"Failed to parse initial response: {str(e)}",
                "locationId": location_id,
            }

        # Step 2: Download the file using the download URL
        try:
            print(f"Downloading file from: {download_url}")
            download_response = requests.get(
                download_url,
                headers=headers,
                verify=False,
                proxies=self._proxies,
                timeout=10,
                stream=True  # Use streaming to handle large files efficiently
            )

            print(f"Download response status: {download_response.status_code}")
            if download_response.status_code != 200:
                return {
                    "status": "error",
                    "error": f"File download failed: status code {download_response.status_code}",
                    "locationId": location_id,
                }

            # Save the file to the specified path
            with open(save_path, "wb") as f:
                for chunk in download_response.iter_content(chunk_size=8192):
                    if chunk:  # Filter out keep-alive chunks
                        f.write(chunk)

            print(f"File downloaded and saved to: {save_path}")
            return {
                "status": "success",
                "locationId": location_id,
                "fileId": file_id,
                "savePath": save_path,
                "message": "File downloaded successfully",
            }

        except Exception as e:
            print(f"Download failed: {str(e)}")
            return {
                "status": "error",
                "error": f"File download failed: {str(e)}",
                "locationId": location_id,
            }

    # Existing methods (for completeness)
    def stringify(self, data: List[Dict[str, Any]]) -> List[str]:
        """
        Convert a list of dictionaries to a list of strings.
        This is a placeholder for the actual implementation.
        """
        return [str(item) for item in data]

    def get_access_token(self):
        """
        Placeholder for fetching an access token. Replace with your actual implementation.
        """
        return "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."  # Replace with the token from Postman

    def validate_location_id(self, location_id: int):
        """
        Placeholder for location ID validation.
        """
        if not isinstance(location_id, int) or location_id <= 0:
            raise ValueError("Invalid location ID")

    def validate_user(self, user: str):
        """
        Placeholder for user validation.
        """
        if not user or not isinstance(user, str):
            raise ValueError("Invalid user")
​​​​​​​​​​​​​​​​​​​​​​​​​​​​​​​​​​​​​​​​​​​​​​​​​​
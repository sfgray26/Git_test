import os
from typing import Optional, Dict, Any, List
import pytest
import requests
from pathlib import Path
import time

# Assuming these are in your project structure
from config.settings import settings
from models.api_response import APIResponse
from utils.validators import validate_request, validate_user, validate_location_id
from utils.rate_limiter import RateLimiter
from utils.stringifier import stringify
from models.service_request import ServiceRequest

class ThirdPartyAPIFacade:
    def __init__(self):
        self.session = requests.Session()
        self.token = None
        self.token_expiry = 0
        self.proxies = {
            'http': 'http://proxy.abc.com:8080',
            'https': 'http://proxy.abc.com:8080'
        }
        self.session.proxies = self.proxies
        self.base_url = settings.API_BASE_URL
        self.rate_limiter = RateLimiter(limit=180, period=60)
        print(f"Initialized with base_url: {self.base_url}")
        print(f"Client ID: {settings.CLIENT_ID}")
        print(f"Client Secret: {settings.CLIENT_SECRET[:5]}... (hidden for security)")

    def _make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Utility method to make HTTP requests with proper headers and token"""
        headers = kwargs.get('headers', {}) or {}
        print(f"Headers in _make_request: {headers} (type: {type(headers)})")
        data = kwargs.get('data', {})
        print(f"Data in _make_request: {data} (type: {type(data)})")
        print(f"Checking if token is needed: 'Authorization' in headers: {'Authorization' in headers}, 'grant_type' in data: {'grant_type' in data}")
        if 'Authorization' not in headers and 'grant_type' not in data:
            print("Fetching token for request")
            token = self.get_access_token()
            headers['Authorization'] = f'Bearer {token}'
        else:
            print("Skipping token fetch: either Authorization header present or this is a token request")
        full_url = endpoint if endpoint.startswith('http') else f"{self.base_url}{endpoint}"
        print(f"Making {method} request to: {full_url}")
        print(f"Request headers: {headers}")
        print(f"Request kwargs: {kwargs}")
        try:
            response = self.session.request(method, full_url, headers=headers, **kwargs)
            print(f"Response status: {response.status_code}")
            print(f"Response content: {response.content.decode('utf-8', errors='replace')[:200]}")
            response.raise_for_status()
            return response
        except requests.RequestException as e:
            print(f"Request failed: {str(e)}")
            raise

    def _get_access_token(self) -> str:
        if not self.token or time.time() > self.token_expiry:
            payload = {
                'grant_type': 'client_credentials',
                'client_id': settings.CLIENT_ID,
                'client_secret': settings.CLIENT_SECRET,
                'scope': '*'
            }
            endpoint = "/v1/los/oauth/token"
            print(f"Fetching new token from {endpoint}")
            # Ensure the correct Content-Type for token requests
            headers = {'Content-Type': 'application/x-www-form-urlencoded'}
            try:
                response = self._make_request('POST', endpoint, data=payload, headers=headers)
                response_json = response.json()
                print(f"Token endpoint response: {response_json}")
                # Check if 'data' key exists
                if 'data' not in response_json:
                    # If 'data' key is missing, try accessing token directly
                    if 'access_token' not in response_json:
                        raise ValueError("Token endpoint response missing 'access_token' key")
                    if 'expires_in' not in response_json:
                        raise ValueError("Token endpoint response missing 'expires_in' key")
                    self.token = response_json['access_token']
                    self.token_expiry = time.time() + response_json['expires_in']
                else:
                    token_data = response_json['data']
                    if 'access_token' not in token_data:
                        raise ValueError("Token endpoint response missing 'access_token' key")
                    if 'expires_in' not in token_data:
                        raise ValueError("Token endpoint response missing 'expires_in' key")
                    self.token = token_data['access_token']
                    self.token_expiry = time.time() + token_data['expires_in']
                print(f"Token retrieved: {self.token[:10]}... (length: {len(self.token)})")
            except requests.RequestException as e:
                # Try to parse the error response for more details
                error_message = str(e)
                if hasattr(e, 'response') and e.response is not None:
                    try:
                        error_json = e.response.json()
                        error_message = error_json.get('meta', {}).get('reason', str(e))
                    except ValueError:
                        error_message = e.response.text
                print(f"Failed to get access token: {error_message}")
                raise Exception(f"Failed to get access token: {error_message}")
            except (ValueError, KeyError) as e:
                print(f"Failed to parse token response: {str(e)}")
                raise
        print(f"Returning cached token: {self.token[:10]}... (length: {len(self.token)})")
        return self.token

    def get_access_token(self) -> str:
        result = self._get_access_token()
        print(f"get_access_token result: {repr(result)} (type: {type(result)})")
        return result

    def upload_file(self, location_id: int, uploaded_by: str, file_path: str, 
                    prepared_by: Optional[str] = None, report_title: Optional[str] = None, 
                    report_date: Optional[str] = None, display_filename: Optional[str] = None, 
                    service_groups: Optional[List[Dict[str, Any]]] = None, 
                    service_types: Optional[List[Dict[str, Any]]] = None, 
                    document_types: Optional[List[Dict[str, Any]]] = None, 
                    document_status: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Upload a file to the Collateral 360 system using a file path, reading into memory"""
        print(f"upload_file called with self: {self}")
        validate_location_id(location_id)
        validate_user(uploaded_by)
        
        if not os.path.isfile(file_path):
            raise ValueError(f"File not found at path: {file_path}")
        
        try:
            token = self.get_access_token()
            print(f"Token in upload_file: {repr(token)} (type: {type(token)})")
        except Exception as e:
            print(f"Failed to get access token: {str(e)}")
            raise Exception(f"Authentication failed: {str(e)}")

        data = {
            'locationId': str(location_id),
            'uploadedBy': uploaded_by,
        }
        
        filename = display_filename if display_filename else os.path.basename(file_path)
        data['displayFileName'] = filename
        
        if prepared_by:
            data['preparedBy'] = prepared_by
        if report_title:
            data['reportTitle'] = report_title
        if report_date:
            data['reportDate'] = report_date
        if service_groups:
            data['serviceGroups'] = stringify(service_groups)
        if service_types:
            data['serviceTypes'] = stringify(service_types)
        if document_types:
            data['documentTypes'] = stringify(document_types)
        if document_status:
            data['documentStatus'] = stringify(document_status)

        with open(file_path, 'rb') as f:
            file_content = f.read()
        
        print(f"File read, size: {len(file_content)} bytes")
        
        files = {
            'file': (filename, file_content, 'application/pdf')
        }
        
        endpoint = f"/v1/los/files/upload/locationId/{location_id}/uploadedBy/{uploaded_by}"
        
        if not self.rate_limiter.allow_request():
            raise Exception("Rate limit exceeded. Please wait before retrying.")

        try:
            response = self._make_request(
                'POST',
                endpoint,
                data=data,
                files=files,
                timeout=10,
                proxies=self.proxies
            )
            try:
                json_data = response.json()
                print(f"Upload response: {json_data}")
                return APIResponse(json_data).data
            except ValueError:
                return {
                    'status': 'success',
                    'locationId': location_id,
                    'uploadedBy': uploaded_by,
                    'displayFileName': filename
                }
        except requests.RequestException as e:
            print(f"Upload request failed: {str(e)}")
            content = e.response.content.decode('utf-8', errors='replace') if e.response else 'No response'
            try:
                error_json = e.response.json()
                message = error_json.get('message', 'Unknown error')
            except (ValueError, AttributeError):
                message = content
            raise Exception(f"File upload failed: {message}")
        except Exception as e:
            print(f"Upload processing failed: {str(e)}")
            raise

# Pytest tests
@pytest.fixture
def api_facade():
    """Fixture to create a fresh API facade instance"""
    facade = ThirdPartyAPIFacade()
    print(f"Created api_facade instance: {facade} (type: {type(facade)})")
    return facade

@pytest.fixture
def real_pdf_file(tmp_path):
    """Fixture to create a real minimal PDF file"""
    file_path = tmp_path / "test.pdf"
    pdf_content = (
        b"%PDF-1.4\n"
        b"1 0 obj\n"
        b"<< /Type /Catalog /Pages 2 0 R >>\n"
        b"endobj\n"
        b"2 0 obj\n"
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>\n"
        b"endobj\n"
        b"3 0 obj\n"
        b"<< /Type /Page /Parent 2 0 R /Resources <<>> /MediaBox [0 0 612 792] >>\n"
        b"endobj\n"
        b"xref\n"
        b"0 4\n"
        b"0000000000 65535 f \n"
        b"0000000010 00000 n \n"
        b"0000000077 00000 n \n"
        b"0000000128 00000 n \n"
        b"trailer\n"
        b"<< /Size 4 /Root 1 0 R >>\n"
        b"startxref\n"
        b"187\n"
        b"%%EOF"
    )
    file_path.write_bytes(pdf_content)
    return str(file_path)

def test_real_basic_upload(api_facade, real_pdf_file):
    """Test basic file upload with a real PDF path to the actual API"""
    print(f"test_real_basic_upload: api_facade = {api_facade} (type: {type(api_facade)})")
    response = api_facade.upload_file(
        location_id=432078,
        uploaded_by="simon_gray@msqga.wellsfargo.com",
        file_path=real_pdf_file,
        report_title="Test Report",
        display_filename="test_report.pdf"
    )
    
    print(f"Response Status Code: {response.status_code}")
    print(f"Response headers: {response.headers}")
    print(f"response body: {response.content.decode('utf-8', errors='replace')}")
    
    assert response is not None
    assert isinstance(response, dict)
    print(f"Basic upload response: {response}")

def test_real_upload_with_all_params(api_facade, real_pdf_file):
    """Test upload with all parameters using a real PDF path to the actual API"""
    print(f"test_real_upload_with_all_params: api_facade = {api_facade} (type: {type(api_facade)})")
    response = api_facade.upload_file(
        location_id=432078,
        uploaded_by="simon_gray@msqga.wellsfargo.com",
        file_path=real_pdf_file,
        report_title="Test Report",
        display_filename="test_report.pdf",
        prepared_by="preparer@example.com",
        report_date="2025-03-21",
        service_groups=[{"id": 1, "name": "Test Group"}],
        service_types=[{"id": 1, "type": "Assessment"}],
        document_types=[{"id": 1, "type": "Report"}],
        document_status={"status": "Completed"}
    )
    
    print(f"Response Status Code: {response.status_code}")
    print(f"Response headers: {response.headers}")
    print(f"response body: {response.content.decode('utf-8', errors='replace')}")
    
    assert response is not None
    assert isinstance(response, dict)
    print(f"Full params upload response: {response}")

def test_real_upload_existing_file(api_facade):
    """Test upload with an existing file path from your system"""
    print(f"test_real_upload_existing_file: api_facade = {api_facade} (type: {type(api_facade)})")
    existing_file_path = r"C:\Users\U769137\OneDrive - wells Fargo\Documents\Repos\test.pdf"
    
    if not os.path.exists(existing_file_path):
        pytest.skip(f"Test skipped: file not found at {existing_file_path}")
    
    response = api_facade.upload_file(
        location_id=432078,
        uploaded_by="simon_gray@msqga.wellsfargo.com",
        file_path=existing_file_path,
        report_title="existing_file_path"
    )
    
    print(f"Response Status Code: {response.status_code}")
    print(f"Response headers: {response.headers}")
    print(f"response body: {response.content.decode('utf-8', errors='replace')}")
    
    assert response is not None
    assert isinstance(response, dict)
    print(f"Existing file upload response: {response}")

@pytest.mark.parametrize("location_id", [-1, 0, "invalid"])
def test_real_invalid_location_id(api_facade, real_pdf_file, location_id):
    """Test upload with invalid location IDs"""
    print(f"test_real_invalid_location_id: api_facade = {api_facade} (type: {type(api_facade)})")
    with pytest.raises(ValueError):
        api_facade.upload_file(
            location_id=location_id,
            uploaded_by="simon_gray@msqga.wellsfargo.com",
            file_path=real_pdf_file
        )

if __name__ == "__main__":
    pytest.main(["-v", "-s"])
​​​​​​​​​​​​​​​​​​​​​​​​​​​​​​​​​​​​​​​​​​​​​​​​​​
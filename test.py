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
        self.token_expiry = 0  # Initialize to ensure token refresh check works
        self.proxies = {
            'http': 'http://proxy.abc.com:8080',
            'https': 'http://proxy.abc.com:8080'
        }
        self.session.proxies = self.proxies
        self.base_url = settings.API_BASE_URL
        self.rate_limiter = RateLimiter(limit=180, period=60)
        print(f"Initialized with base_url: {self.base_url}")

    def _make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Utility method to make HTTP requests with proper headers and token"""
        headers = kwargs.get('headers', {})
        # Only add token for non-auth requests (avoid circular dependency)
        if 'Authorization' not in headers and 'grant_type' not in kwargs.get('data', {}):
            token = self.get_access_token()
            headers['Authorization'] = f'Bearer {token}'
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
            try:
                response = self._make_request('POST', endpoint, data=payload)
                token_data = response.json()['data']
                self.token = token_data['access_token']
                self.token_expiry = time.time() + token_data['expires_in']
                print(f"Token retrieved: {self.token[:10]}... (length: {len(self.token)})")
            except requests.RequestException as e:
                print(f"Failed to get access token: {str(e)}")
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
        
        headers = {
            'Authorization': f'Bearer {token}',
        }
        endpoint = f"/v1/los/files/upload/locationId/{location_id}/uploadedBy/{uploaded_by}"
        
        if not self.rate_limiter.allow_request():
            raise Exception("Rate limit exceeded. Please wait before retrying.")

        try:
            response = self._make_request(
                'POST',
                endpoint,
                headers=headers,
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
    return ThirdPartyAPIFacade()

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
    response = api_facade.upload_file(
        location_id=123,  # Replace with valid location_id
        uploaded_by="testuser@example.com",  # Replace with valid email
        file_path=real_pdf_file,
        report_title="Test Report",
        display_filename="test_report.pdf"
    )
    
    assert response is not None
    assert isinstance(response, dict)
    print(f"Basic upload response: {response}")

def test_real_upload_with_all_params(api_facade, real_pdf_file):
    """Test upload with all parameters using a real PDF path to the actual API"""
    response = api_facade.upload_file(
        location_id=123,  # Replace with valid location_id
        uploaded_by="testuser@example.com",  # Replace with valid email
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
    
    assert response is not None
    assert isinstance(response, dict)
    print(f"Full params upload response: {response}")

def test_real_upload_existing_file(api_facade):
    """Test upload with an existing file path from your system"""
    existing_file_path = "/path/to/your/existing/file.pdf"  # Replace with your file path
    
    if not os.path.exists(existing_file_path):
        pytest.skip(f"Test skipped: File not found at {existing_file_path}")
    
    response = api_facade.upload_file(
        location_id=123,  # Replace with valid location_id
        uploaded_by="testuser@example.com",  # Replace with valid email
        file_path=existing_file_path,
        report_title="Existing File Test"
    )
    
    assert response is not None
    assert isinstance(response, dict)
    print(f"Existing file upload response: {response}")

@pytest.mark.parametrize("location_id", [-1, 0, "invalid"])
def test_real_invalid_location_id(api_facade, real_pdf_file, location_id):
    """Test upload with invalid location IDs"""
    with pytest.raises(ValueError):
        api_facade.upload_file(
            location_id=location_id,
            uploaded_by="testuser@example.com",
            file_path=real_pdf_file
        )

if __name__ == "__main__":
    pytest.main(["-v", "-s"])
​​​​​​​​​​​​​​​​​​​​​​​​​​​​​​​​​​​​​​​​​​​​​​​​​​
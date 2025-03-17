# blueprints/collateral.py
from flask import Blueprint, jsonify, request
from facade.third_party_api import api_facade
from schemas import (
    CollateralOverviewSchema,
    CollateralFieldsSchema,
    EnvironmentalRiskCodesSchema,
    UpdateCollateralRequestSchema,
    ServiceRequestSchema
)
from apispec import APISpec
from apispec.ext.marshmallow import MarshmallowPlugin
from apispec.ext.flask import FlaskPlugin
import yaml

collateral_bp = Blueprint('collateral', __name__, url_prefix='/api/v1/collateral')

# Initialize APISpec for this blueprint
spec = APISpec(
    title='Collateral360 API',
    version='1.0.0',
    openapi_version='3.0.3',
    plugins=[FlaskPlugin(), MarshmallowPlugin()],
    info=dict(
        description='API for managing collateral overview and related data'
    ),
    servers=[
        dict(url='https://api.uatabc.corp.lightboxre.com')
    ]
)

# Register schemas with APISpec
spec.components.schema('CollateralOverview', schema=CollateralOverviewSchema)
spec.components.schema('CollateralFields', schema=CollateralFieldsSchema)
spec.components.schema('EnvironmentalRiskCodes', schema=EnvironmentalRiskCodesSchema)
spec.components.schema('UpdateCollateralRequest', schema=UpdateCollateralRequestSchema)
spec.components.schema('ServiceRequest', schema=ServiceRequestSchema)

# Define security scheme
spec.components.security_scheme('bearerAuth', {
    'type': 'http',
    'scheme': 'bearer',
    'bearerFormat': 'JWT'
})

# Routes
@collateral_bp.route('/overview/<int:location_id>', methods=['GET'])
def get_collateral_overview(location_id):
    """Get collateral overview for a location
    ---
    get:
      summary: Get collateral overview
      parameters:
        - in: path
          name: location_id
          required: true
          schema:
            type: integer
        - in: query
          name: include
          schema:
            type: string
      responses:
        200:
          description: Successful response
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/CollateralOverview'
      security:
        - bearerAuth: []
    """
    try:
        result = api_facade.get_collateral_overview(location_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@collateral_bp.route('/overview/<int:location_id>', methods=['PATCH'])
def update_collateral_overview(location_id):
    """Update collateral overview for a location
    ---
    patch:
      summary: Update collateral overview
      parameters:
        - in: path
          name: location_id
          required: true
          schema:
            type: integer
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/UpdateCollateralRequest'
      responses:
        200:
          description: Successful response
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/CollateralOverview'
      security:
        - bearerAuth: []
    """
    try:
        data = request.get_json()
        result = api_facade.update_collateral_overview(location_id, data)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@collateral_bp.route('/fields', methods=['GET'])
def get_collateral_fields():
    """Get available collateral fields
    ---
    get:
      summary: Get collateral fields
      responses:
        200:
          description: Successful response
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/CollateralFields'
      security:
        - bearerAuth: []
    """
    try:
        result = api_facade.get_collateral_fields()
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@collateral_bp.route('/risk-codes/<int:location_id>', methods=['GET'])
def get_environmental_risk_codes(location_id):
    """Get environmental risk codes for a location
    ---
    get:
      summary: Get environmental risk codes
      parameters:
        - in: path
          name: location_id
          required: true
          schema:
            type: integer
      responses:
        200:
          description: Successful response
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/EnvironmentalRiskCodes'
      security:
        - bearerAuth: []
    """
    try:
        result = api_facade.get_environmental_risk_codes(location_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@collateral_bp.route('/service-request', methods=['POST'])
def submit_service_request():
    """Submit a service request
    ---
    post:
      summary: Submit a service request
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/ServiceRequest'
      responses:
        200:
          description: Service request submitted successfully
          content:
            application/json:
              schema:
                type: object
                properties:
                  meta:
                    type: object
                    properties:
                      success: {type: boolean}
                  data:
                    type: object
      security:
        - bearerAuth: []
    """
    try:
        service_request = request.get_json()
        # Validate the request against the schema
        schema = ServiceRequestSchema()
        validated_request = schema.load(service_request)
        # Here you would process the service request (e.g., save to a database, forward to another API)
        return jsonify({
            "meta": {"success": True},
            "data": {"message": "Service request submitted", "request": validated_request}
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Generate and save the OpenAPI spec for this blueprint
with collateral_bp.test_request_context():
    spec.path(view=get_collateral_overview)
    spec.path(view=update_collateral_overview)
    spec.path(view=get_collateral_fields)
    spec.path(view=get_environmental_risk_codes)
    spec.path(view=submit_service_request)

# Save to YAML
with open('openapi.yaml', 'w') as f:
    yaml.dump(spec.to_dict(), f, default_flow_style=False)
​​​​​​​​​​​​​​​​​​​​​​​​​​​​​​​​​​​​​​​​​​​​​​​​​​
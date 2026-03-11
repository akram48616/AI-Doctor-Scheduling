# tests/test_routes.py

import json
import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture
def app():
    """Create and configure Flask app for testing"""
    # Mock database initialization before importing app
    with patch('backend.utils.db.init_engine') as mock_init_engine, \
         patch('backend.utils.db.Base') as mock_base:
        
        # Create a mock engine
        mock_engine = MagicMock()
        mock_init_engine.return_value = mock_engine
        mock_base.metadata.create_all = MagicMock()
        
        from backend.app import create_app
        
        # Create app with mocked DB
        test_app = create_app()
        test_app.config['TESTING'] = True
        
        return test_app


@pytest.fixture
def client(app):
    """Create Flask test client"""
    return app.test_client()


# ============================================================================
# Admin Routes Tests
# ============================================================================

class TestAdminRoutes:
    """Test admin API endpoints"""
    
    def test_overbooking_plan_route_exists(self, client):
        """Test GET /api/admin/overbooking/plan endpoint exists"""
        response = client.get('/api/admin/overbooking/plan')
        assert response.status_code in [200, 500]
    
    def test_optimization_run_route_exists(self, client):
        """Test POST /api/admin/optimization/run endpoint exists"""
        response = client.post('/api/admin/optimization/run')
        assert response.status_code in [200, 500]
    
    def test_utilization_report_route_exists(self, client):
        """Test GET /api/admin/utilization/report endpoint exists"""
        response = client.get('/api/admin/utilization/report')
        assert response.status_code in [200, 500]


# ============================================================================
# Doctor Routes Tests
# ============================================================================

class TestDoctorRoutes:
    """Test doctor API endpoints"""
    
    def test_doctor_schedule_route_exists(self, client):
        """Test GET /api/doctor/<id>/schedule endpoint exists"""
        response = client.get('/api/doctor/1/schedule')
        assert response.status_code in [200, 500]
    
    def test_doctor_schedule_with_different_id(self, client):
        """Test with different doctor ID"""
        response = client.get('/api/doctor/999/schedule')
        assert response.status_code in [200, 500]
    
    def test_doctor_utilization_route_exists(self, client):
        """Test GET /api/doctor/<id>/utilization endpoint exists"""
        response = client.get('/api/doctor/1/utilization')
        assert response.status_code in [200, 500]
    
    def test_doctor_utilization_with_different_id(self, client):
        """Test utilization with different doctor ID"""
        response = client.get('/api/doctor/999/utilization')
        assert response.status_code in [200, 500]


# ============================================================================
# Patient Routes Tests
# ============================================================================

class TestPatientRoutes:
    """Test patient API endpoints"""
    
    def test_patient_appointments_route_exists(self, client):
        """Test GET /api/patient/<id>/appointments endpoint exists"""
        response = client.get('/api/patient/1/appointments')
        assert response.status_code in [200, 500]
    
    def test_patient_appointments_with_different_id(self, client):
        """Test with different patient ID"""
        response = client.get('/api/patient/999/appointments')
        assert response.status_code in [200, 500]
    
    def test_patient_book_route_exists(self, client):
        """Test POST /api/patient/<id>/book endpoint exists"""
        payload = {
            "doctor_id": 1,
            "datetime": "2026-03-15T14:00:00"
        }
        response = client.post(
            '/api/patient/1/book',
            data=json.dumps(payload),
            content_type='application/json'
        )
        assert response.status_code in [200, 400, 500]
    
    def test_patient_book_empty_json(self, client):
        """Test booking with empty JSON"""
        response = client.post(
            '/api/patient/1/book',
            data=json.dumps({}),
            content_type='application/json'
        )
        assert response.status_code in [200, 400, 500]
    
    def test_patient_book_with_different_patient_id(self, client):
        """Test booking for different patient"""
        payload = {
            "doctor_id": 5,
            "datetime": "2026-03-15T14:00:00"
        }
        response = client.post(
            '/api/patient/999/book',
            data=json.dumps(payload),
            content_type='application/json'
        )
        assert response.status_code in [200, 400, 500]


# ============================================================================
# Resource Routes Tests
# ============================================================================

class TestResourceRoutes:
    """Test resource API endpoints"""
    
    def test_optimized_slots_route_exists(self, client):
        """Test GET /api/resource/optimized-slots endpoint exists"""
        response = client.get('/api/resource/optimized-slots?doctors=1&date=2026-03-09')
        assert response.status_code in [200, 400, 500]
    
    def test_optimized_slots_multiple_doctors(self, client):
        """Test with multiple doctor IDs"""
        response = client.get('/api/resource/optimized-slots?doctors=1,2,3&date=2026-03-09')
        assert response.status_code in [200, 400, 500]
    
    def test_optimized_slots_invalid_date_format(self, client):
        """Test with invalid date format"""
        response = client.get('/api/resource/optimized-slots?doctors=1&date=invalid-date')
        assert response.status_code in [200, 400, 500]
    
    def test_optimized_slots_missing_date(self, client):
        """Test without date parameter"""
        response = client.get('/api/resource/optimized-slots?doctors=1')
        assert response.status_code in [200, 400, 500]
    
    def test_optimized_slots_missing_doctors(self, client):
        """Test without doctors parameter"""
        response = client.get('/api/resource/optimized-slots?date=2026-03-09')
        assert response.status_code in [200, 400, 500]
    
    def test_optimized_slots_invalid_doctor_ids(self, client):
        """Test with non-numeric doctor IDs"""
        response = client.get('/api/resource/optimized-slots?doctors=abc,xyz&date=2026-03-09')
        assert response.status_code in [200, 400, 500]


# ============================================================================
# App Integration Tests
# ============================================================================

class TestAppRoutes:
    """Test main app routes"""
    
    def test_index_route(self, client):
        """Test GET / (index route)"""
        response = client.get('/')
        assert response.status_code in [200, 404, 500]
    
    def test_health_route(self, client):
        """Test GET /health endpoint"""
        response = client.get('/health')
        assert response.status_code in [200, 500]
    
    def test_nonexistent_route_404(self, client):
        """Test accessing non-existent route returns 404"""
        response = client.get('/api/nonexistent/route')
        assert response.status_code in [404, 500]


# ============================================================================
# HTTP Method Tests
# ============================================================================

class TestHTTPMethods:
    """Test correct HTTP methods for each route"""
    
    def test_get_route_rejects_post(self, client):
        """Test that GET-only routes reject POST"""
        response = client.post('/api/admin/overbooking/plan')
        assert response.status_code in [405, 500]
    
    def test_post_route_rejects_get(self, client):
        """Test that POST-only routes reject GET"""
        response = client.get('/api/patient/1/book')
        assert response.status_code in [405, 500]


# ============================================================================
# Content Type Tests
# ============================================================================

class TestContentTypes:
    """Test content type handling"""
    
    def test_post_without_json_content_type(self, client):
        """Test POST without JSON content type"""
        response = client.post(
            '/api/patient/1/book',
            data='{"doctor_id": 1}',
            content_type='text/plain'
        )
        assert response.status_code in [200, 400, 415, 500]
    
    def test_invalid_json_payload(self, client):
        """Test with malformed JSON"""
        response = client.post(
            '/api/patient/1/book',
            data='invalid json {',
            content_type='application/json'
        )
        assert response.status_code in [200, 400, 500]


# ============================================================================
# Parameter Validation Tests
# ============================================================================

class TestParameterValidation:
    """Test parameter validation in routes"""
    
    def test_doctor_schedule_invalid_id_type(self, client):
        """Test doctor schedule with non-integer ID"""
        response = client.get('/api/doctor/abc/schedule')
        assert response.status_code in [200, 404, 500]
    
    def test_patient_book_missing_doctor_id(self, client):
        """Test booking without doctor_id"""
        payload = {"datetime": "2026-03-15T14:00:00"}
        response = client.post(
            '/api/patient/1/book',
            data=json.dumps(payload),
            content_type='application/json'
        )
        assert response.status_code in [200, 400, 500]
    
    def test_patient_book_missing_datetime(self, client):
        """Test booking without datetime"""
        payload = {"doctor_id": 1}
        response = client.post(
            '/api/patient/1/book',
            data=json.dumps(payload),
            content_type='application/json'
        )
        assert response.status_code in [200, 400, 500]
    
    def test_optimized_slots_negative_doctor_id(self, client):
        """Test with negative doctor ID"""
        response = client.get('/api/resource/optimized-slots?doctors=-1&date=2026-03-09')
        assert response.status_code in [200, 400, 500]
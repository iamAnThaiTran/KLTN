"""
Test suite for the recommendation API
"""

import pytest
from fastapi.testclient import TestClient
from app.api.routes import app, MockCrawler, RecommendationOrchestrator
import uuid

client = TestClient(app)

class TestHealthCheck:
    """Test health check endpoint"""
    
    def test_health_check(self):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestQueryEndpoint:
    """Test /api/query endpoint"""
    
    def test_vague_query(self):
        """Test with a vague query that requires clarification"""
        response = client.post(
            "/api/query",
            json={"user_input": "tôi muốn mua quà"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "conversation_id" in data
        assert "question" in data or "products" in data
        print(f"Vague query response: {data}")
    
    def test_specific_query(self):
        """Test with a specific query"""
        response = client.post(
            "/api/query",
            json={"user_input": "giày thể thao size 42 màu trắng"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "conversation_id" in data
        print(f"Specific query response: {data}")
    
    def test_query_with_conversation_id(self):
        """Test query with existing conversation_id"""
        conversation_id = str(uuid.uuid4())
        response = client.post(
            "/api/query",
            json={
                "user_input": "tôi muốn mua giày",
                "conversation_id": conversation_id
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["conversation_id"] == conversation_id


class TestRespondEndpoint:
    """Test /api/respond endpoint"""
    
    def test_respond_to_question(self):
        """Test responding to a clarification question"""
        # First, get a query that needs info
        query_response = client.post(
            "/api/query",
            json={"user_input": "tôi muốn mua quà"}
        )
        assert query_response.status_code == 200
        conversation_id = query_response.json()["conversation_id"]
        
        # Then respond
        response = client.post(
            "/api/respond",
            json={
                "conversation_id": conversation_id,
                "question_type": "category",
                "value": "giày"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["conversation_id"] == conversation_id
        print(f"Response answer: {data}")
    
    def test_respond_nonexistent_session(self):
        """Test responding to non-existent session"""
        response = client.post(
            "/api/respond",
            json={
                "conversation_id": "invalid-session-id",
                "question_type": "category",
                "value": "giày"
            }
        )
        assert response.status_code == 404


class TestSessionEndpoints:
    """Test session management endpoints"""
    
    def test_get_session(self):
        """Test getting session state"""
        # Create a session
        query_response = client.post(
            "/api/query",
            json={"user_input": "tôi muốn mua quà"}
        )
        conversation_id = query_response.json()["conversation_id"]
        
        # Get session
        response = client.get(f"/api/session/{conversation_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["conversation_id"] == conversation_id
        print(f"Session state: {data}")
    
    def test_get_nonexistent_session(self):
        """Test getting non-existent session"""
        response = client.get("/api/session/invalid-id")
        assert response.status_code == 404
    
    def test_clear_session(self):
        """Test clearing a session"""
        # Create a session
        query_response = client.post(
            "/api/query",
            json={"user_input": "tôi muốn mua quà"}
        )
        conversation_id = query_response.json()["conversation_id"]
        
        # Clear it
        response = client.delete(f"/api/session/{conversation_id}")
        assert response.status_code == 200
        
        # Verify it's gone
        response = client.get(f"/api/session/{conversation_id}")
        assert response.status_code == 404


class TestConversationFlow:
    """Test complete conversation flows"""
    
    def test_full_conversation_flow(self):
        """Test a complete conversation from start to results"""
        print("\n=== Testing Full Conversation Flow ===")
        
        # Step 1: Initial vague query
        print("\nStep 1: User asks 'tôi muốn mua quà'")
        response1 = client.post(
            "/api/query",
            json={"user_input": "tôi muốn mua quà"}
        )
        assert response1.status_code == 200
        data1 = response1.json()
        conversation_id = data1["conversation_id"]
        print(f"Response: {data1}")
        
        # Step 2: User responds to clarification
        if "question" in data1:
            print(f"\nStep 2: API asks for clarification")
            response2 = client.post(
                "/api/respond",
                json={
                    "conversation_id": conversation_id,
                    "question_type": "category",
                    "value": "giày"
                }
            )
            assert response2.status_code == 200
            data2 = response2.json()
            print(f"Response: {data2}")
            
            # Continue until we get products
            if "question" in data2:
                print(f"\nStep 3: User responds to another question")
                response3 = client.post(
                    "/api/respond",
                    json={
                        "conversation_id": conversation_id,
                        "question_type": "attribute",
                        "value": "thể thao",
                        "attribute_name": "loại"
                    }
                )
                assert response3.status_code == 200
                data3 = response3.json()
                print(f"Response: {data3}")


if __name__ == "__main__":
    # Run with: pytest test_routes.py -v -s
    pytest.main([__file__, "-v", "-s"])

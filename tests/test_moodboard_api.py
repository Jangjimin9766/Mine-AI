from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from app.main import app

client = TestClient(app)

@patch("app.core.llm_client.llm_client.generate_text")
@patch("app.core.local_diffusion_client.LocalDiffusionClient.generate_image")
def test_create_moodboard(mock_generate_image, mock_generate_text):
    # Mock LLM responses
    mock_generate_text.return_value = "winter, jazz, cozy, warm lighting, 8k"
    mock_generate_image.return_value = "data:image/png;base64,iVBORw0KGgo..."

    response = client.post(
        "/api/magazine/moodboard",
        json={
            "topic": None,
            "user_mood": "Sophisticated",
            "user_interests": ["Design", "Tech"],
            "magazine_tags": ["Minimalist", "Modern"],
            "magazine_titles": ["Future of AI", "Design Trends"]
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data["image_url"].startswith("data:image/png;base64,")
    assert data["description"] == "winter, jazz, cozy, warm lighting, 8k"
    
    # Verify mock calls
    mock_generate_text.assert_called_once()
    mock_generate_image.assert_called_once()

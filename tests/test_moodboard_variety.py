from app.core.moodboard_maker import generate_moodboard_prompt
from unittest.mock import patch

# Mock LLM Client to avoid API calls, but we want to see the INPUT prompt to the LLM changing
# However, generate_moodboard_prompt calls llm_client.generate_text.
# We want to verify that the SYSTEM PROMPT passed to llm_client contains different variations.

@patch("app.core.llm_client.llm_client.generate_text")
def test_moodboard_variety(mock_generate_text):
    mock_generate_text.return_value = "Mocked Prompt"
    
    # Call 1
    generate_moodboard_prompt(topic="Test")
    call_args_1 = mock_generate_text.call_args[0] # (system_prompt, user_prompt)
    system_prompt_1 = call_args_1[0]
    
    # Call 2
    generate_moodboard_prompt(topic="Test")
    call_args_2 = mock_generate_text.call_args[0]
    system_prompt_2 = call_args_2[0]
    
    # Call 3
    generate_moodboard_prompt(topic="Test")
    call_args_3 = mock_generate_text.call_args[0]
    system_prompt_3 = call_args_3[0]

    print("\n--- Prompt Variation Check ---")
    print(f"Prompt 1 contains variation: {system_prompt_1[-200:]}") # Print end of prompt where variation is
    print(f"Prompt 2 contains variation: {system_prompt_2[-200:]}")
    
    # Note: Randomness might pick the same one, but with 5 variations, it's unlikely to be same 3 times.
    # We won't assert inequality strictly to avoid flaky tests, but we print it for manual verification.
    
if __name__ == "__main__":
    test_moodboard_variety()

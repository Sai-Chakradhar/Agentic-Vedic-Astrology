import google.generativeai as genai
import json

def format_chart_for_prompt(chart_data):
    """
    Converts complex chart JSON into a structured text summary for LLM.
    """
    # Basic verification
    if "error" in chart_data:
        return f"Error in chart data: {chart_data['error']}"
        
    summary = []
    summary.append("## Birth Chart Details")
    
    # Lagna / Ascendant
    if "D1" in chart_data and "ascendant" in chart_data["D1"]:
        asc = chart_data["D1"]["ascendant"]
        summary.append(f"**Ascendant (Lagna)**: {asc.get('sign')} ({asc.get('nakshatra')})")
        
    # Planets
    if "D1" in chart_data and "planets" in chart_data["D1"]:
        summary.append("\n### Planetary Positions (D1 Rasi):")
        for planet, details in chart_data["D1"]["planets"].items():
            summary.append(f"- **{planet}**: {details.get('sign')} in House {details.get('house')} "
                           f"(Nakshatra: {details.get('nakshatra')})")
                           
    # Dasha
    # The JSON structure for dasha seemed complex in the grep. 
    # Let's look for "Vimshottari" or similar keys if they exist, or summarize the huge list.
    # Searching specifically for current dasha would be ideal, but for now we dump what we have efficiently.
    # If the JSON has a "Vimshottari" section, usage is better.
    # Based on grep, "dashaLord" appears many times.
    # We will pass the structural relevant parts.
    
    # For now, let's append the whole JSON string but truncated if too huge?
    # Gemini can handle it. Let's just pass the JSON structure as text in a code block.
    # But clean it a bit if possible.
    
    return json.dumps(chart_data, indent=2)

def get_astrology_response(chart_data, user_query, api_key, stream=False):
    """
    Sends chart context and query to Gemini.
    """
    if not api_key:
        return "Error: API Key is missing."
    
    # Clean API Key to prevent metadata errors
    api_key = api_key.strip()
    
    try:
        genai.configure(api_key=api_key)
    except Exception as e:
        # Catch any potential configuration errors, though genai.configure is mostly local.
        # Network errors related to the key typically occur during API calls (e.g., list_models).
        return f"Error configuring Gemini API: {str(e)}"
    
    # Dynamically find supported models
    supported_models = []
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                supported_models.append(m.name)
    except Exception as e:
        error_msg = str(e)
        if "400" in error_msg or "INVALID_ARGUMENT" in error_msg:
            return "Error: The API Key provided is invalid (400). Please check for typos."
        if "403" in error_msg or "PERMISSION_DENIED" in error_msg:
            return "Error: Permission denied (403). The API Key may not have access to Generative Language API."
        return f"Error connecting to Google API: {error_msg}"
        
    if not supported_models:
        return "No models found that support generateContent. Your API key might need to be enabled for specific models in Google AI Studio."
        
    # Priority list
    priorities = ['models/gemini-1.5-flash', 'models/gemini-1.5-flash-001', 'models/gemini-pro', 'models/gemini-1.0-pro']
    
    # Determine the model to use
    selected_model = None
    for p in priorities:
        if p in supported_models:
            selected_model = p
            break
            
    # Fallback to the first available if none of priorities match
    if not selected_model:
        selected_model = supported_models[0]
    
    chart_context = format_chart_for_prompt(chart_data)
        
    prompt = f"""
You are an expert Vedic Astrologer. You have deep knowledge of Parashara Hora Sastra, Jaimini Sutras, and modern interpretations.
You have been provided with the user's Vedic Birth Chart and Dasha details below.

User Query: "{user_query}"

### Chart Data
```json
{chart_context}
```

Instructions:
1. Analyze the chart specifically answering the user's query.
2. Use the provided planetary positions, house placements, and Nakshatras.
3. Pay close attention to the Vimshottari Dasha (Mahadasha/Antardasha) if relevant to the timing of the query. (Look for 'dasha' keys in the data).
4. Be accurate, empathetic, and insightul.
5. If the query is about specific timing, correlate with the Dasha periods provided.

Answer:
"""
    
    try:
        model = genai.GenerativeModel(selected_model)
        if stream:
            return model.generate_content(prompt, stream=True)
        else:
            response = model.generate_content(prompt)
            return response.text
    except Exception as e:
        error_msg = f"Error contacting Gemini: {str(e)}"
        if stream:
            # Yield error as a chunk so frontend handles it gracefully
            return (type('obj', (object,), {'text': error_msg}) for _ in [None])
        return error_msg

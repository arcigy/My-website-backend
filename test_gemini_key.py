import os
import google.generativeai as genai

KEY = "AIzaSyASyd1a4Irm_fz_dm8EtpXgg7BhKzguoSs"

def test_key():
    try:
        genai.configure(api_key=KEY)
        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content("Say 'Key is working!'")
        print(f"RESULT: {response.text}")
    except Exception as e:
        print(f"FAILED: {str(e)}")

if __name__ == "__main__":
    test_key()

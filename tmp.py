# import requests
# import os

# api_key = os.environ.get("GROQ_API_KEY")
# url = "https://api.groq.com/openai/v1/models"

# headers = {
#     "Authorization": f"Bearer {api_key}",
#     "Content-Type": "application/json"
# }

# response = requests.get(url, headers=headers)

# print(response.json())


import google.generativeai as genai

# 본인의 API 키가 설정되어 있어야 합니다.
genai.configure(api_key="AIzaSyBKEwimgefkD1QlHhH14hqXELj8Rvt5kG8")

print("사용 가능한 모델 목록:")
for m in genai.list_models():
    # 3.1 또는 lite가 포함된 모델만 필터링해서 출력
    if "3.1" in m.name or "lite" in m.name.lower():
        print(f"API 호출용 모델명: {m.name}")
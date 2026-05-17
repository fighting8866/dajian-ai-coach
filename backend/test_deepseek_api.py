import os
from openai import OpenAI

client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
)

resp = client.chat.completions.create(
    model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
    messages=[
        {"role": "system", "content": "你是一个测试助手。"},
        {"role": "user", "content": "请只回复：DeepSeek API 测试成功"},
    ],
    stream=False,
)

print(resp.choices[0].message.content)
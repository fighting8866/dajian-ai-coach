from openai import OpenAI

client = OpenAI(
    base_url="http://10.192.187.186:11434/v1/",
    api_key="ollama",
)

resp = client.chat.completions.create(
    model="qwen2.5:3b",
    messages=[
        {"role": "system", "content": "你是答辩追问老师。"},
        {"role": "user", "content": "请只回复：远端Ollama OpenAI兼容测试成功"},
    ],
)

print(resp.choices[0].message.content)
# LLM modules

This project uses Qwen max model with OPENAI chat completions API.
Other models can be used as well. Especially, if you want to switch to ChatGPT, you can directly modify the following code in GATSIM/config.py:

```
client = OpenAI(
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)
```

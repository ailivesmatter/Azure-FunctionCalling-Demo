'''
创建 function calling 的过程包括 3 个主要步骤：

1.调用 Chat Completions API，并提供您的函数列表和用户消息。
2.读取模型的响应以执行操作，即执行函数或 API 调用。
3.使用函数的响应再次调用 Chat Completions API，以使用该信息创建对用户的响应。

'''
import os
import openai
import requests
from openai import AzureOpenAI
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
deployment = os.environ['AZURE_OPENAI_DEPLOYMENT']
api_key = os.getenv("AZURE_OPENAI_API_KEY")

client = AzureOpenAI(
    api_key=api_key,
    api_version=os.environ['AZURE_OPENAI_API_VERSION'],
    azure_endpoint=os.environ['AZURE_OPENAI_ENDPOINT']
)

# 创建用户消息
messages = [{"role": "user", "content": "Find me a good course for a beginner student to learn Azure."}]

# 创建 functions
functions = [
    {
        "name": "search_courses",
        "description": "Retrieves courses from the search index based on the parameters provided",
        "parameters": {
            "type": "object",
            "properties": {
                "role": {
                    "type": "string",
                    "description": "The role of the learner (i.e. developer, data scientist, student, etc.)"
                },
                "product": {
                    "type": "string",
                    "description": "The product that the lesson is covering (i.e. Azure, Power BI, etc.)"
                },
                "level": {
                    "type": "string",
                    "description": "The level of experience the learner has prior to taking the course (i.e. beginner, intermediate, advanced)"
                }
            },
            "required": ["role"]
        }
    }
]

# 进行 function call
response = client.chat.completions.create(
    model=deployment,
    messages=messages,
    functions=functions,
    function_call="auto"
)

# Accessing the response correctly
response_message = response.choices[0].message

# 现在我们将定义调用 Microsoft Learn API 来获取课程列表的函数
def search_courses(role, product, level):
    url = "https://learn.microsoft.com/api/catalog/"
    params = {
        "role": role,
        "product": product,
        "level": level
    }
    response = requests.get(url, params=params)
    modules = response.json()["modules"]
    results = []
    for module in modules[:5]:
        title = module["title"]
        url = module["url"]
        results.append({"title": title, "url": url})
    return str(results)

# Check if the model wants to call a function
if response_message.function_call.name:
    print("Recommended Function call:")
    print(response_message.function_call.name)
    print()

    # Call the function.
    function_name = response_message.function_call.name

    available_functions = {
        "search_courses": search_courses,
    }
    function_to_call = available_functions[function_name]

    function_args = json.loads(response_message.function_call.arguments)
    function_response = function_to_call(**function_args)

    print("Output of function call:")
    print(function_response)
    print(type(function_response))

    # Add the assistant response and function response to the messages
    messages.append(  # adding assistant response to messages
        {
            "role": response_message.role,
            "function_call": {
                "name": function_name,
                "arguments": response_message.function_call.arguments,
            },
            "content": None
        }
    )
    messages.append(  # adding function response to messages
        {
            "role": "function",
            "name": function_name,
            "content": function_response,
        }
    )

# 在我们将向 LLM 发送更新后的消息 messages ，以便我们可以接收自然语言响应，而不是 API JSON 格式的响应。
print("Messages in next request:")
print(messages)
print()

second_response = client.chat.completions.create(
    messages=messages,
    model=deployment,
    function_call="auto",
    functions=functions,
    temperature=0
)  # get a new response from GPT where it can see the function response

print(second_response.choices[0].message)

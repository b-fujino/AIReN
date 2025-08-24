
from dotenv import load_dotenv
load_dotenv()  # Load environment variables from .env file
import requests
import json
import time
import sys

from pprint import pprint

import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # Set the logging level to DEBUG
fname = f"Study_Output/debug_log_{time.strftime('%Y%m%d_%H%M%S')}.log"
fl_handler = logging.FileHandler(filename=fname, encoding="utf-8")
fl_handler.setFormatter(logging.Formatter('[%(asctime)s] - %(levelname)s - %(message)s'))
logger.addHandler(fl_handler)


#modelname = "gpt-oss:latest" # Currently structured output has not been supported yet.   
modelname = "gemma3n:e4b-it-fp16" # Not support Tools
#modelname = "gemma3n:e2b-it-fp16" # Not support Tools
#modelname = "gemma3n:latest" # Not support Tools

#modelname = "mistral-small3.2:latest" 
Key = "ollama"
IntervalForGemma3n = 0.0 # Gemma3n output is too fast, so we need to slow it down by setting this.
SLEEPTIME = 0

from pydantic import BaseModel, Field
from ollama import chat, ChatResponse

class CheckValidity(BaseModel):
    is_valid: bool = Field(description="If the answer is valid, true; if not, false.")
    feedback: str = Field(description="Feedback on the reporter's answer's validity.")


class JudgeAndInstruct(BaseModel):
    go_next: bool = Field(description="If you think 'go ahead', true; if you think 'stay and follow your instruction', false.")
    instruct: list[str] = Field(description="Instructions based on the situation. An array with 1 to 3 elements.", max_items=3, min_items=1)
    model_config = {
        "description": "Return a 'go_next' and 'instruct' as an answer to the user's input.",
    }

# format_JudgeAndInstruct = {
# #region
#     "type": "object",
#     "description": "Return a 'go_next'  and 'instruct' based on the user's question.",
#     "properties": {
#         "go_next": {
#             "type": "boolean",
#             "description": "If Yes, true; if No, false."
#         },
#         "instruct": {
#             "type": "array",
#             "description": "Instructions based on the situation. An array with 1 to 3 elements.",
#             "items": {
#                 "type": "string",
#                 "description": "One specific instruction."
#             },
#             "minItems": 1,
#             "maxItems": 3
#         },
#     },
#     "required": ["go_next", "instruct"]
# }
# # endregion

# print(json.dumps(JudgeAndInstruct.model_json_schema(), ensure_ascii=False, indent=2))

Tool_JudgeAndInstruct = [{
#region
    "type": "function",
    "function": {
        "name": "judge_and_instruct",
        "description": "Return a judgment and instructions based on the user's question.",
        "parameters": {
            "type": "object",
            "properties": {
                "go_next": {
                    "type": "boolean",
                    "description": "If Yes, true; if No, false."
                },
                "instruct": {
                    "type": "array",
                    "description": "Instructions based on the situation. An array with 1 to 3 elements.",
                    "items": {
                        "type": "string",
                        "description": "One specific instruction."
                    },
                    "minItems": 1,
                    "maxItems": 3
                }
            },
            "required": ["go_next", "instruct"]
        }
    }
}]
# endregion



def Agent_chat(messages, system_prompt, model=modelname, temperature=0.7, max_tokens=8192*2, stream=False, print_output=True, Debug=False):
    '''
    Call the Ollama API with the given parameters.

    This function sends a request to the Ollama API and returns the response.
    Parameters:
    - messages: A list of message objects to send to the API.
    - system_prompt: The system prompt to include in the request.
    - model: The model to use for the request (default is the global modelname).
    - temperature: The temperature to use for the request (default is 0.7).
    - max_tokens: The maximum number of tokens to generate in the response (default is 8192).
    - stream: Whether to stream the response (default is False).
    - print_output: Whether to print the response (default is True).
    - Debug: Whether to enable debugging information (used tokens, duration) output (default is False).

    Returns:
    - The response from the Ollama API.

    Note:
    Even if Debug is False, debugging information is still logged to the log file.
    '''
    time.sleep(SLEEPTIME)  # Wait for 10 seconds before making the API call


    # system promptをmessagesの先頭に追加
    full_messages = [{"role": "system", "content": system_prompt}] + messages
    if Debug:
        print("Prompt:")  
        pprint(full_messages)

    try:
        response: ChatResponse = chat(
            model=model,
            messages=full_messages,
            options={
                "temperature": temperature,
                "num_ctx": max_tokens
            },
            stream=stream,            
        )
        if not stream:
            logger.debug(f"""
                        Prompt: {full_messages}
                        Response: {response.message.content}
                        Prompt tokens: {response.prompt_eval_count}
                        Completion tokens: {response.eval_count}
                        Duration: {response.total_duration/1e9: .2f} seconds""")
            if print_output:
                if Debug:
                    print(f"prompt_token: {response.prompt_eval_count}")
                    print(f"completion_token: {response.eval_count}")
                    print(f"duration: {response.total_duration/1e9: .2f} seconds")
                print(response.message.content)
            return response.message.content
        else:
            messages = "" # for reassemblying streamed messages
            for chunk in response:
                if 'content' in chunk["message"]:
                    if print_output:
                        print(chunk["message"]["content"], end="", flush=True)
                        if model == "gemma3n:e4b-it-fp16": # Gemma3n's streaming is too fast, so...
                            time.sleep(IntervalForGemma3n)  # Add a small delay for streaming output
                    messages += chunk["message"]["content"]
                if chunk.get('done'):
                    prompt_token = chunk.get('prompt_eval_count', 0)
                    completion_token = chunk.get('eval_count', 0)
                    duration = chunk.get('total_duration', 0)/ 1e9
                    print("")  # Ensure a newline after the streamed output


            logger.debug(f"""
                        Prompt: {full_messages}
                        Response: {messages}
                        Prompt tokens: {prompt_token}
                        Completion tokens: {completion_token}
                        Duration: {duration: .2f} seconds""")

            if print_output:
                if Debug:
                    print(f"\nprompt_token: {prompt_token}")
                    print(f"completion_token: {completion_token}")
                    print(f"duration: {duration: .2f} seconds")

            return messages

    except requests.exceptions.RequestException as e:
        print(f"Error calling OpenAI API: {e}")
        return None

               
#format_JudgeAndInstruct
def Agent_chat_parsed(messages, system_prompt, format, model=modelname,  temperature=0.0, max_tokens=8192*2, print_output=True, Debug=False):
    '''
    Call the Ollama API with the given parameters and a tool.

    This function sends a request to the Ollama API and returns the response structured.
    Parameters:
    - messages: A list of message objects to send to the API.
    - system_prompt: The system prompt to include in the request.
    - tool_name: The name of the tool to use for the request.
    - model: The model to use for the request (default is the global modelname).
    - temperature: The temperature to use for the request (default is 0.7).
    - print_output: Whether to print the output (default is True).
    - Debug: Whether to enable debuging information(used tokens, duration) output (default is False).
    Returns:
    - The parsed response from the Ollama API.
    Note:
    Even if Debug is False, debugging information is still logged to the log file.
    '''
    time.sleep(SLEEPTIME)  # Wait for 1 second before making the API call

    # system promptをmessagesの先頭に追加
    full_messages = [{"role": "system", "content": system_prompt}] + messages
    if Debug:
        print("Prompt:")  
        pprint(full_messages)

    try:
        response: ChatResponse = chat(
            model=model,
            messages=full_messages,
            format=format,
            options={
                "temperature": temperature,
                "num_ctx": max_tokens
            }
        )
        # print(f"Prompt: {full_messages}")
        logger.debug(f"""
                    Prompt: {full_messages}
                    Response: {response.message.content}
                    Prompt tokens: {response.prompt_eval_count}
                    Completion tokens: {response.eval_count}
                    Duration: {response.total_duration/1e9: .2f} seconds""")
        
        if print_output:
            if Debug:
                print(f"prompt_token: {response.prompt_eval_count}")
                print(f"completion_token: {response.eval_count}")
                print(f"duration: {response.total_duration/1e9: .2f} seconds")
            print(json.loads(response.message.content))
        return json.loads(response.message.content)

    except requests.exceptions.RequestException as e:
        logger.error(f"Error calling OpenAI API: {e}\nBody: {getattr(e, 'response', None) and e.response.text}")
        print(f"Error calling OpenAI API: {e}\nBody: {getattr(e, 'response', None) and e.response.text}")



def Agent_chat_tools(messages, system_prompt, model=modelname, tools=Tool_JudgeAndInstruct, temperature=0.7, max_tokens=8192, print_output=True, Debug=False):
    """
    Call the Ollama API with the given parameters and a tool.

    This function sends a request to the Ollama API and returns the response structured.
    Parameters:
    - messages: A list of message objects to send to the API.
    - system_prompt: The system prompt to include in the request.
    - tool_name: The name of the tool to use for the request.
    - model: The model to use for the request (default is the global modelname).
    - temperature: The temperature to use for the request (default is 0.7).
    - print_output: Whether to print the output (default is True) to terminal.
    - Debug: Whether to enable debugging information (used tokens, duration) output (default is False).
    Returns:
    - JSON object followed by tools
    Note:
    Even if Debug is False, debugging information is still logged to the log file.
    """
    # system promptをmessagesの先頭に追加
    full_messages = [{"role": "system", "content": system_prompt}] + messages
    if Debug:
        print("Prompt:")  
        pprint(full_messages)

    count = 0
    while count < 20:
        try:
            response: ChatResponse = chat(
                model=model,
                messages=full_messages,
                tools=tools,
                options={
                    "temperature": temperature,
                    "num_ctx": max_tokens
                }
            )
            logger.debug(f"""
                        Prompt: {full_messages}
                        Response: {response.message.content if response.message.tool_calls is None else response.message.tool_calls[0].function.arguments}
                        Prompt tokens: {response.prompt_eval_count}
                        Completion tokens: {response.eval_count}
                        Duration: {response.total_duration/1e9: .2f} seconds""")            
            if print_output:
                if Debug:
                    print(f"prompt_token: {response.prompt_eval_count}")
                    print(f"completion_token: {response.eval_count}")
                    print(f"duration: {response.total_duration/1e9: .2f} seconds")
            if response.message.tool_calls is None:
                if Debug:
                    print(response.message.content)
                    print("No tool calls found in the response. Retrying...")
                count+=1
                continue
            if print_output:
                print(response.message.tool_calls[0].function.arguments)
            return response.message.tool_calls[0].function.arguments

        except requests.exceptions.RequestException as e:
            logger.error(f"Error calling OpenAI API: {e}\nBody: {getattr(e, 'response', None) and e.response.text}")    
            print(f"Error calling OpenAI API: {e}\nBody: {getattr(e, 'response', None) and e.response.text}")

    if print_output:
        print(f"Total retries: {count}")
        sys.exit(1)



# 実行例
if __name__ == "__main__":
    result = Agent_chat(
        messages=[{"role": "user", "content": "Hello, how are you?"}],
        system_prompt="You are a helpful assistant.",
        stream=True
    )
   
    print(f"===== turn ==============================")
    
    for i in range(1):
        result = Agent_chat_parsed(
            messages=[{"role": "user", "content": "Should I send a present to my girlfriend on her birthday?"}],
            system_prompt="You are a helpful assistant. You will request a advice from user. If you think user's message is reasonable and positive, 'go_next' should be True. Otherwise, it should be False and give the user some advices as 'instruct'.",
            temperature=0.7,
            format=JudgeAndInstruct.model_json_schema(),  # Use the JudgeAndInstruct model to format the response
        )

        
    print(f"===== turn ==============================")
    for i in range(1):
        result = Agent_chat_tools(
            messages=[{"role": "user", "content": "Should I send a present to my girlfriend on her birthday?"}],
            system_prompt="You are a helpful assistant. You will request a advice from user. If you think user's message is reasonable and positive, 'go_next' should be True. Otherwise, it should be False and give the user some advices as 'instruct'.",
            temperature=0.7,
        )


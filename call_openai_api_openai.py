
from dotenv import load_dotenv
load_dotenv()  # Load environment variables from .env file
import requests
import json
import time
import sys
import os

from pprint import pprint

import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # Set the logging level to DEBUG
fname = f"Study_Output/debug_log_{time.strftime('%Y%m%d_%H%M%S')}.log"
fl_handler = logging.FileHandler(filename=fname, encoding="utf-8")
fl_handler.setFormatter(logging.Formatter('[%(asctime)s] - %(levelname)s - %(message)s'))
logger.addHandler(fl_handler)


from pydantic import BaseModel, Field
from openai import OpenAI
modelname = "gpt-4o-mini"  # "gpt-4o" "gpt-4o-mini" "llama2"
IntervalForGemma3n = 0.0 # Gemma3n output is too fast, so we need to slow it down by setting this.
SLEEPTIME = 0
client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY"),
)


class CheckValidity(BaseModel):
    is_valid: bool = Field(description="If the answer is valid, true; if not, false.")
    feedback: str = Field(description="Feedback on the reporter's answer's validity.")


class JudgeAndInstruct(BaseModel):
    go_next: bool = Field(description="If you think 'go ahead', true; if you think 'stay and follow your instruction', false.")
    instruct: list[str] = Field(description="Instructions based on the situation. An array with 1 to 3 elements.", max_items=3, min_items=1)
    model_config = {
        "description": "Return a 'go_next' and 'instruct' as an answer to the user's input.",
    }


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



def Agent_chat(messages, system_prompt, model=modelname, temperature=0.7, max_tokens=8192*2, stream=False, Debug=False):
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
    - Debug: Whether to enable debugging information (used tokens, duration) output (default is False).
    Returns:
    - The response from the Ollama API.
    Note:
    Even if Debug is False, debugging information is still logged to the log file.
    '''

    if not stream:
        return _Agent_chat_once(messages, system_prompt, model=model, temp=temperature, max_tokens=max_tokens, Debug=Debug)
    else:
        return _Agent_chat_stream(messages, system_prompt, model=model, temp=temperature, max_tokens=max_tokens, Debug=Debug)


def _Agent_chat_once(messages, system_prompt, temp, model=modelname, max_tokens=8192*2,  Debug=False):
    ''',
    Call the OpenAI API with the given parameters.

    This function sends a request to the OpenAI API and returns the response.
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
    full_messages = [{"role": "developer", "content": system_prompt}] + messages
    if Debug:
        print("Prompt:")  
        pprint(full_messages)

    response = client.responses.create(
        model=model,
        input=full_messages,
        #instructions= system_prompt,
        #input = messages,
        max_output_tokens=max_tokens,
        temperature=temp,
        stream=False,            
    )
    logger.debug(f"""
                Prompt: {full_messages}
                Response: {response.output_text}
                Prompt tokens: {response.usage.input_tokens}
                Completion tokens: {response.usage.output_tokens}
                """)
    return response.output_text


def _Agent_chat_stream(messages, system_prompt, model=modelname, temp=0.7, max_tokens=8192*2,  Debug=False):
    '''
    Call the OpenAI API with the given parameters.

    This function sends a request to the OpenAI API and returns the response.
    Parameters:
    - messages: A list of message objects to send to the API.
    - system_prompt: The system prompt to include in the request.
    - model: The model to use for the request (default is the global modelname).
    - temperature: The temperature to use for the request (default is 0.7).
    - max_tokens: The maximum number of tokens to generate in the response (default is 8192).
    - print_output: Whether to print the response (default is True).
    - Debug: Whether to enable debugging information (used tokens, duration) output (default is False).

    Returns:
    - The response with streaming from the OpenAI API.

    Note:
    Even if Debug is False, debugging information is still logged to the log file.
    '''
    # system promptをmessagesの先頭に追加
    full_messages = [{"role": "developer", "content": system_prompt}] + messages
    if Debug:
        print("Prompt:")  
        pprint(full_messages)

    response = client.responses.stream(
        model=model,
        input=full_messages,
        # instructions= system_prompt,
        # input = messages,        
        max_output_tokens=max_tokens,
        temperature=temp,
    )

    messages = ""
    with response as r:
        for chunk in r:
            #print(chunk)
            if chunk.type == "response.output_text.delta":
                yield chunk.delta
                messages += chunk.delta


    logger.debug(f"""
                Prompt: {full_messages}
                Response: {messages}
            """)
                # Prompt tokens: {prompt_token}
                # Completion tokens: {completion_token}
                # Duration: {duration: .2f} seconds

    return messages



               
#format_JudgeAndInstruct
def Agent_chat_parsed(messages, system_prompt, format, model=modelname,  temperature=0.0, max_tokens=8192*2, print_output=True, Debug=False):
    '''
    Call the OpenAI API with the given parameters and a tool.

    This function sends a request to the OpenAI API and returns the response structured.
    Parameters:
    - messages: A list of message objects to send to the API.
    - system_prompt: The system prompt to include in the request.
    - tool_name: The name of the tool to use for the request.
    - model: The model to use for the request (default is the global modelname).
    - temperature: The temperature to use for the request (default is 0.7).
    - print_output: Whether to print the output (default is True).
    - Debug: Whether to enable debuging information(used tokens, duration) output (default is False).
    Returns:
    - The parsed response from the OpenAI API.
    Note:
    Even if Debug is False, debugging information is still logged to the log file.
    '''
    time.sleep(SLEEPTIME)  # Wait for 1 second before making the API call

    # system promptをmessagesの先頭に追加
    full_messages = [{"role": "developer", "content": system_prompt}] + messages
    if Debug:
        print("Prompt:")  
        pprint(full_messages)

    try:
        response = client.responses.parse(
            model=model,
            #input=full_messages,
            instructions= system_prompt,
            input = messages,
            text_format=format,
            temperature=temperature,
            max_output_tokens=max_tokens,
        )

        # print(f"Prompt: {full_messages}")
        logger.debug(f"""
                    Prompt: {full_messages}
                    Response: {response.output_text}
                    Prompt tokens: {response.usage.input_tokens}
                    Completion tokens: {response.usage.output_tokens}""")

        if print_output:
            if Debug:
                print(f"prompt_token: {response.usage.input_tokens}")
                print(f"completion_token: {response.usage.output_tokens}")
            print(json.loads(response.output_text))
        return json.loads(response.output_text)

    except Exception as e:
        print(f"Error calling OpenAI API: {e}\nBody: {getattr(e, 'response', None) and e.response.text}")


# 実行例
if __name__ == "__main__":
    result = Agent_chat(
        messages=[{"role": "user", "content": "Hello, how are you?"}],
        system_prompt="You are a helpful assistant.",
        stream=False,
        Debug=True
    )
    
    print(result)
    
    result = Agent_chat(
        messages=[{"role": "user", "content": "Hello, how are you?"}],
        system_prompt="You are a helpful assistant.",
        stream=True,
        Debug=True
    )
    
    for res in result:
        print(res, end="", flush=True)
    print("")

   
    print(f"===== turn ==============================")
    
    for i in range(1):
        result = Agent_chat_parsed(
            messages=[{"role": "user", "content": "Should I send a present to my girlfriend on her birthday?"}],
            system_prompt="You are a helpful assistant. You will request a advice from user. If you think user's message is reasonable and positive, 'go_next' should be True. Otherwise, it should be False and give the user some advices as 'instruct'.",
            temperature=0.7,
            format=JudgeAndInstruct,  # Use the JudgeAndInstruct model to format the response
        )

        
    # print(f"===== turn ==============================")
    # for i in range(1):
    #     result = Agent_chat_tools(
    #         messages=[{"role": "user", "content": "Should I send a present to my girlfriend on her birthday?"}],
    #         system_prompt="You are a helpful assistant. You will request a advice from user. If you think user's message is reasonable and positive, 'go_next' should be True. Otherwise, it should be False and give the user some advices as 'instruct'.",
    #         temperature=0.7,
    #     )


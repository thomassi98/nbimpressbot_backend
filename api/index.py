from flask import Flask, request, Response, stream_with_context
import os
from openai import OpenAI
import time
import io

app = Flask(__name__)

@app.route('/')
def home():
    return 'Hello, World!'

@app.route('/about')
def about():
    return 'About'

@app.route('/streamingTest', methods=['POST'])
def streamPrompt():
    # TODO: Implement streaming responses
    user_query = request.json.get('prompt')
    instructions = "Provide me with a Hello World"
    client = OpenAI(api_key=os.getenv('OPEN_AI_KEY'))

    @stream_with_context
    def generate():
        # response = client.chat.completions.create(
        #     model="gpt-4o",
        #     messages=[
        #         {"role": "system", "content": "You're working as a communications assistant for Norges Bank Investment Management (NBIM). Tasks include writing press releases following NBIM's format."},
        #         {"role": "user", "content": user_query}
        #         ],
        #     temperature=0,
        #     stream=True)
        # return response
        response = [
                {"choices": [{"delta": {"content": "Hello"}}]},
                {"choices": [{"delta": {"content": " "}}]},
                {"choices": [{"delta": {"content": "World"}}]},
                {"choices": [{"delta": {"content": "!"}}]},

        ]*100
        for chunk in response:
            content = chunk['choices'][0]['delta']["content"]
            time.sleep(0.005)
            print(content)
            yield 'data: ' + content + '\n\n'

    # generate()
    # return "Test"
    response = Response(generate(), mimetype="text/event-stream")

    return response
    # response = generate()
    # return str(response)

# TODO: Handle file upload
@app.route('/prompt', methods=['POST'])
def prompt():
    user_query = request.json.get('prompt')
    client = OpenAI(api_key=os.getenv('OPEN_AI_KEY'))
    instructions = "You're working as a communications assistant for Norges Bank Investment Management (NBIM). Tasks include writing press releases following NBIM's format. You should use the file as a context for your response, if present. Do your best to answer the users query"
    client = OpenAI(api_key=os.getenv('OPEN_AI_KEY'))


    @stream_with_context
    def generate():
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": instructions},
                {"role": "user", "content": user_query}
                ],
            temperature=0,
            stream=True,)

        for chunk in response:
            content = chunk.choices[0].delta.content
#            content = chunk['choices'][0]['delta']["content"]
            #time.sleep(0.5)
            print(content)
            if content:
                yield str(content)

    # generate()
    # return "Test"
    response = Response(generate(), content_type="text/plain_text")

    return response
    # response = generate()
    # return str(response)


# TODO: Handle file upload
@app.route('/prompt_file', methods=['POST'])
def prompt_file():
    # Debugging: Print the content type and request data
    print("Content-Type:", request.content_type)
    print("Request Data:", request.data)
    print("Request Form:", request.form)
    print("Request Files:", request.files)

    if 'file' in request.files:
        file = request.files['file']
        user_query = request.form.get('prompt')
        # Debugging: Print file details
        print("File received:", file.filename)
        print("User query:", user_query)
    else:
        file = None
        user_query = request.json.get('prompt')
        print("No file received")
        print("User query:", user_query)

    instructions = "You're working as a communications assistant for Norges Bank Investment Management (NBIM). Tasks include writing press releases following NBIM's format. If a file is present, use it as a context for your response."
    client = OpenAI(api_key=os.getenv('OPEN_AI_KEY'))
    assistant_id = os.getenv('ASSISTANT_ID')

    # Create thread
    thread = client.beta.threads.create()
    if file:
        # Read the file content into bytes
        file_content = file.read()
        file_name = file.filename
        file_stream = io.BytesIO(file_content)

        message_file = client.files.create(file=(file_name, file_stream), purpose="assistants")

    client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content=instructions,
        attachments=[{"file_id": message_file.id, "tools": [{"type": "file_search"}]}] if file else []
    )
    client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content=user_query
    )

    @stream_with_context
    def generate():
        # Create and run a new thread for the assistant
        run_response = client.beta.threads.runs.create_and_poll(
            thread_id=thread.id,
            assistant_id=assistant_id,
        )

        cancel_statuses = ["failed", "requires_action", "cancelled", "cancelling", "expired"]

        if run_response.status in cancel_statuses:
            print("Thread cancelled with status: " + run_response.status)
            yield "Thread cancelled with status: " + run_response.status
            return

        if run_response.status == 'completed': 
            messages = client.beta.threads.messages.list(
                thread_id=run_response.thread_id
            )
            for message in messages.data:
                for content_block in message.content:
                    if content_block.type == 'text':
                        yield content_block.text.value + "\n"
        else:
            print(run_response.status)
            yield "Thread not completed"

    return Response(generate(), content_type="text/plain_text")
# ... existing code ...



if __name__ == "__main__":
    app.debug = True
    app.run(threaded=True)
    # response = generate()
    # response = generate()
    # return str(response)


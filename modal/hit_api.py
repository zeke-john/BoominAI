import requests
import time

url = 'https://sumanyai--jubsterai-main.modal.run'
params = {
    'prompt': 'Drake type beat',
    'duration': 10,
    'extend_stride': 10,
    'temperature': 0
}

start_time = time.time()  # Record the start time
response = requests.get(url, params=params)
end_time = time.time()  # Record the end time

if response.status_code == 200:
    print("Request successful.")
    # Do something with the response, like print it
    print(response.json())
    print(f"Time taken: {end_time - start_time} seconds")
else:
    print(f"Error: {response.status_code}")
    print(f"Time taken: {end_time - start_time} seconds")
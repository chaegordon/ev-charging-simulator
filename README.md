# ev-charging-simulator
Agent based model of EV charging behaviour simulating plugged in % and SoC % at different times of day. Through this together for some fun, its by no means a "rigorous" simulation (current implimintations use of the std_mins in the index page is not rigorous). However the graphs look about right.

TODO:
1. Add agent based view.
2. Update Index page so have rigorous inputs.
3. Improve charging paths (i.e. more likely symmetric "there and back" events rather than uniform discharge).

## Usage - Poetry
1. Clone the repository
2. Install poetry (I recommend using "curl -sSL https://install.python-poetry.org | python3 -" rather than pipx)
3. Run `poetry install` in the root directory of the repository
4. To run the fastapi server, run `poetry run uvicorn main:app --reload`

## Usage - Docker
1. Clone the repository
2. Build the docker image with `docker build -t ev-charging-simulator .`
3. Run the docker container with `docker run -p 8000:8000 ev-charging-simulator`

## Once the server is running
1. Navigate to `http://localhost:8000/docs` to see the API documentation
2. the root endpoint is `http://localhost:8000/` and gives an input form to submit a simulation request, clicking Submit will redirect to the results page.

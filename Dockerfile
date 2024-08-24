FROM python:3.9

WORKDIR /app

RUN pip install poetry

COPY pyproject.toml pyproject.toml
COPY poetry.lock poetry.lock

RUN poetry install

COPY . .

# need --host to 0.0.0.0 to allow for connections from outside the container
# also need to port map 8000 to 8000 when running the container
CMD ["poetry", "run", "uvicorn", "main:app", "--reload", "--host", "0.0.0.0"]
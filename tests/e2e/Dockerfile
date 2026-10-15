FROM docker.io/python:3.12-slim
WORKDIR /tests
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# docker compose -f local.yml --profile tests run --rm e2e-runner   (see Makefile: make test-selenium)
CMD ["pytest", "-v", "--junitxml=/results/e2e-junit.xml"]

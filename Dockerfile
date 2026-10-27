FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir redis requests
COPY worker.py .
CMD ["python","-u","worker.py"]

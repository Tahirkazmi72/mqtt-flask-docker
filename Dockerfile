FROM python:3.10

WORKDIR /app
COPY app.py .
RUN pip install flask paho-mqtt

EXPOSE 5000
CMD ["python", "app.py"]

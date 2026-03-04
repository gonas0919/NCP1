FROM python:3.12-slim
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# 5. Flask가 기본으로 사용하는 5000번 포트 개방
EXPOSE 5000

# 6. 컨테이너가 켜지면 실행할 명령어
CMD ["python", "app.py"]
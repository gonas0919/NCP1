FROM python:3.12-slim

# 2. 컨테이너 내부 작업 폴더 설정
WORKDIR /app

# 3. 필요한 패키지 설치 (에러 방지 옵션 필요 없음!)
RUN pip install flask

# 4. 현재 폴더의 모든 파일(app.py, templates 등)을 컨테이너 안으로 복사
COPY . .

# 5. Flask가 기본으로 사용하는 5000번 포트 개방
EXPOSE 5000

# 6. 컨테이너가 켜지면 실행할 명령어
CMD ["python", "app.py"]
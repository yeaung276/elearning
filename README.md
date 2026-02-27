### Environment

- **Operating System:** macOS
- **Python Version:** >=3.12
- **Django version**: 6.0

### Online version

### Docker Installation
It is highly recommanded to run the entire stack using docker. I have already provided docker-compose.yaml and respective build file.
So, if you have the chance, use docker and run using `docker-compose up`.
### Manual Installation
1. Install the dependencies using `uv sync`. requirements.txt file is provided but `uv sync` is preferred.
2. Install ffmpeg, one of the the celery task use ffmpeg and whisper to transcribe video.
3. Install redis. `brew install redis`.
4. Run redis, `redix```
5. Run the celery worker. `uv run celery -A elearning worker --loglevel=info`
6. Run the django server. `uv run manage.py runserver`
7. Database file with mock data is provided so you don't need to run `uv run manage.py migrate`.

# Credentials
Student 1
username: student1
password: Password123!@#

Student 2
username: student2
password: Password123!@#

Student 3
username: student3
password: Password123!@#

Teacher 1
username: teacher1
password: Password123!@#

Teacher 2
username: teacher2
password: Password123!@#

Teacher 3
username: teacher3
password: Password123!@#

Admin
username: admin
password: admin
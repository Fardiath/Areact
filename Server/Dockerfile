FROM python:3.9

WORKDIR /app

COPY requirements.txt .

RUN pip install --upgrade pip

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN python djangoapps/manage.py makemigrations
RUN python djangoapps/manage.py  migrate

CMD ["python", "manage.py", "runserver"]

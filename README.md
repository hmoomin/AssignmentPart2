# **AssignmentPart2**
*Bristol Regional Food Network (case study from blackboard)*

# *What was required from assignment*
*A Dockerised Django + Django REST Framework (DRF) application using PostgreSQL.*

## Project Overview
This project runs as two containers:
* web-1 → Django backend (API + web server)
* db-1 → PostgreSQL database

Built and managed using Docker Compose.

## Tech Stack
* Python 3.11
* Django 5.0
* Django REST Framework
* PostgreSQL 15
* Docker / Docker Compose

## Full Setup Process 
These are the exact steps I used to create and run the containerised environment
> [!NOTE] 
> I did this via my VS Code terminal using a Macbook.

### 1. Create project directory
I used the terminal command:
'mkdir foodnetwork'

Then going into that created directory with:
'cd foodnetwork'

### 2. Create Python Requirements 
> [!IMPORTANT]
> Stay in the foodnetwork directory.

Now I need a requirements text doc, to do that I did:
'touch requirements.txt'

Then add:
'''
Django==5.0 
djangorestframework 
psycopg2-binary 
python-dotenv 
asgiref==3.7.2 
sqlparse==0.4.4 
stripe==5.0.0
'''

### 3. Create Django project
Once done and successful, I then created the project by:
'django-admin startproject backend'

### 4. Create Dockerfile
Now doing the same for the Dockerfile:
'touch Dockerfile'

Then add:
> [!WARNING]
> Each line should be entered one at a time to avoid any errors.

'''
FROM python:3.11
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "backend/manage.py", "runserver", "0.0.0.0:8000"]
'''

### 5. Create docker-compose.yml
Repeating the process for the .yml file:
'touch docker-compose.yml'

Then add:
'''
services:
  web:
    build: .
    command: sh -c "
      echo 'Waiting for database...' &&
      sleep 5 &&
      python backend/manage.py migrate &&
      python backend/manage.py runserver 0.0.0.0:8000
      "
    volumes:
      - .:/app
    ports:
      - "8000:8000"
    depends_on:
      - db

  db:
    image: postgres:15
    environment:
      POSTGRES_DB: fooddb
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    ports:
      - "5432:5432"
'''

### 6. Configure Django for PostgreSQL
Once done I went into the settings.py to update the Database:

'''
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'fooddb',
        'USER': 'postgres',
        'PASSWORD': 'postgres',
        'HOST': 'db',
        'PORT': 5432,
    }
}
''' 

> [!IMPORTANT]
> Host is db (service name), not localhost.

### 7. Build and start containers

> [!IMPORTANT]
> Make sure you're still in the foodnetwork directory.

Now it is time to build! I used the terminal command:
'docker-compose up --build'

#### What this does:

* Builds the web image
* Pulls PostgreSQL 15
* Starts containers (web-1, db-1)
* Runs migrations automatically

### 8. Verify containers
Once successful, check the containers are created:
'docker ps'

What you should see:
'''
foodnetwork-web-1
foodnetwork-db-1
'''

### 9. Access the application
The url links for the application:
* App: [http://localhost:8000](http://localhost:8000)
* Admin: [http://localhost:8000/admin](http://localhost:8000/admin)

### 10. Running the application
#### Quick Start
Put into the terminal:
'docker-compose up --build'

Then in the web browser open:
* In the search bar [http://localhost:8000](http://localhost:8000)

#### First time
If it is a first run or migrations didn't apply, put into the terminal:
'docker exec -it foodnetwork-web-1 python backend/manage.py migrate'

#### API (Django REST Framework)
Once DRF is installed and configured, endpoints follow standard REST patterns:

|Endpoint| Method| Description|
|--------|-------|------------|
|'/api/...'| GET | Retrieve data|
|'/api/...'| POST | Create data |
|'/api/.../<id>/'| PUT/PATCH | Update|
|'/api/.../<id>/'| DELETE | Remove|

#### Useful Commands I used
##### Stop containers
'docker-compose down'

##### Rebuild containers
'docker-compose up --build'

##### Run migrations manually
'docker exec -it foodnetwork-web-1 python backend/manage.py migrate'

##### Create superuser
'docker exec -it foodnetwork-web-1 python backend/manage.py createsuperuser'

##### Open Django shell
'docker exec -it foodnetwork-web-1 python backend/manage.py shell'

> [!NOTE]
> The sleep 5 ensures Postgres starts before Django connects
> Volumes sync your code live into the container

##### Ports:
* 8000 → Django
* 5432 → PostgreSQL

##### Features
* Fully containerised backend
* PostgreSQL integration
* Django REST Framework ready
* Auto migrations on startup
* Persistent development environment
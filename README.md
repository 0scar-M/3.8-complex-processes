# 3.8-complex-processes

My submission for the NCEA Level 3 3.8 Complex Processes assessment.

**Project Title**: Web Media Converter

**Project Description**: A web app that converts media files into different formats.

Hosted on DigitalOcean at http://170.64.162.244/

To run project, create docker-compose.yml file and paste in the yaml code below. Then run ```docker compose up```.

## docker-compose.yml for running application
```yml
services:
  frontend:
    image: 21omccartney/3.8—complex—processes:frontend
    ports:
      - "80:80"
    depends_on:
      - backend

  backend:
    image: 21omccartney/3.8—complex—processes:backend
    volumes:
      - db_volume:/data
    ports:
      - "5000:5000"
    environment:
      - DATABASE_PATH=/data/database.db
      - HOST_NAME=170.64.162.244
    depends_on:
      - database
  
  database:
    image: 21omccartney/3.8—complex—processes:database
    volumes:
      - db_volume:/data

volumes:
  db_volume:
```

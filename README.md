# 3.8-complex-processes

My submission for the NCEA Level 3 3.8 Complex Processes assessment.

**Project Title**: Web Media Converter

**Project Description**: A web app that converts media files into different formats.

Hosted on DigitalOcean at http://170.64.162.244/

To run the project, firstly install [Docker Desktop](https://www.docker.com/products/docker-desktop/).
Next, create a docker-compose.yml file and paste in the yaml code below. 
Then, in the directory of the docker-compose.yml file, run ```docker compose up```. 
The app will then be available on local port 80, and you will be able to view it at http://localhost/.

## ```docker-compose.yml``` file for running application on local machine:
```yml
services:
  frontend:
    image: 21omccartney/3.8-complex-processes:frontend
    ports:
      - "80:80"
    depends_on:
      - backend

  backend:
    image: 21omccartney/3.8-complex-processes:backend
    volumes:
      - db_volume:/data
    ports:
      - "5000:5000"
    environment:
      - DATABASE_PATH=/data/database.db
      - HOST_NAME=localhost
    depends_on:
      - database
  
  database:
    image: 21omccartney/3.8-complex-processes:database
    volumes:
      - db_volume:/data

volumes:
  db_volume:
```

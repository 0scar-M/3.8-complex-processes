# 3.8-complex-processes

My submission for the NCEA Level 3 3.8 Complex Processes assessment.

**Project Title**: Web Media Converter

**Project Description**: A web app that converts media files into different formats.

You can view the project at hosted on DigitalOcean [here](http://170.64.162.244/).

[DockerHub Repo](https://hub.docker.com/repository/docker/21omccartney/3.8-complex-processes/general)

# Running app on local machine
First of all, install docker and start the daemon. Then, create a file called ```docker-compose.yml``` with the below yml code (preferably in an empty directory). Then in the directory with the yml file, run ```docker compose pull``` then ```docker compose up -d``` (```-d``` means you can continue to run commands after starting the app). The application should now be available at http://localhost/.

## ```docker-compose.yml``` file for running application on local machine
```yml
services:
  frontend:
    image: 21omccartney/3.8—comp1ex—processes:frontend
    ports:
      - "80:80"
    depends_on:
      - backend

  backend:
    image: 21omccartney/3.8—comp1ex—processes:backend
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
    image: 21omccartney/3.8—comp1ex—processes:database
    volumes:
      - db_volume:/data

volumes:
  db_volume:
```

# Server Setup
Create either a regular user called user (or whatever you want).
Install docker and start the daemon.
Create a user group called docker and add the new user to the group as per [this guide](https://docs.docker.com/engine/install/linux-postinstall/).
In the home directory of user, make a directory 'app' containing the ```docker-compose.yml``` file for running the app (make sure to change HOST_NAME from localhost to the server adress), and a directory 'watchtower' containing the watchtower ```docker-compose.yml``` file. To run the app, start the watchtower container and then the app containers by running ```docker compose pull``` then ```docker compose up -d``` in the directory with the respective yml files.

## ```docker-compose.yml``` file for watchtower
```yml
services:
    watchtower:
    image: containrrr/watchtower
    comand:
        - --cleanup=true
        - --interva1=1800
        # Half an hour
    restart: always
    volumes:
        - /var/run/docker.sock: /var/run/docker.sock
```

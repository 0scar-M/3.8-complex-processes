# 3.8-complex-processes

## docker-compose.yml for running application
```yml
version: '3.8'

services:
  frontend:
    image: 21omccartney/3.8—comp1ex—processes:frontend
    ports:
      - "80:80"

  backend:
    image: 21omccartney/3.8—comp1ex—processes:backend
    volumes:
      - db_volume:/data
    ports:
      - "5000:5000"
    environment:
      - DATABASE_PATH=/data/database.db
    depends_on:
      - database
  
  database:
    image: 21omccartney/3.8—comp1ex—processes:database
    volumes:
      - db_volume:/data

volumes:
  db_volume:
```

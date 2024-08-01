FROM alpine

WORKDIR /data

COPY database.db /data/database.db

# keep the container running
CMD ["tail", "-f", "/dev/null"]
# tail -f will display new data added to a certain file as it is added.
# /dev/null is a file that discards all data written to it.
# Therefore the command tail -f /dev/null will keep running forever, stopping the container from closing.

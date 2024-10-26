### TODO

## IMPORTANT

- Actually check if the torrents have all the pieces available
        - Make a queue system and only start downloading when all pieces are avaiable

- Make announce not once work with http but with udp and/or wss
        - Maybe make an object storing all working announce links (this is important incase all peers in a tracker dont work)

- GUI ofc


## LESS IMPORTANT

- Get multithreading working
    - Or use python select to send reqs which mimicks it
- Make sure the ping command works on a windows computer
- Put everything in a docker container
- More exception handling
- More testing
    
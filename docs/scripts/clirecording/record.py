#!/usr/bin/env python3
import screenplays
from clidirector import CliDirector

if __name__ == "__main__":
    director = CliDirector()
    screenplays.record_user_interface(director)
    screenplays.record_intercept_requests(director)
    screenplays.record_modify_requests(director)
    screenplays.record_replay_requests(director)

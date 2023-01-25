#!/bin/bash

celery -A satpy_pygeoapi_plugin worker --loglevel=DEBUG -E
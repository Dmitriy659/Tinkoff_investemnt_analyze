#!/bin/bash
black --line-length 120 .
isort --profile black --line-length 120 .

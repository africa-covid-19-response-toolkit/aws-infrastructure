FROM python:3.8

RUN mkdir -p /stacks
WORKDIR /stacks
COPY setup.py /stacks

RUN python setup.py install

COPY . /stacks

RUN python setup.py install > /dev/null

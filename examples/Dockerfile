FROM python:3.9


COPY examples/requirements.txt /
RUN python -m pip install -r /requirements.txt

COPY examples/main.py /main.py
COPY intercept /intercept

ENV PYTHONPATH=/intercept:

RUN python -c "import intercept"
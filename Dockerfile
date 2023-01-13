
# use python 3.10.8

FROM python:3.10.8

# set working directory

WORKDIR /bot

# copy requirements.txt to working directory

COPY deps.txt ./

# install dependencies

RUN pip install -r deps.txt

# copy all files to working directory

COPY . .

# run bot

CMD ["python", "-m", "bot"]


# set working directory

WORKDIR /bot

# copy requirements.txt to working directory

COPY requirements.txt ./

# install dependencies

RUN pip install -r requirements.txt

# copy all files to working directory

COPY . .

# run bot

CMD ["python", "-m", "bot"]
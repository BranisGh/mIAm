# Use the official Python image as a base
FROM python:3.9-slim

# Set the working directory
WORKDIR /app

# Copy the necessary files
COPY . .

# Install
RUN pip3 install -r requirements.txt 

# Expose the port that Streamlit runs on
EXPOSE 8501

# Set the command to run the Streamlit app
CMD ["streamlit", "run", "src/mIAm/app/app.py", "--server.port=8501", "--server.address=0.0.0.0"]

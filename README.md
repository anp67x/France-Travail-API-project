# Job Market Data Analysis Using the France Travail API

## Authors: PACCHIONI Antoine, ROMANENKO German
- Program: M1 DS2E, University of Strasbourg
- Academic year: 2025–2026


## Overview
This project collects job offers related to the data sector (e.g., data analyst, data scientist, data engineer) from the France Travail public API.  
The pipeline retrieves the offers, extracts relevant information (title, location, contract type, salary when available), and exports structured CSV and JSON files for analysis.  
A local web interface is provided to run the pipeline and download the generated datasets.


## API Credentials
To access the France Travail API, users must create a `.env` file in the project root directory and provide their own API credentials (`CLIENT_ID` and `CLIENT_SECRET`).
For confidentiality and security reasons, the `.env` file is not included in this repository.

Example structure of the `.env` file:
CLIENT_ID=your_client_id_here  
CLIENT_SECRET=your_client_secret_here

## How it works

The project is organized into several Python files, each with a specific role:
- `main.py`  
  Runs the whole pipeline. It connects to the API, retrieves the job offers, processes the data, and saves the final files.
  It must be executed before running the descriptive analysis separately.
- `acces_token.py`  
  Handles authentication with the France Travail API and generates the access token.
- `prepare_data.py`  
  Selects the relevant information from the API response and structures it into a usable dataset.
- `extract_salary.py`  
  Extracts salary information from the offers and converts it into a comparable format when possible.
- `analyse_descriptive.py`  
  Produces simple descriptive statistics from the final dataset.
  Run it to display descriptive statistics.
- `.env`  
  Stores the API credentials (not included in the repository for security reasons).
- `webapp.py`  
  Provides a simple local web interface to run the pipeline and download the generated files.
  It is explained below how to run this file.

## Example Output Files

The CSV files included in this repository are pre-generated example outputs.
They allow the project (and the descriptive analysis module) to run even if no API credentials are provided.

## How to run the local web interface (important steps)

1. Install the required Python packages:

pip install flask  
pip install requests  
pip install pandas  
pip install python-dotenv  

2. Create a `.env` file in the project root directory and add your API credentials:

CLIENT_ID=your_client_id  
CLIENT_SECRET=your_client_secret  

3. Run the application:

python webapp.py  

4. Open your browser and go to:

http://127.0.0.1:5000

## Ethical Considerations
The project uses publicly available data provided by the official France Travail API.
No personal or sensitive data is collected beyond what is publicly accessible through the API.
API credentials are stored locally and are not shared in this repository.




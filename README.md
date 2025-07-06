# AI Company Information Crawler

This Python-based crawler uses AI to extract company information from websites. It processes a CSV file containing company names and websites, and uses an AI server to extract detailed information about each company.

## Features

- Asynchronous web crawling for better performance
- AI-powered information extraction
- Configurable AI server connection
- Progress tracking and logging
- CSV input/output handling
- Error handling and retry mechanisms
- User agent rotation for better crawling success

## Requirements

- Python 3.8 or higher
- Windows or Linux operating system (tested on Ubuntu 20.04 LTS)
- Access to an AI server (configurable)

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd ArkAIScrape
```

2. Create a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Linux
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Directory Structure

```
ArkAIScrape/
├── ai_server.py       # AI Server Configuration
├── run.py             # Main crawler script
├── webapp.py          # Web app script
├── requirements.txt   # Python dependencies
└── output/            # Generated output files
```

## Usage

1. Prepare your input CSV file with at least these columns:
   - Company Name (One of 'Company', 'Company Name', 'company', 'company_name', 'CompanyName', 'COMPANY')
   - Website (One of 'Website', 'website', 'URL', 'url', 'Web Site', 'Company Website', 'WEBSITE')

2. Run the crawler:
```bash
python run.py <your_input_file.csv>
```

Replace `<your_input_file.csv>` with the path to your input CSV file. The base name of this file will be used in the output filenames.

The script will:
- Verify the AI server connection
- Process each company in the input CSV
- Generate two new CSVs (success and failure) with additional information
- Create logs in the `logs` directory

## Output

After running the script, two CSV files will be generated in the `output/` directory:

1.  **Success File**: Contains records where information was successfully extracted or a website was found via search. Named as `yourInputFileName-success-YYYYMMDDHHMMSS.csv`.
2.  **Failure File**: Contains records where the website could not be fetched or AI processing failed. Named as `yourInputFileName-failure-YYYYMMDDHHMMSS.csv`.

Both output CSVs will contain the following columns:
- Company Name
- Website
- Phone Number
- Street Address
- City
- State
- Zip Code
- Facebook Page
- Facebook Page Name
- Facebook Likes
- Facebook About
- LinkedIn Page
- Public Email
- Contact Person
- Processing Time (seconds)
- Status
- Last Updated

## Status Codes

- Success: Information successfully extracted
- No Website: Company has no website listed
- Failed to Fetch: Could not access the website
- AI Processing Failed: AI server could not process the data
- Error: Other errors occurred during processing
- Pending: Initial state

## Contributing

Feel free to submit issues and enhancement requests!

## License

[Your chosen license] 
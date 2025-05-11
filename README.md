# Ticket Annotation Tool

A web application for annotating customer support tickets to identify in-app technical issues.

## Features

- Dashboard with summary statistics and filtering
- Interactive annotation interface
- Google OAuth authentication with company domain restriction
- Data visualization with Plotly.js
- Filtering by category and date
- Tracking of annotation history

## Requirements

- Python 3.8+
- Flask and extensions
- Pandas for data processing
- Plotly for data visualization
- SQLite database

## Installation

1. Clone the repository:
   ```
   git clone <repository-url>
   cd annotation_tool
   ```

2. Create and activate a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Set up environment variables:
   Create a `.env` file in the project root with the following variables:
   ```
   SECRET_KEY=your-secret-key
   GOOGLE_CLIENT_ID=your-google-client-id
   GOOGLE_CLIENT_SECRET=your-google-client-secret
   COMPANY_DOMAIN=your-company-domain.com
   ```

## Google OAuth Setup

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project
3. Configure the OAuth consent screen:
   - Set the User Type to "Internal" (for company users only)
   - Add the required scopes (email, profile)
4. Create OAuth client ID credentials:
   - Application type: Web application
   - Authorized JavaScript origins: `http://localhost:5000`
   - Authorized redirect URIs: `http://localhost:5000/auth/callback`
5. Copy the Client ID and Client Secret to your `.env` file

## Database Setup

The application will automatically create the database tables when it first runs. To load sample data:

1. Ensure your JSON file is in the correct format and placed in the `data/` directory
2. Log in as an admin user (email starting with "admin@")
3. Click the "Load Sample Data" button on the dashboard

## Running the Application

1. Start the Flask development server:
   ```
   python run.py
   ```

2. Access the application at `http://localhost:5000`

## Project Structure

```
annotation_tool/
├── app/                      # Application package
│   ├── auth/                 # Authentication module
│   ├── main/                 # Main application module
│   ├── models/               # Database models
│   ├── static/               # Static files (CSS, JS)
│   └── templates/            # HTML templates
├── data/                     # Data files
├── instance/                 # Instance-specific files
├── migrations/               # Database migrations
├── config.py                 # Configuration
├── requirements.txt          # Dependencies
└── run.py                    # Application entry point
```

## Usage

1. Log in with your company Google account
2. View the dashboard to see annotation statistics
3. Filter by category and date range
4. Click on numbers in the summary table to start annotating tickets
5. For each ticket, decide if it's an in-app technical issue
6. Optionally provide a rationale for your decision
7. Navigate through tickets using the skip and submit buttons

## License

[MIT License](LICENSE)
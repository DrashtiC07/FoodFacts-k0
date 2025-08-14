# Food Facts Scanner

A Django web application for scanning food product barcodes and retrieving nutritional information.

## Features

- **Barcode Scanning**: Upload images or enter barcodes manually
- **Product Information**: Detailed nutrition facts, ingredients, and health scores
- **User Accounts**: Registration, login, and personalized dashboards
- **Favorites & Reviews**: Save favorite products and write reviews
- **Search**: Find products by name, brand, or barcode
- **Responsive Design**: Works on desktop and mobile devices
- **Dark/Light Theme**: Toggle between themes

## Installation

1. **Clone the repository**
\`\`\`bash
git clone <repository-url>
cd foodfacts
\`\`\`

2. **Create virtual environment**
\`\`\`bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
\`\`\`

3. **Install dependencies**
\`\`\`bash
pip install -r requirements.txt
\`\`\`

4. **Configure Tesseract** (for OCR functionality)
- Download and install Tesseract OCR
- Update the path in `scanner/views.py` if needed

5. **Run migrations**
\`\`\`bash
python manage.py makemigrations
python manage.py migrate
\`\`\`

6. **Create superuser**
\`\`\`bash
python manage.py createsuperuser
\`\`\`

7. **Run the development server**
\`\`\`bash
python manage.py runserver
\`\`\`

## Usage

1. **Register/Login**: Create an account or login
2. **Scan Products**: Use the scan page to upload barcode images or enter manually
3. **View Details**: See detailed product information, nutrition facts, and reviews
4. **Dashboard**: Track your scan history, favorites, and dietary goals
5. **Search**: Find products in the database

## API Integration

The application integrates with:
- **OpenFoodFacts API**: Primary source for product data
- **BarcodeLookup API**: Secondary source (requires API key)
- **UPC Database API**: Tertiary source

## Technologies Used

- **Backend**: Django 4.2+
- **Frontend**: Bootstrap 5, HTML5, CSS3, JavaScript
- **Database**: SQLite (default)
- **Image Processing**: OpenCV, PIL
- **OCR**: Tesseract, pyzbar
- **APIs**: OpenFoodFacts, BarcodeLookup, UPC Database

## Project Structure

\`\`\`
foodfacts/
├── accounts/           # User management app
├── scanner/           # Product scanning app
├── static/           # Static files (CSS, JS, images)
├── templates/        # HTML templates
├── media/           # User uploaded files
└── manage.py        # Django management script
\`\`\`

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

This project is licensed under the MIT License.

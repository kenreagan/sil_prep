# E-commerce Customer Order API

A Django REST Framework-based e-commerce API system that manages customers, hierarchical product categories, products, and orders with integrated authentication, SMS notifications, and email alerts.

## 🚀 Live Demo

The API is currently hosted and accessible at: **http://207.244.235.227:9000**

## 📋 Features

- **Customer Management**: Registration, authentication, and profile management
- **Hierarchical Categories**: Arbitrary depth category trees for product organization
- **Product Management**: CRUD operations with category associations and search functionality
- **Order Processing**: Complete order management with item tracking
- **Authentication**: 
  - Django Token Authentication
  - OpenID Connect (OIDC) integration
- **Notifications**: 
  - SMS alerts via Africa's Talking gateway
  - Email notifications to administrators
- **Advanced Queries**: Category-based price averaging and order statistics

## 🏗️ Architecture

### Database Models

- **Customer**: Extended Django User model with additional profile fields
- **Category**: Hierarchical category structure with parent-child relationships
- **Product**: Products linked to categories with pricing and inventory
- **Order**: Customer orders with status tracking
- **OrderItem**: Individual items within orders

### Authentication Methods

1. **Token Authentication**: Traditional Django token-based auth
2. **OpenID Connect**: OAuth2/OIDC integration for modern authentication

## 📡 API Endpoints

### Authentication
```
POST /auth/login/                    # Login with username/password
POST /auth/oidc-login/              # OpenID Connect login
```

### Customer Management
```
POST /api/v1/customers/register/            # Customer registration
GET  /api/v1/customers/profile/            # Get customer profile
PUT  /api/v1/customers/profile/            # Update customer profile
```

### Categories
```
GET  /api/v1/categories/                   # List categories (with filtering)
POST /api/v1/categories/                   # Create new category
GET  /api/v1/categories/{id}/              # Get specific category
PUT  /api/v1/categories/{id}/              # Update category
DELETE /api/v1/categories/{id}/            # Delete category
GET  /api/v1/categories/tree/              # Get complete category tree
GET  /api/v1/categories/{id}/average-price/ # Get average price for category
```

### Products
```
GET  /api/v1/products/                     # List products (with search & filtering)
POST /api/v1/products/                     # Create new product
GET  /api/v1/products/{id}/                # Get specific product
PUT  /api/v1/products/{id}/                # Update product
DELETE /api/v1/products/{id}/              # Delete product
```

### Orders
```
GET  /api/v1/orders/                       # List customer orders
POST /api/v1/orders/                       # Create new order
GET  /api/v1/orders/{id}/                  # Get specific order
GET  /api/v1/orders/statistics/            # Get order statistics
```

## 🔧 Key Features

### Hierarchical Categories
Categories support arbitrary depth nesting, allowing complex product organization:
```
All Products
├── Electronics
│   ├── Computers
│   │   ├── Laptops
│   │   └── Desktops
│   └── Mobile Phones
└── Clothing
    ├── Men's Wear
    └── Women's Wear
```

### Smart Filtering
- **Category Filtering**: Products can be filtered by category (includes subcategories)
- **Search**: Full-text search across product names, descriptions, and SKUs
- **Parent/Child Navigation**: Easy category tree navigation

### Order Processing
When an order is placed:
1. **Validation**: Product availability and pricing verification
2. **Calculation**: Automatic total calculation
3. **Creation**: Order and order items creation
4. **Notifications**: 
   - SMS to customer via Africa's Talking
   - Email notification to administrator

### Price Analytics
Get comprehensive pricing statistics for any category:
- Average price across all products in category and subcategories
- Total product count
- Total inventory value

## 🛠️ Technology Stack

- **Backend**: Django 4.x + Django REST Framework
- **Database**: PostgreSQL (production) / SQLite (development)
- **Authentication**: Django Token Auth + OpenID Connect
- **SMS Service**: Africa's Talking API
- **Email**: Django Email Backend
- **Deployment**: Docker + Kubernetes

## 🔐 Authentication

### Token Authentication
```bash
# Login to get token
curl -X POST http://207.244.235.227:9000/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "your_username", "password": "your_password"}'

# Use token in subsequent requests
curl -H "Authorization: Token your_token_here" \
  http://207.244.235.227:9000/api/v1/products/
```

### OpenID Connect
```bash
# Get OIDC token
curl -X POST http://207.244.235.227:9000/auth/oidc-login/

# Use Bearer token
curl -H "Authorization: Bearer your_access_token" \
  http://207.244.235.227:9000/api/v1/products/
```

## 📊 Example Usage

### Create a Category
```bash
curl -X POST http://207.244.235.227:9000/api/v1/categories/ \
  -H "Authorization: Token your_token" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Electronics",
    "description": "Electronic products and gadgets",
    "slug": "electronics"
  }'
```

### Add a Product
```bash
curl -X POST http://207.244.235.227:9000/api/v1/products/ \
  -H "Authorization: Token your_token" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Laptop",
    "description": "High-performance laptop",
    "price": "999.99",
    "sku": "LAP001",
    "category": "category_uuid_here",
    "stock_quantity": 10
  }'
```

### Place an Order
```bash
curl -X POST http://207.244.235.227:9000/api/v1/orders/ \
  -H "Authorization: Token your_token" \
  -H "Content-Type: application/json" \
  -d '{
    "shipping_address": "123 Main St, Nairobi, Kenya",
    "notes": "Please handle with care",
    "items": [
      {
        "product_id": "product_uuid_here",
        "quantity": 2
      }
    ]
  }'
```

### Get Category Price Analytics
```bash
curl -H "Authorization: Token your_token" \
  http://207.244.235.227:9000/api/v1/categories/{category_id}/average-price/
```

## 🔍 Query Parameters

### Products
- `category`: Filter by category ID (includes subcategories)
- `search`: Search in name, description, or SKU

### Categories  
- `parent`: Filter by parent category ID

## 📧 Notifications

### SMS Notifications
- Sent to customers when orders are placed
- Uses Africa's Talking SMS gateway
- Includes order number and total amount

### Email Notifications
- Sent to administrators for new orders
- Contains complete order details including:
  - Customer information
  - Order items with pricing
  - Shipping address
  - Order status

## 🏃‍♂️ Getting Started

### Prerequisites
- Python 3.8+
- PostgreSQL
- Africa's Talking API credentials (for SMS)
- SMTP settings (for email)

### Quick Start
1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Configure environment variables
4. Run migrations: `python manage.py migrate`
5. Create superuser: `python manage.py createsuperuser`
6. Start server: `python manage.py runserver`

### Environment Variables
```bash
SECRET_KEY=your_secret_key
DATABASE_URL=postgresql://user:password@localhost/dbname
AFRICAS_TALKING_API_KEY=your_api_key
AFRICAS_TALKING_USERNAME=your_username
ADMIN_EMAIL=admin@example.com
OIDC_CLIENT_ID=your_oidc_client_id
OIDC_CLIENT_SECRET=your_oidc_client_secret
OIDC_TOKEN_URL=your_token_url
OIDC_INTROSPECT_URL=your_introspect_url
```

## 🧪 Testing

The project includes comprehensive test coverage for:
- Model relationships and methods
- API endpoints and permissions
- Authentication flows
- Business logic validation

Run tests with:
```bash
python manage.py test
coverage run --source='.' manage.py test
coverage report
```

## 🚢 Deployment

The application is containerized and deployed using:
- **Docker**: For containerization
- **Kubernetes**: For orchestration and scaling
- **PostgreSQL**: Production database

## 📝 API Response Formats

### Success Response
```json
{
  "id": "uuid-here",
  "name": "Product Name",
  "price": "99.99",
  "category": {
    "id": "uuid-here",
    "name": "Category Name"
  }
}
```

### Error Response
```json
{
  "error": "Error message here",
  "details": {
    "field": ["Specific field error"]
  }
}
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## 📄 License

This project is developed as part of the Savannah Informatics Backend Engineer Assessment.

---

**Live API Base URL**: http://207.244.235.227:9000

For questions or support, please refer to the API documentation or contact the development team.
# Steps Bot — Telegram Bot for Step Tracking and Rewards

keys:
start_welcome - Стартовое сообщение
main_menu - Меню
promo_intro - это на промокоды
walk_choice - это после нажатия "Начать прогулку"

## Overview

**Steps Bot** is a Telegram bot application for tracking user activity (steps/walks), managing rewards, promo codes, families/groups, and orders. The bot integrates with a Django admin panel for content management and provides administrative REST APIs for managing pickup points (ПВЗ) and retrieving order data.

### Key Features

- 👥 **User Registration & Profiles**: Registration, balance tracking, family/group management
- 🚶 **Activity Tracking**: Walk tracking with temperature coefficients, form-based logging
- 💰 **Reward System**: Promo codes, balance management, proportional family rewards
- 🛒 **Order Catalog**: Product catalog with categories, pricing in points
- 📦 **Local PVZ Management**: Local pickup points database (instead of CDEK API)
- 📊 **Admin API**: REST endpoints for PVZ management and order retrieval
- 💬 **Broadcasts**: Scheduled notifications and rele messages
- 🤝 **Referral System**: User referral tracking and rewards

---

## Architecture

```
steps_bot/
├── db/                 # Database layer
│   ├── models/         # SQLAlchemy models
│   ├── repo.py         # Repository functions (queries)
│   └── session.py      # Async DB session setup
├── handlers/           # Telegram message handlers
├── services/           # Business logic
├── states/             # Finite state machine (FSM) states
├── presentation/       # UI (keyboards, commands)
├── api/                # FastAPI admin endpoints
└── settings.py         # Configuration

app/admin/              # Django admin panel
├── core/               # Models & admin interface
└── settings.py         # Django settings
```

**Key Patterns:**
- **Service Layer**: Business logic in `services/*.py`
- **Repository Pattern**: Data access via `db/repo.py`
- **FSM**: User flows with states in `states/`
- **Thin Handlers**: Request routing, minimal logic

---

## Technology Stack

- **Python 3.11+**
- **Poetry**: Dependency management
- **aiogram 3.x**: Telegram bot framework
- **FastAPI**: Admin REST API
- **SQLAlchemy 2.x**: ORM with async support
- **PostgreSQL**: Database (asyncpg driver)
- **Alembic**: Database migrations
- **Django 5.x**: Admin panel (separate)
- **Docker Compose**: Local development environment

---

## Local Setup

### Prerequisites

- Python 3.11+
- PostgreSQL (via Docker)
- Poetry

### Installation

1. **Clone the repository and navigate to project root**
   ```bash
   cd steps_bot
   ```

2. **Install dependencies**
   ```bash
   poetry install
   ```

3. **Copy `.env.example` to `.env` and configure**
   ```bash
   cp .env.example .env
   ```
   
   **Required environment variables:**
   ```env
   # Bot & Webhook
   BOT_TOKEN=your_telegram_bot_token_here
   WEBHOOK_URL=https://your-domain.com/webhook

   # Database
   POSTGRES_HOST=localhost
   POSTGRES_PORT=5432
   POSTGRES_USER=steps_bot
   POSTGRES_PASSWORD=your_secure_password
   POSTGRES_DB=steps_bot

   # Admin API
   API_KEY=your_secret_api_key_here

   # Optional: CDEK integration (kept for reference, not used for PVZ)
   CDEK_ACCOUNT=your_account
   CDEK_SECURE=your_secure
   CDEK_FROM_CITY_CODE=298  # Moscow code
   MEDIA_ROOT=/app/media
   ```

4. **Start PostgreSQL via Docker Compose**
   ```bash
   docker-compose up -d postgres
   ```

5. **Apply migrations**
   ```bash
   alembic upgrade head
   ```

6. **Run the bot** (polling mode)
   ```bash
   python -m app.steps_bot.main
   ```

   Or **FastAPI admin API** (in another terminal)
   ```bash
   uvicorn app.steps_bot.api.admin:app --reload --host 0.0.0.0 --port 8000
   ```

7. **Django admin panel** (optional)
   ```bash
   cd app/admin
   python manage.py runserver 0.0.0.0:8001
   ```

---

## Admin API Documentation

### Authentication

All endpoints require `API_Key` header:
```bash
-H "API_Key: your_secret_api_key_here"
```

### POST `/pvz` — Replace PVZ List

**Description**: Replace entire PVZ list in database with new data.

**Request**:
```bash
curl -X POST http://localhost:8000/pvz \
  -H "API_Key: your_secret_api_key" \
  -H "Content-Type: application/json" \
  -d '[
    {
      "id": "019620d8987e745880fb93a122b7da44",
      "full_address": "Москва Ленинградский проспект 75 к1А"
    },
    {
      "id": "01999b820a3477899acb908629c78962",
      "full_address": "Москва Большая Черкизовская улица 3 к1"
    },
    {
      "id": "0199b9d0a69b77a09018951faeb4697d",
      "full_address": "Москва Варшавское шоссе 168"
    }
  ]'
```

**Response** (200 OK):
```json
{
  "success": true,
  "count": 3,
  "message": "Successfully saved 3 PVZ items"
}
```

### GET `/order/{date_range}` — Get Orders by Date Range

**Description**: Retrieve orders for a specified date range.

**Path Parameter**:
- `date_range`: Two ISO dates separated by hyphen in format `YYYY-MM-DD-YYYY-MM-DD`
- Example: `2025-10-01-2025-10-17`

**Request**:
```bash
curl -X GET "http://localhost:8000/order/2025-10-01-2025-10-17" \
  -H "API_Key: your_secret_api_key"
```

**Response** (200 OK):
```json
[
  {
    "first_name": "Иван",
    "last_name": "Петров",
    "phone": "+79991234567",
    "email": "ivan@example.com",
    "pvz_id": "019620d8987e745880fb93a122b7da44",
    "order_id": "1",
    "created_at": "2025-10-05T14:30:22.123456+00:00",
    "product_code": "1"
  },
  {
    "first_name": "Мария",
    "last_name": "Сидорова",
    "phone": "+79991234568",
    "email": "",
    "pvz_id": "01999b820a3477899acb908629c78962",
    "order_id": "2",
    "created_at": "2025-10-06T10:15:45.654321+00:00",
    "product_code": "2"
  }
]
```

**Error Responses**:
- `400 Bad Request`: Invalid date format
- `401 Unauthorized`: Missing API_Key header
- `403 Forbidden`: Invalid API_Key
- `500 Internal Server Error`: Database error

---

## Running Tests

### Setup Test Environment

```bash
# Tests require pytest and test database setup
poetry add --group dev pytest pytest-asyncio httpx
```

### Run All Tests

```bash
pytest -v
```

### Run Specific Test Modules

```bash
# API tests
pytest tests/test_api_pvz.py -v
pytest tests/test_api_orders.py -v

# Integration tests
pytest tests/test_bot_integration.py -v
```

---

## Database Migrations

### Create New Migration

```bash
alembic revision --autogenerate -m "description of changes"
```

### Apply Migrations

```bash
alembic upgrade head
```

### Rollback Last Migration

```bash
alembic downgrade -1
```

### View Migration History

```bash
alembic history
```

---

## Django Admin Panel

Navigate to `http://localhost:8001/admin/` after running Django development server.

### Available Sections

- **Users**: User management, balance, roles
- **Families**: Family groups, invitations, balance
- **Products**: Catalog items, categories, pricing
- **Orders**: Order history, status tracking
- **PVZ**: Pickup points (add/edit/delete manually)
- **Promo Groups**: Discount groups and promo codes
- **Broadcasts**: Scheduled messages
- **Settings**: Bot configuration

---

## Bot User Flow

### Order/Purchase Flow

1. User starts bot → `/start`
2. Views catalog → `/catalog`
3. Selects product → enters purchase flow
4. Chooses PVZ delivery
5. Enters city → bot queries local PVZ database
6. Selects pickup point from list
7. Enters recipient details (name, phone)
8. Confirms order
9. **Final Message** (exact):
   ```
   Спасибо за участие в игре! 
   🎁 Как идет Ваш подарок можно увидеть по ссылке, которую Яндекс выслал в смс.
   ```

### PVZ Selection

- Bot queries `get_pvz_by_city(session, city)` from local database
- Shows buttons with `full_address` from PVZ records
- If no PVZ found for city: "К сожалению нет доступных ПВЗ по указанному адресу."

---

## Deployment

### Docker Compose (All Services)

```bash
docker-compose up -d
```

This runs:
- PostgreSQL database
- Bot (polling mode)
- FastAPI admin API

### Production Considerations

- Use webhook instead of polling for bot (set `WEBHOOK_URL` in `.env`)
- Configure environment variables in production environment
- Use environment secrets manager (e.g., AWS Secrets Manager, HashiCorp Vault)
- Enable HTTPS for webhook URL
- Monitor database performance and logs
- Set up CI/CD pipeline for migrations and deployments

---

## API_KEY Management

The `API_KEY` environment variable protects all admin endpoints. Rotate regularly:

```bash
# Generate new secure key
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Update in .env and restart services
API_KEY=newly_generated_key
```

---

## Troubleshooting

### Bot doesn't start
- Check `BOT_TOKEN` is valid
- Verify PostgreSQL is running: `docker ps`
- Check logs: `docker-compose logs steps_bot`

### PVZ not showing in bot
- Verify PVZ records exist: Check Django admin or direct DB query
- Check city name matching (uses `LIKE` query)
- Verify `full_address` contains city name

### Admin API returns 403
- Check `API_Key` header matches `.env` value
- Verify header name is exactly `API_Key` (case-sensitive)

### Database connection fails
- Check PostgreSQL is running: `docker-compose up -d postgres`
- Verify database credentials in `.env`
- Check `POSTGRES_HOST` is correct (use service name in Docker)

---

## Project Structure Details

### Key Files

| File/Directory | Purpose |
|---|---|
| `app/steps_bot/main.py` | Bot entry point (polling) |
| `app/steps_bot/api/admin.py` | FastAPI admin endpoints |
| `app/steps_bot/db/models/pvz.py` | PVZ SQLAlchemy model |
| `app/steps_bot/db/repo.py` | Repository functions (queries) |
| `app/steps_bot/handlers/buy.py` | Order/purchase flow |
| `app/steps_bot/services/buy_service.py` | Order business logic |
| `app/admin/core/models.py` | Django admin models (DB interface) |
| `app/admin/core/admin.py` | Django admin configuration |

### Models Hierarchy

```
User
├── Family (optional)
├── Balance
├── Orders
│   ├── OrderItem
│   └── PVZ (reference)
└── Walk Records

PVZ (independent)
├── id (primary key, string)
└── full_address

Product
├── Category
└── OrderItem
```

---

## Contributing

1. Follow existing code style (type hints, docstrings)
2. Run migrations for schema changes
3. Add tests for new features
4. Update documentation for API changes
5. Commit with clear messages: `feat:`, `fix:`, `docs:`, etc.

---

## License

Proprietary — All rights reserved.

---

## Support

For issues or questions:
- Check existing GitHub issues
- Review memory-bank/ documentation for architectural decisions
- Contact development team

---

**Last Updated**: 2025-10-18  
**Version**: 1.0.0
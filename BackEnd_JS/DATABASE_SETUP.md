# Database Setup Guide

## Prerequisites

1. Docker and Docker Compose installed
2. Node.js 18+ installed

## Steps to Connect Backend to PostgreSQL

### 1. Start PostgreSQL and Redis Containers

```bash
cd db_service
docker-compose up -d
```

This will start:
- PostgreSQL on port 5432
- Redis on port 6379

Verify containers are running:
```bash
docker ps
```

### 2. Install Dependencies

```bash
cd BackEnd_JS
npm install
```

This installs Prisma and bcrypt for database and password handling.

### 3. Configure Environment Variables

The `.env` file is already created. Update it if needed:

```
DATABASE_URL=postgresql://admin:your_password@localhost:5432/product_db
REDIS_HOST=localhost
REDIS_PORT=6379
JWT_SECRET=your_super_secret_jwt_key_change_in_production
```

### 4. Run Database Migrations

```bash
# Generate Prisma Client
npx prisma generate

# Create database tables
npx prisma db push
```

Or manually apply SQL scripts:
```bash
# If using psql directly
psql -U admin -d product_db -h localhost -f ../db_service/postgres/create-tables.sql
psql -U admin -d product_db -h localhost -f ../db_service/postgres/create-functions.sql
psql -U admin -d product_db -h localhost -f ../db_service/postgres/create-indexes.sql
```

### 5. Start Backend Server

```bash
npm start
```

The server will start on `http://localhost:3000`

## Testing Auth Endpoints

### Register
```bash
curl -X POST http://localhost:3000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "password123",
    "fullName": "Test User"
  }'
```

### Login
```bash
curl -X POST http://localhost:3000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "password123"
  }'
```

### Get Current User
```bash
curl -X GET http://localhost:3000/api/v1/auth/me \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

## Prisma Studio (Optional GUI)

To view and edit database data with a UI:

```bash
npx prisma studio
```

This opens Prisma Studio at `http://localhost:5555`

## Common Issues

### "Cannot find module 'prisma'"
- Run `npm install`

### "Database connection refused"
- Make sure containers are running: `docker ps`
- Check PostgreSQL is on port 5432: `docker logs product_postgres`

### "Table already exists"
- Run: `npx prisma migrate reset` (warning: deletes all data)

### "Password hash mismatch"
- Make sure bcrypt is installed: `npm install bcrypt`

## Development Workflow

1. **Modify schema**: Edit `prisma/schema.prisma`
2. **Create migration**: `npx prisma migrate dev --name description`
3. **Apply changes**: `npx prisma db push`
4. **Restart server**: `npm start`

## Troubleshooting

Check database connection:
```bash
psql -U admin -h localhost -d product_db -c "SELECT 1"
```

Check Prisma logs:
```bash
npx prisma generate --verbose
```

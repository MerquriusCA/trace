# Admin Access

## Quick Access

### Production Admin Login
**URL**: https://trace-production-79d5.up.railway.app/admin/login

### Local Admin Login
**URL**: http://localhost:8000/admin/login

## Default Password
**Test Password**: `trace-admin-2024`

## Setting Custom Password

Set the `ADMIN_PASSWORD` environment variable in Railway or your local `.env` file:

```bash
ADMIN_PASSWORD=your-secure-password-here
```

## How It Works

1. Navigate to `/admin/login`
2. Enter the admin password
3. System generates a JWT token valid for 24 hours
4. Automatically redirects to `/admin/dashboard` with token
5. Token is included in URL for all admin pages

## Admin Pages

Once authenticated, you can access:

- **Dashboard**: `/admin/dashboard` - View all users and stats
- **Products**: `/admin/products` - View Stripe products
- **User Details**: `/admin/user/{id}/dashboard` - Individual user stats

## Security Notes

- Token expires after 24 hours
- Password is checked server-side only
- No passwords are stored in the frontend
- Token includes admin flag for authorization

## Testing Locally

1. Start the backend:
```bash
cd backend
python app.py
```

2. Navigate to: http://localhost:8000/admin/login

3. Enter password: `trace-admin-2024`

4. You'll be redirected to the admin dashboard

## Production Setup

1. Set `ADMIN_PASSWORD` in Railway environment variables
2. Deploy the changes
3. Access at: https://trace-production-79d5.up.railway.app/admin/login
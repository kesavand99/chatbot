# Authentication Service - Page Structure

This directory contains a modular authentication system with separate pages for different authentication flows.

## File Structure

### HTML Pages
- **`index.html`** - Landing page with navigation to all auth options
- **`login.html`** - Email/password login + Google login button
- **`register.html`** - Registration form (with optional MFA checkbox)
- **`mfa.html`** - MFA setup & verification panel (QR code, OTP input)
- **`google_register.html`** - Extra fields when first time signing in with Google
- **`welcome.html`** - Dashboard/welcome page shown after successful authentication

### Shared Resources
- **`common.js`** - Shared JavaScript helpers (API_BASE, setOut, localStorage handling, Google integration, MFA functions)
- **`common.css`** - Shared CSS styles for consistent look and feel

### Legacy
- **`google_auth_test.html`** - Original monolithic file (kept for reference)

## Page Flow

### Login Flow
1. User visits `login.html`
2. Can login with email/password or Google
3. If MFA required, redirected to `mfa.html`
4. After successful auth, redirected to `welcome.html`

### Registration Flow
1. User visits `register.html`
2. Fills registration form
3. If MFA enabled (checkbox), redirected to `mfa.html`
4. After successful registration, redirected to `welcome.html`

### Google Registration Flow
1. User clicks Google sign-in on login page
2. If first-time Google user, redirected to `google_register.html`
3. Additional info collected and account created
4. After successful registration, redirected to `welcome.html`

### MFA Flow
1. Triggered from login or registration
2. Shows QR code for TOTP setup
3. User scans QR and enters verification code
4. On success, redirected to `welcome.html`

### Welcome/Dashboard Flow
1. After any successful authentication, user lands on `welcome.html`
2. Shows user information and session status
3. Provides quick actions (MFA setup, logout, token verification)
4. Logout redirects back to `index.html`

## Key Features

### Shared JavaScript (`common.js`)
- **Configuration**: API_BASE, Google Client ID management
- **Navigation**: Page-to-page navigation helpers
- **Google Integration**: GIS initialization and token handling
- **MFA Functions**: Setup, verification, and state management
- **Storage**: localStorage and sessionStorage handling
- **API Communication**: Fetch wrappers for backend endpoints

### Session Management
- Uses sessionStorage to pass data between pages (MFA context, credentials)
- Uses localStorage for access token persistence
- Automatic cleanup of temporary data

### Responsive Design
- Mobile-friendly responsive layout
- Consistent styling across all pages
- Clean, modern UI with proper form validation

## Usage

### Starting the System
1. Open `index.html` for the landing page
2. Or directly navigate to specific pages:
   - `login.html` for existing users
   - `register.html` for new users
   - `mfa.html` for MFA setup (usually accessed via other pages)

### Backend Integration
- Configure `API_BASE` in `common.js` to point to your backend
- Ensure backend endpoints match the expected API calls:
  - `POST /auth/login`
  - `POST /auth/register`
  - `POST /auth/googleauthentication`
  - `GET /auth/google/config`
  - `POST /auth/mfa/start`
  - `POST /auth/mfa/verify`
  - `POST /auth/mfa/toggle`

### Google Setup
- Configure Google Client ID in your backend
- The frontend fetches the client ID dynamically from `/auth/google/config`

## Development Notes

### Adding New Pages
1. Create new HTML file using the same structure as existing pages
2. Include `common.css` and `common.js`
3. Add navigation links in other pages as needed
4. Update this README

### Customizing Styles
- Edit `common.css` to change the look and feel
- CSS variables are defined in `:root` for easy theme customization

### Error Handling
- All API calls include proper error handling
- Errors are displayed in the response box on each page
- User-friendly error messages with technical details in console

## Security Considerations

- Access tokens stored in localStorage (consider httpOnly cookies for production)
- Temporary data in sessionStorage is cleaned up after use
- Google ID tokens handled securely through GIS library
- MFA secrets displayed temporarily during setup only
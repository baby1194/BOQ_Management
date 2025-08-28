# BOQ Item Creation Password Setup

## Overview

This application now requires a password confirmation for critical BOQ (Bill of Quantities) operations to ensure only authorized users can perform these actions.

## Protected Actions

The following actions now require password confirmation:

1. **Creating new BOQ items** - Adding new items to the BOQ
2. **Updating contract quantities** - Creating new contract quantity update versions
3. **Deleting contract updates** - Removing contract quantity update versions

## Setup Instructions

### Option 1: Environment Variable (Recommended)

1. Create a `.env` file in the `frontend` directory
2. Add the following line to the `.env` file:
   ```
   VITE_BOQ_CREATION_PASSWORD=your_secure_password_here
   ```
3. Replace `your_secure_password_here` with your actual secure password
4. Restart the development server

### Option 2: Direct Code Modification

1. Open `frontend/src/pages/BOQItems.tsx`
2. Find the line:
   ```typescript
   const BOQ_CREATION_PASSWORD = "your_secure_password_here";
   ```
3. Replace `"your_secure_password_here"` with your actual password
4. Save the file

## How It Works

### Creating BOQ Items

- When a user clicks "Create BOQ Item", a password confirmation dialog appears
- The user must enter the correct password to proceed
- If the password is incorrect, an error message is displayed

### Updating Contract Quantities

- When a user clicks "Update Contract Quantity", a password confirmation dialog appears
- The user must enter the correct password to confirm creating a new contract update version
- This protects against accidental creation of unnecessary contract updates

### Deleting Contract Updates

- When a user clicks the delete icon (🗑️) on a contract update, a password confirmation dialog appears
- The user must enter the correct password to confirm the deletion
- A warning message indicates the action cannot be undone
- This prevents accidental deletion of important contract updates

### Dialog Features

- The dialog can be closed with the Cancel button or Escape key
- Pressing Enter in the password field will attempt to confirm
- Different dialog titles and messages based on the action
- Color-coded buttons (blue for create/update, red for delete)
- Error messages for incorrect passwords

## Security Notes

- The password is stored in the frontend code, so it's visible to anyone with access to the source
- For production use, consider implementing server-side authentication
- Change the password regularly and use a strong, unique password
- Never commit the actual password to version control
- All critical operations (create, update, delete) are now protected

## Environment Variable Benefits

- Keeps passwords out of source code
- Easy to change without modifying code
- Follows security best practices
- Works with different environments (dev, staging, production)

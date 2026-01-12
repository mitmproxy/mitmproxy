# Setting Up GitHub Secrets

This guide explains how to configure the required secrets for automated releases.

## Required Secrets

| Secret | Platform | Description |
|--------|----------|-------------|
| `APPLE_CERTIFICATE` | macOS | Base64-encoded Developer ID certificate |
| `APPLE_CERTIFICATE_PASSWORD` | macOS | Password for the certificate |
| `APPLE_ID` | macOS | Apple ID email for notarization |
| `APPLE_APP_PASSWORD` | macOS | App-specific password |
| `SPARKLE_PRIVATE_KEY` | macOS | EdDSA private key for update signing |
| `SPARKLE_PUBLIC_KEY` | macOS | EdDSA public key (for Info.plist) |

## macOS Code Signing Secrets

### 1. APPLE_CERTIFICATE

Export your Developer ID Application certificate:

1. **Open Keychain Access** on your Mac
2. Go to "My Certificates" category
3. Find "Developer ID Application: Oximy, Inc. (K6H6LCASRA)"
4. Right-click → Export → Save as `.p12` file
5. Set a strong password when prompted

Convert to Base64:
```bash
base64 -i /path/to/certificate.p12 | pbcopy
# The Base64 string is now in your clipboard
```

Add to GitHub:
1. Go to repository → Settings → Secrets and variables → Actions
2. Click "New repository secret"
3. Name: `APPLE_CERTIFICATE`
4. Value: Paste the Base64 string

### 2. APPLE_CERTIFICATE_PASSWORD

The password you set when exporting the .p12 file.

Add to GitHub:
- Name: `APPLE_CERTIFICATE_PASSWORD`
- Value: Your certificate export password

### 3. APPLE_ID

Your Apple ID email address used for notarization.

Example: `developer@oximy.com`

Add to GitHub:
- Name: `APPLE_ID`
- Value: Your Apple ID email

### 4. APPLE_APP_PASSWORD

Create an app-specific password for notarization:

1. Go to [appleid.apple.com](https://appleid.apple.com)
2. Sign in with your Apple ID
3. Navigate to Security → App-Specific Passwords
4. Click "Generate"
5. Name it something like "GitHub Actions Notarization"
6. Copy the generated password

Add to GitHub:
- Name: `APPLE_APP_PASSWORD`
- Value: The app-specific password (format: `xxxx-xxxx-xxxx-xxxx`)

## Sparkle Signing Secrets

### 5. SPARKLE_PRIVATE_KEY

Generate Sparkle EdDSA keys:

```bash
cd OximyMac

# First, fetch Sparkle package
swift build

# Generate keys
.build/checkouts/Sparkle/bin/generate_keys
```

Output:
```
A key has been generated and saved in:
    /Users/you/Library/Sparkle-Keys/ed25519

Your public key:
    5Dj8gQ... (base64 string)

Add the public key to your Info.plist with the SUPublicEDKey key.
```

**IMPORTANT:** The private key file must be kept secure! Never commit it to the repository.

Read the private key:
```bash
cat ~/Library/Sparkle-Keys/ed25519
```

Add to GitHub:
- Name: `SPARKLE_PRIVATE_KEY`
- Value: Contents of the `ed25519` file (starts with `-----BEGIN PRIVATE KEY-----`)

### 6. SPARKLE_PUBLIC_KEY

The public key output from the `generate_keys` command (the base64 string).

Add to GitHub:
- Name: `SPARKLE_PUBLIC_KEY`
- Value: The base64 public key string (e.g., `5Dj8gQ...`)

This key is embedded in the app's Info.plist and used to verify updates.

## Windows Code Signing (Optional)

If you have a Windows code signing certificate:

### WINDOWS_SIGN_CERT

1. Export your code signing certificate as `.pfx`
2. Base64 encode it:
   ```powershell
   [Convert]::ToBase64String([IO.File]::ReadAllBytes("certificate.pfx"))
   ```
3. Add to GitHub as `WINDOWS_SIGN_CERT`

### WINDOWS_SIGN_PASSWORD

The password for your .pfx file. Add as `WINDOWS_SIGN_PASSWORD`.

## Adding Secrets to GitHub

### Via Web UI

1. Navigate to your repository on GitHub
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Enter the name and value
5. Click **Add secret**

### Via GitHub CLI

```bash
# Set a secret
gh secret set APPLE_CERTIFICATE < certificate.p12.base64
gh secret set APPLE_CERTIFICATE_PASSWORD --body "your-password"
gh secret set APPLE_ID --body "developer@oximy.com"
gh secret set APPLE_APP_PASSWORD --body "xxxx-xxxx-xxxx-xxxx"
gh secret set SPARKLE_PRIVATE_KEY < ~/Library/Sparkle-Keys/ed25519
gh secret set SPARKLE_PUBLIC_KEY --body "5Dj8gQ..."

# List secrets
gh secret list
```

## Verifying Setup

After adding all secrets, verify by running a test workflow:

1. Go to Actions → Oximy Release
2. Run workflow with a test version (e.g., `0.0.1-test`)
3. Check "Mark as pre-release"
4. Monitor the workflow for any authentication errors

If successful, delete the test release:
```bash
gh release delete oximy-v0.0.1-test --yes
git push --delete origin oximy-v0.0.1-test
```

## Security Best Practices

1. **Never log secrets** - Don't echo secrets in workflow logs
2. **Rotate regularly** - Update app-specific passwords periodically
3. **Limit access** - Only give repository admin access to trusted team members
4. **Use environment protection** - Consider using GitHub Environments for additional approval steps
5. **Backup keys** - Store Sparkle private key in a secure backup location

## Troubleshooting

### "Unable to build chain to self-signed root"

The certificate chain is incomplete. Export the certificate with "Certificate Authority" included.

### "The specified item could not be found in the keychain"

The certificate wasn't imported correctly. Check the Base64 encoding and password.

### "Unable to submit for notarization"

- Verify Apple ID and app-specific password are correct
- Check that your Apple Developer account is active
- Ensure 2FA is enabled on your Apple ID

### "Sparkle signature verification failed"

- Ensure SPARKLE_PUBLIC_KEY matches the private key used to sign
- Regenerate keys if you've lost the original pair (requires new release)

## Quick Reference

```bash
# Export certificate to base64 (macOS)
base64 -i certificate.p12 | pbcopy

# Generate Sparkle keys
.build/checkouts/Sparkle/bin/generate_keys

# Read Sparkle private key
cat ~/Library/Sparkle-Keys/ed25519

# Set secret via CLI
gh secret set SECRET_NAME --body "value"

# List all secrets
gh secret list
```

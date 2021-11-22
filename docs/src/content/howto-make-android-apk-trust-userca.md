---
title: "Make Android app trust user CA"
menu:
    howto:
        weight: 4
---

# Make an Android app trust user CA
Almost any app will not trust user CA's by default. Installing a CA in the system certificate store requires rooting the device or emulator. This is sometimes not an option, especially if the app refuses to run on a rooted device.

We can have an app trust the user certificate store, if however the app has its own and doesn't even use the one android provides further patching will be required.

## 1. Prerequisites
- [Android Studio/Android Sdk](https://developer.android.com/studio), [Apktool](https://ibotpeaches.github.io/Apktool/) and openssl are installed.
- Android Studio's build-tools are added to the $PATH variable. They are usually located at `$HOME/Android/sdk/build-tools/<version-number>/`.
- The apps .apk file inside its own directory.

## 2. Patching the app
- To decompile the app run `apktool d <appname>.apk`. This will create a directory containing the contents of the .apk file.
- Open `<appname>/AndroidManifest.xml` in an editor and add the following attribute to the `<application>` tag:
```
android:networkSecurityConfig="@xml/network_security_config"
```
- Create or patch the file `<appname>/res/xml/network_security_config.xml` and insert:
```xml
<?xml version="1.0" encoding="utf-8"?>
<network-security-config>
    <base-config cleartextTrafficPermitted="true">
        <trust-anchors>
            <certificates src="system" />
            <certificates src="user" />
        </trust-anchors>
    </base-config>
</network-security-config>
```
- Repackage the app with `apktool b <appname> -o app-modified.apk`.
- Next we have to [zipalign](https://developer.android.com/studio/command-line/zipalign) our new file: `zipalign -p -f 4 app-modified.apk app-zipped.apk`.

## 3. Signing the app
Since patching the app has invalidated its signature we have to sign it ourselves.
- Generate a key and certificate with
```bash
openssl req -x509 -days 9125 -newkey rsa:4096 -nodes -keyout key.pem -out cert.pem
```
- We need the key in pkcs format.
```bash
openssl pkcs8 -topk8 -outform DER -in key.pem -inform PEM -out key.pk8 -nocrypt
```
- Now we are ready to sign our file
```bash
apksigner sign --key key.pk8 --cert cert.pem --out app-signed.apk app-zipped.apk
```
The app is now ready to be installed, you can use `adb install app-signed.apk` or transfer the file manually to the device and install it from a file browser.

## 4. Troubleshooting
If `adb install app.signed.apk` hangs without an error message it may help to install directly from the device shell, at least in order to get an error message.
- `adb push app-signed.apk /data/local/` moves the app on the device.
- `adb shell` runs the device shell.
- `pm install /data/local/app-signed.apk` attempts an installation.
- `rm app-signed.apk` removes the file again from the device.

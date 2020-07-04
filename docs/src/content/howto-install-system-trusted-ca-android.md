---
title: "Install System CA on Android"
menu:
    howto:
        weight: 4
---

# Install System CA Certificate on Android Emulator

[Since Android 7, apps ignore user certificates](https://android-developers.googleblog.com/2016/07/changes-to-trusted-certificate.html), unless they are configured to use them.
As most applications do not explicitly opt in to use user certificates, we need to place our mitmproxy CA certificate in the system certificate store,
in order to avoid having to patch each application, which we want to monitor.

Please note, that apps can decide to ignore the system certificate store and maintain their own CA certificates. In this case you have to patch the application.

## 1. Prerequisites

  - Emulator from Android SDK with proxy settings pointing to mitmproxy

  - Mitmproxy CA certificate
    - Usually located in `~/.mitmproxy/mitmproxy-ca-cert.cer`
    - If the folder is empty or does not exist, run `mitmproxy` in order to generate the certificates
    
## 2. Rename certificate
Enter your certificate folder
```bash
cd ~/.mitmproxy/
```

  - CA Certificates in Android are stored by the name of their hash, with a '0' as extension
  - Now generate the hash of your certificate
  
```bash
openssl x509 -inform PEM -subject_hash_old -in mitmproxy-ca-cert.cer | head -1
```
Lets assume, the output is `c8450d0d`

We can now copy `mitmproxy-ca-cert.cer` to `c8450d0d.0` and our system certificate is ready to use
```bash
cp mitmproxy-ca-cert.cer c8450d0d.0
```

## 3. Insert certificate into system certificate store

Note, that Android 9 (API LEVEL 28) was used to test the following steps and that the `emulator` executable is located in the Android SDK

  - Start your android emulator. 
     - Get a list of your AVDs with `emulator -list-avds`
     - Make sure to use the `-writable-system` option. Otherwise it will not be possible to write to `/system`
     - Keep in mind, that the **emulator will load a clean system image when starting without `-writable-system` option**.
     - This means you always have to start the emulator with `-writable-system` option in order to use your certificate

```bash
emulator -avd <avd_name_here> -writable-system
```

  - Restart adb as root
  
```bash
adb root
```

  - Get write access to `/system` on the device
  - In earlier versions (API LEVEL < 28) of Android you have to use `adb shell "mount -o rw,remount /system"`
  
```bash
adb shell "mount -o rw,remount /"
```

  - Push your certificate to the system certificate store and set file permissions
  
```bash
adb push c8450d0d.0 /system/etc/security/cacerts
adb shell "chmod 664 /system/etc/security/cacerts/c8450d0d.0"
```

## 4. Reboot device and enjoy decrypted TLS traffic

  - Reboot your device. 
     - You CA certificate should now be system trusted
         
```bash
adb reboot
```

**Remember**: You **always** have to start the emulator using the `-writable-system` option in order to use your certificate

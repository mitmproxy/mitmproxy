---
title: "System CA on Android Emulator"
menu:
    howto:
        weight: 4
---

# Install System CA Certificate on Android Emulator
Since Android 7, [apps ignore user provided certificates](https://android-developers.googleblog.com/2016/07/changes-to-trusted-certificate.html), unless they are configured to use them.
As most applications do not explicitly opt in to use user certificates, we need to place our mitmproxy CA certificate in the system certificate store,
in order to avoid having to patch each application, which we want to monitor.

Please note, that apps can decide to ignore the system certificate store and maintain their own CA certificates. In this case you have to patch the application.

## 1. Prerequisites

- [Android Studio/Android Sdk](https://developer.android.com/studio) is installed (tested with Version 4.1.3 for Linux 64-bit)
- An Android Virtual Device (AVD) was created. Setup documentation available [here](https://developer.android.com/studio/run/managing-avds)
  - The AVD must not run a production build (these will prevent you from using `adb root`)
  - The proxy settings of the AVD are configured to use mitmproxy. Documentation [here](https://developer.android.com/studio/run/emulator-networking#proxy)

- Emulator and adb executables from Android Sdk have been added to $PATH variable
  - emulator usually located at `/home/<your_user_name>/Android/Sdk/emulator/emulator` on Linux systems
  - adb usually located at `/home/<your_user_name>/Android/Sdk/platform-tools/adb` on Linux systems
  - I added these lines to my `.bashrc`
  ``` bash
  export PATH=$PATH:$HOME/Android/Sdk/platform-tools
  export PATH=$PATH:$HOME/Android/Sdk/emulator
  ```

- Mitmproxy CA certificate has been created
  - Usually located in `~/.mitmproxy/mitmproxy-ca-cert.cer` on Linux systems
  - If the folder is empty or does not exist, run `mitmproxy` in order to generate the certificates

## 2. Rename certificate

CA Certificates in Android are stored by the name of their hash, with a '0' as extension (Example: `c8450d0d.0`). It is necessary to figure out the hash of your CA certificate and copy it to a file with this hash as filename. Otherwise Android will ignore the certificate. 
By default, the mitmproxy CA certificate is located in this file: `~/.mitmproxy/mitmproxy-ca-cert.cer`


### Instructions

- Enter your certificate folder: `cd ~/.mitmproxy/`
- Generate hash and copy certificate : ``hashed_name=`openssl x509 -inform PEM -subject_hash_old -in mitmproxy-ca-cert.cer | head -1` && cp mitmproxy-ca-cert.cer $hashed_name.0``

## 3. Insert certificate into system certificate store

Now we have to place our CA certificate inside the system certificate store located at `/system/etc/security/cacerts/` in the Android filesystem. By default, the `/system` partition is mounted as read-only. The following steps describe how to gain write permissions on the `/system` partition and how to copy the certificate created in the previous step.

### Instructions for API LEVEL > 28
 Starting from API LEVEL 29 (Android 10), it seems to be impossible to mount the "/" partition as read-write. Google provided a [workaround for this issue](https://android.googlesource.com/platform/system/core/+/master/fs_mgr/README.overlayfs.md) using OverlayFS. Unfortunately, at the time of writing this (11. April 2021), the instructions in this workaround will result in your emulator getting stuck in a [boot loop](https://issuetracker.google.com/issues/144891973). Some smart guy on Stackoverflow [found a way](https://stackoverflow.com/questions/60867956/android-emulator-sdk-10-api-29-wont-start-after-remount-and-reboot) to get the `/system` directory writable anyway.

**Keep in mind:** You always have to start the emulator using the `-writable-system` option if you want to use your certificate. Otherwise Android will load a "clean" system image.

Tested on emulators running API LEVEL 29 and 30

 #### Instructions
   - List your AVDs: `emulator -list-avds` (If this yields an empty list, create a new AVD in the Android Studio AVD Manager)
   - Start the desired AVD: `emulator -avd <avd_name_here> -writable-system` (add `-show-kernel` flag for kernel logs)
   - restart adb as root: `adb root`
   - disable secure boot verification: `adb shell avbctl disable-verification`
   - reboot device: `adb reboot`
   - restart adb as root: `adb root`
   - perform remount of partitions as read-write: `adb remount`. (If adb tells you that you need to reboot, reboot again `adb reboot` and run `adb remount` again.)
   - push your renamed certificate from step 2: `adb push <path_to_certificate> /system/etc/security/cacerts`
   - set certificate permissions: `adb shell chmod 664 /system/etc/security/cacerts/<name_of_pushed_certificate>`
   - reboot device: `adb reboot`

### Instructions for API LEVEL <= 28

Tested on emulators running API LEVEL 26, 27 and 28

**Keep in mind:** You always have to start the emulator using the `-writable-system` option if you want to use your certificate. Otherwise Android will load a "clean" system image.

   - List your AVDs: `emulator -list-avds` (If this yields an empty list, create a new AVD in the Android Studio AVD Manager)
   - Start the desired AVD: `emulator -avd <avd_name_here> -writable-system` (add `-show-kernel` flag for kernel logs)
   - restart adb as root: `adb root`
   - perform remount of partitions as read-write: `adb remount`. (If adb tells you that you need to reboot, reboot again `adb reboot` and run `adb remount` again.)
   - push your renamed certificate from step 2: `adb push <path_to_certificate> /system/etc/security/cacerts`
   - set certificate permissions: `adb shell chmod 664 /system/etc/security/cacerts/<name_of_pushed_certificate>`
   - reboot device: `adb reboot`

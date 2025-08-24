---
title: "System CA on Android Emulator"
weight: 4
aliases:
  - /howto-install-system-trusted-ca-android/
---

# Install System CA Certificate on Android Emulator
Since Android 7, [apps ignore user provided certificates](https://android-developers.googleblog.com/2016/07/changes-to-trusted-certificate.html), unless they are configured to use them.
As most applications do not explicitly opt in to use user certificates, we need to place our mitmproxy CA certificate in the system certificate store,
in order to avoid having to patch each application, which we want to monitor.

Please note, that apps can decide to ignore the system certificate store and maintain their own CA certificates. In this case you have to patch the application.

## 1. Prerequisites

- [Android Studio/Android Sdk](https://developer.android.com/studio) is installed (tested with Version 4.1.3 for Linux 64-bit)
- An Android Virtual Device (AVD) was created. Setup documentation available [here](https://developer.android.com/studio/run/managing-avds)
  - AVD production builds (those labeled with "Google Play") will prevent you from using `adb root`. You need to use [the Magisk method]({{< ref "#instructions-when-using-magisk" >}}) if you need Google Play installed.
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

Now we have to place our CA certificate inside the system certificate store located at `/system/etc/security/cacerts/` in the Android filesystem. By default, the `/system` partition is mounted as read-only. The following steps describe how to gain write permissions on the `/system` partition and how to copy the certificate created in [the previous step]({{< ref "#2-rename-certificate" >}}).

### Instructions when using Magisk
If you want to use a production build (labeled "Google Play"; it's those builds that have Google Play installed) you can use Magisk to obtain root in your AVD.
[Magisk](https://github.com/topjohnwu/Magisk) allows root on your Android device or emulator.

See the [instructions here](https://gitlab.com/newbit/rootAVD) for installing Magisk on your AVD.
Note: the instructions say to start your AVD. Do not supply an `-http-proxy` directive to mitmproxy at this point.

When you are done with that, your emulator will allow root. You can check this by running a terminal emulator and typing `su`.
Magisk should ask you if you want to grant root to the program. After granting this, typing `whoami` would display `root`.

However, after you have installed Magisk, you can no longer start your emulator with `-writable-system`. It will cause a boot loop. (Start your AVD with `-show-kernel` to see the error.)
But you can install your mitmproxy certificate by putting it in a Magisk module, and installing that module.
Magisk will take care of copying your certificate to `/system/etc/security/cacerts/` during boot.

#### Downloading the Magisk module from mitmweb
If you run mitmweb, you can get simply download the Magisk module instead of handcrafting it.
Stop your AVD, and start it again with `-http-proxy 127.0.0.1:8080` (or whatever IP and port combination you are running mitmweb's proxy on).

Then, *inside* the AVD, start a browser and navigate to `http://mitm.it/cert/magisk`.
You will be prompted to download `mitmproxy-magisk-module.zip`, which is the Magisk module you need. Store that file somewhere (like in 'Downloads').

Then open up Magisk, click on `Modules` and install your module.

Reboot your AVD.

#### Creating the Magisk module containing your certificate
If you do not run mitmweb, you'll need to create a Magisk module yourself.
See [here](https://topjohnwu.github.io/Magisk/guides.html#magisk-modules) for in-depth information on Magisk modules, but basically it boils down to this:

Create the following directories:
- `mitmproxycert` (this will be the root of your module)
- `mitmproxycert/com/google/android`
- `mitmproxycert/system/etc/security/cacerts`

Place your renamed certificate from [step 2]({{< ref "#2-rename-certificate" >}}) inside `mitmproxycert/system/etc/security/cacerts` and `chmod 664` it.

Save the content of [https://github.com/topjohnwu/Magisk/blob/master/scripts/module_installer.sh](https://github.com/topjohnwu/Magisk/blob/master/scripts/module_installer.sh) as a local file `update-binary` and place it inside `mitmproxycert/com/google/android`.

Create a file named `updater-script` containing only the string `#MAGISK` and place it inside `mitmproxycert/com/google/android`.

Create a file named `module.prop` and place it inside `mitmproxycert`. The file should contain something like:

```
id=mitmproxycert
name=MITM proxy certificate
version=1
versionCode=1
author=mitmproxycert
description=My shiny MITM proxy certificate to reveal all secrets and obtain world domination!
```

Zip the module using something like `cd ./mitmproxycert ; zip -r ./../mitmproxycert.zip ./` and push it to your running AVD using `adb push ./../mitmproxycert.zip /storage/emulated/0/Download/`.

The go to your AVD, open up Magisk, click on `Modules` and install your module (you'll find it in the Downloads folder).

Reboot your AVD.

### Instructions for API LEVEL > 28 using `-writable-system`
By default, the `/system` partition is mounted as read-only. The following steps describe how to gain write permissions on the `/system` partition and how to copy the certificate created in chapter 2.

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
   - push your renamed certificate from [step 2]({{< ref "#2-rename-certificate" >}}): `adb push <path_to_certificate> /system/etc/security/cacerts`
   - set certificate permissions: `adb shell chmod 644 /system/etc/security/cacerts/<name_of_pushed_certificate>`
   - reboot device: `adb reboot`

### Instructions for API LEVEL <= 28 using `-writable-system`

Tested on emulators running API LEVEL 26, 27 and 28

**Keep in mind:** You always have to start the emulator using the `-writable-system` option if you want to use your certificate. Otherwise Android will load a "clean" system image.

   - List your AVDs: `emulator -list-avds` (If this yields an empty list, create a new AVD in the Android Studio AVD Manager)
   - Start the desired AVD: `emulator -avd <avd_name_here> -writable-system` (add `-show-kernel` flag for kernel logs)
   - restart adb as root: `adb root`
   - perform remount of partitions as read-write: `adb remount`. (If adb tells you that you need to reboot, reboot again `adb reboot` and run `adb remount` again.)
   - push your renamed certificate from [step 2]({{< ref "#2-rename-certificate" >}}): `adb push <path_to_certificate> /system/etc/security/cacerts`
   - set certificate permissions: `adb shell chmod 644 /system/etc/security/cacerts/<name_of_pushed_certificate>`
   - reboot device: `adb reboot`

### Testing that your certificate is loaded from the system certificate store

In your AVD, go to Settings → Security → Advanced → Encryption & credentials → Trusted credentials. Find your certificate (default name is `mitmproxy`) in the list.

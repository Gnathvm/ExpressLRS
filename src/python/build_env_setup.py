Import("env", "projenv")
import os
import shutil
import upload_via_esp8266_backpack
import esp_compress
import elrs_helpers
import BFinitPassthrough
import ETXinitPassthrough
import UnifiedConfiguration

def add_target_uploadoption(name: str, desc: str) -> None:
    # Add an upload target 'uploadforce' that forces update if target mismatch
    # This must be called after UPLOADCMD is set
    env.AddCustomTarget(
        name=name,
        dependencies="${BUILD_DIR}/${PROGNAME}.bin",
        title=name,
        description=desc,
        actions=env['UPLOADCMD']
    )

def get_version(env):
    return '%s (%s) %s' % (env.get('GIT_VERSION'), env.get('GIT_SHA'), env.get('REG_DOMAIN'))

platform = env.get('PIOPLATFORM', '')
stm = platform in ['ststm32']

target_name = env['PIOENV'].upper()
print("PLATFORM : '%s'" % platform)
print("BUILD ENV: '%s'" % target_name)
print("build version: %s\n\n" % get_version(env))

if platform in ['espressif8266']:
    if "_WIFI" in target_name:
        env.Replace(UPLOAD_PROTOCOL="custom")
        env.Replace(UPLOADCMD=upload_via_esp8266_backpack.on_upload)
    elif "_UART" in target_name:
        env.Replace(
            UPLOADER="$PROJECT_DIR/python/external/esptool/esptool.py",
            UPLOAD_SPEED=460800,
            UPLOADERFLAGS=[
                "-b", "$UPLOAD_SPEED", "-p", "$UPLOAD_PORT",
                "-c", "esp8266", "--before", "default_reset", "--after", "soft_reset", "write_flash"
            ]
        )
    elif "_BETAFLIGHTPASSTHROUGH" in target_name:
        env.Replace(
            UPLOADER="$PROJECT_DIR/python/external/esptool/esptool.py",
            UPLOAD_SPEED=420000,
            UPLOADERFLAGS=[
                "--passthrough", "-b", "$UPLOAD_SPEED", "-p", "$UPLOAD_PORT",
                "-c", "esp8266", "--before", "no_reset", "--after", "soft_reset", "write_flash"
            ]
        )
        env.AddPreAction("upload", BFinitPassthrough.init_passthrough)

elif platform in ['espressif32']:
    if "_WIFI" in target_name:
        env.Replace(UPLOAD_PROTOCOL="custom")
        env.Replace(UPLOADCMD=upload_via_esp8266_backpack.on_upload)
    elif "_UART" in target_name:
        env.Replace(
            UPLOADER="$PROJECT_DIR/python/external/esptool/esptool.py",
            UPLOAD_SPEED=460800
        )
    if "_ETX" in target_name:
        env.Replace(UPLOADER="$PROJECT_DIR/python/external/esptool/esptool.py")
        env.AddPreAction("upload", ETXinitPassthrough.init_passthrough)
    elif "_BETAFLIGHTPASSTHROUGH" in target_name:
        if "ESP32S3" in target_name:
            chip = "esp32-s3"
        elif "ESP32C3" in target_name:
            chip = "esp32-c3"
        else:
            chip = "esp32"
        env.Replace(
            UPLOADER="$PROJECT_DIR/python/external/esptool/esptool.py",
            UPLOAD_SPEED=420000,
            UPLOADERFLAGS=[
                "--passthrough", "-b", "$UPLOAD_SPEED", "-p", "$UPLOAD_PORT",
                "-c", chip, "--before", "no_reset", "--after", "hard_reset", "write_flash"
            ]
        )
        env.AddPreAction("upload", BFinitPassthrough.init_passthrough)

if "_WIFI" in target_name:
    add_target_uploadoption("uploadconfirm", "Do not upload, just send confirm")
    if "_TX_" in target_name:
        env.SetDefault(UPLOAD_PORT="elrs_tx.local")
    else:
        env.SetDefault(UPLOAD_PORT="elrs_rx.local")

if platform != 'native':
    add_target_uploadoption("uploadforce", "Upload even if target mismatch")

# Remove stale binary so the platform is forced to build a new one and attach options/hardware-layout files
try:
    os.remove(env['PROJECT_BUILD_DIR'] + '/' + env['PIOENV'] +'/'+ env['PROGNAME'] + '.bin')
except FileNotFoundError:
    None
env.AddPostAction("$BUILD_DIR/${PROGNAME}.bin", UnifiedConfiguration.appendConfiguration)
if platform in ['espressif8266'] and "_WIFI" in target_name:
    env.AddPostAction("$BUILD_DIR/${PROGNAME}.bin", esp_compress.compressFirmware)

def copyBootApp0bin(source, target, env):
    file = os.path.join(env.PioPlatform().get_package_dir("framework-arduinoespressif32"), "tools", "partitions", "boot_app0.bin")
    shutil.copy2(file, os.path.join(env['PROJECT_BUILD_DIR'], env['PIOENV']))

if platform in ['espressif32']:
    env.AddPreAction("$BUILD_DIR/${PROGNAME}.bin", copyBootApp0bin)

if platform in ['espressif32', 'espressif8266']:
    if not os.path.exists('hardware'):
        elrs_helpers.git_cmd('clone', 'https://github.com/Gnathvm/targets', 'hardware')

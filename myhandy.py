import signal
import sys
import os
import onnx_asr
import subprocess
import pyperclip
if sys.platform == "linux":
    from evdev import UInput, ecodes as e
else:
    import pyautogui


LOCK_FILE = os.getenv('LOCK_FILE', '/tmp/myhandy.lock')
WAVE_FILE = os.getenv('WAVE_FILE', '/tmp/myhandyrecord.wav')
RECORD_CMD = os.getenv('ARECORD_CMD', 'arecord -r 16000 -c 1 -f S16_LE -t wav').split()
BEEP_CMD = os.getenv('BEEP_CMD', 'aplay /usr/share/sounds/sound-icons/glass-water-1.wav').split()
NOTIFY_CMD = os.getenv('NOTIFY_CMD', 'notify-send -t 1 -h boolean:transient:true').split()
EXIT_WORD = os.getenv('EXIT_WORD', 'Выход.').lower()
MODEL_NAME = os.getenv('MODEL_NAME', 'gigaam-v3-e2e-ctc')
MODEL_PATH = os.getenv('MODEL_PATH', './models')
RECORD_PROCESS = None
MODEL = None


def pastetext(text):
    print(f"Распознано: {text}")
    if not text.strip():
        run_subprocess(NOTIFY_CMD + ['Nothing recognized. Try again.'])
        return
    if text.lower() == EXIT_WORD:
        run_subprocess(NOTIFY_CMD + ['Closing...'])
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)
        sys.exit(0)
        
    pyperclip.copy(text)
    if sys.platform == "linux":
        ui = UInput()
        # Ctrl+/Shift/+V
        ui.write(e.EV_KEY, e.KEY_LEFTCTRL, 1)
        # ui.write(e.EV_KEY, e.KEY_LEFTSHIFT, 1)
        ui.write(e.EV_KEY, e.KEY_V, 1)
        ui.syn()
        ui.write(e.EV_KEY, e.KEY_V, 0)
        # ui.write(e.EV_KEY, e.KEY_LEFTSHIFT, 0)
        ui.write(e.EV_KEY, e.KEY_LEFTCTRL, 0)
        ui.syn()
        ui.close()
    else:
        pyautogui.hotkey('ctrl', 'v') #  не работает в wayland(ubuntu), поэтому юзаем evdev
    run_subprocess(NOTIFY_CMD + [f'"{text}"'])

def run_subprocess(cmd=None):
    if cmd:
        return subprocess.Popen(cmd)
    else:
        return None

def handler(signum, frame):
    global RECORD_PROCESS
    if RECORD_PROCESS:
        recognize_text()
    else:
        RECORD_PROCESS = start_record()

def start_record():
    run_subprocess(NOTIFY_CMD + ['Starting recording...'])
    run_subprocess(BEEP_CMD)
    return run_subprocess(RECORD_CMD + [WAVE_FILE])

def recognize_text():
    global RECORD_PROCESS
    global MODEL
    RECORD_PROCESS.terminate()
    RECORD_PROCESS.wait()
    RECORD_PROCESS = None
    text = MODEL.recognize(WAVE_FILE)
    pastetext(text)

def main():

    if os.path.exists(LOCK_FILE):
        try:
            pid = int(open(LOCK_FILE).read())
            os.kill(pid, signal.SIGUSR1)
            sys.exit(0)
        except ProcessLookupError:
            # Process doesn't exist anymore, clean up stale lock file
            os.remove(LOCK_FILE)
        except (ValueError, IOError):
            # Lock file is corrupted or unreadable
            os.remove(LOCK_FILE)

    # Первая копия
    with open(LOCK_FILE, 'w') as f:
        f.write(str(os.getpid()))

    signal.signal(signal.SIGUSR1, handler)

    os.kill(os.getpid(), signal.SIGUSR1) # Запускаем запись сразу при старте
    
    global MODEL
    MODEL = onnx_asr.load_model(MODEL_NAME, MODEL_PATH) # Загружаем модель ASR

    try:
        while True:
            signal.pause() # Ждем сигналов 
    except KeyboardInterrupt:
        os.remove(LOCK_FILE)

if __name__ == '__main__':
    main()
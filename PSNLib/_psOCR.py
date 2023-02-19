import subprocess
try:
    from ._utils import relativeItem
except ImportError:
    from _utils import  relativeItem

class PsOCRException(Exception):
    pass


def recogniseGame(img: str) -> str:
    ocr = relativeItem('PSNOCR')
    proc = subprocess.Popen([ocr, img], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = proc.communicate()
    if err:
        raise PsOCRException(err)

    output = out.decode('utf-8').split('\n')[0]
    if output.startswith('OK:'):
        return output.split('OK:')[1].strip()
    else:
        raise PsOCRException(out)


if __name__ == '__main__':
    print(recogniseGame('/Users/Sal/Desktop/1.png'))